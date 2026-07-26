"""Background job processing for async document ingestion.

Ingesting a document (parse -> chunk -> embed -> index) can take minutes for
large files, which would otherwise block the request thread and time out the
client (see IndexResult-based synchronous /upload for the blocking version).

Two implementations, selected by api/dependencies.py based on whether
Postgres is configured:

``JobStore`` -- single-process, in-memory, one worker thread. State is lost
on restart and isn't shared across instances. Used when no Postgres is
configured (the scanning-fallback deployment), where the shared BM25 index
is a local pickle full-rebuilt on every ingest and isn't safe for concurrent
workers anyway -- one worker was already the correct concurrency for that
backend, so nothing about this class needed to change.

``WorkerPool`` -- persistent, multi-worker, backed by a Postgres
``JobRepository`` (``ingestion_jobs`` table, claimed via
``FOR UPDATE SKIP LOCKED``). Job state survives a restart; several worker
threads safely process different jobs concurrently since the incremental
Postgres-backed BM25/dedup/compliance repositories (see
storage/repositories/postgres/) have no shared-mutable-state race the old
single-worker constraint was protecting against.
"""

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Literal, Optional

from rag_hybrid_search.storage.repositories.base import IngestionJob, JobRepository

logger = logging.getLogger(__name__)

JobState = Literal["processing", "ready", "failed"]


@dataclass
class Job:
    job_id: str
    state: JobState = "processing"
    result: Optional[dict] = None
    error: Optional[str] = None


class JobStore:
    """Tracks background ingestion jobs, executed one at a time on a dedicated worker thread.

    A single worker (``max_workers=1``) deliberately serializes ingestion so
    concurrent uploads can't race on the shared BM25 rebuild or chunk store
    writes -- the same safety property the old synchronous endpoint got for
    free by running on one thread.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingestion-worker")

    def submit(self, work: Callable[[], dict]) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = Job(job_id=job_id)
        self._executor.submit(self._run, job_id, work)
        return job_id

    def _run(self, job_id: str, work: Callable[[], dict]) -> None:
        try:
            result = work()
            with self._lock:
                self._jobs[job_id] = Job(job_id=job_id, state="ready", result=result)
        except Exception as e:  # noqa: BLE001 - surface any failure via job status, not a crash
            logger.exception("background ingestion job %s failed", job_id)
            with self._lock:
                self._jobs[job_id] = Job(job_id=job_id, state="failed", error=str(e))

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)


def process_ingestion_payload(payload: dict, container) -> dict:
    """Ingest every file described in an ``ingestion_jobs.payload`` row.

    Payload shape (built by api/routes.py at enqueue time, files' raw bytes
    already written to ``container.uploads_dir`` before the job is
    persisted -- jsonb isn't a place to put file bytes, and writing to disk
    first means a worker picking this up after a restart can still find the
    content):

        {"files": [{"filename": str, "stored_path": str}, ...],
         "document_type": str, "regulation": str | None, ...}

    Mirrors the old ``work()`` closure in ``upload_documents_async`` exactly
    (same shared-dedup-cache / deferred-BM25-rebuild pattern, see
    ``IngestionPipeline.ingest_batch`` docstring) -- moved here so both
    ``JobStore`` and ``WorkerPool`` can reuse it. Imports ``api.routes``
    locally, not at module level: routes.py imports api.dependencies (for
    ``Container``), and dependencies.py builds a ``WorkerPool`` bound to
    this function, so a top-level import here would be circular. By the
    time this function actually runs (a worker thread claiming a job after
    startup), routes.py is already fully imported.
    """
    from api.routes import IndexResponse, _ingest_bytes  # local import: see docstring

    files = payload["files"]
    existing_pairs = [
        (item.chunk, item.embedding) for item in container.chunk_store.all_with_embeddings()
    ] if files else []
    effective_date = date.fromisoformat(payload["effective_date"]) if payload.get("effective_date") else None
    results = [
        _ingest_bytes(
            f["filename"], Path(f["stored_path"]).read_bytes(), payload["document_type"], container,
            regulation=payload.get("regulation"), authority=payload.get("authority"),
            jurisdiction=payload.get("jurisdiction"), effective_date=effective_date,
            risk_category=payload.get("risk_category"),
            existing_pairs=existing_pairs, rebuild_bm25=False,
        )
        for f in files
    ]
    if files:
        container.index_manager.rebuild_bm25_index()
    container.metrics.increment("uploads", len(files))
    return IndexResponse(results=results).model_dump()


class WorkerPool:
    """Multi-threaded claim-based worker pool consuming a persistent
    ``JobRepository`` (Postgres ``ingestion_jobs``, ``FOR UPDATE SKIP
    LOCKED``): several worker threads claim and process different jobs
    concurrently, job state survives a process restart, a claimed job whose
    worker crashes without updating its heartbeat is reclaimed by the
    reaper after ``heartbeat_timeout_s``, and a failed job is retried with
    exponential backoff up to ``JobRepository.fail``'s max_retries before
    landing in the ``dead_letter`` status for manual inspection.
    """

    def __init__(
        self,
        job_repository: JobRepository,
        process: Callable[[dict], dict],
        *,
        concurrency: int,
        heartbeat_interval_s: int,
        heartbeat_timeout_s: int,
        poll_interval_s: float = 1.0,
    ):
        self._jobs = job_repository
        self._process = process
        self._concurrency = max(1, concurrency)
        self._heartbeat_interval_s = heartbeat_interval_s
        self._heartbeat_timeout_s = heartbeat_timeout_s
        self._poll_interval_s = poll_interval_s
        self._threads: list[threading.Thread] = []
        self._stop = threading.Event()
        self._paused = threading.Event()

    def start(self) -> None:
        for i in range(self._concurrency):
            t = threading.Thread(target=self._run_worker, name=f"ingestion-worker-{i}", daemon=True)
            t.start()
            self._threads.append(t)
        reaper = threading.Thread(target=self._run_reaper, name="ingestion-reaper", daemon=True)
        reaper.start()
        self._threads.append(reaper)
        logger.info("worker pool started: %d worker(s)", self._concurrency)

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    @property
    def paused(self) -> bool:
        return self._paused.is_set()

    def shutdown(self, wait_s: float = 30.0) -> None:
        """Stop claiming new jobs and wait up to ``wait_s`` for in-flight
        ones to finish. Ingestion isn't cheaply preemptible mid-embedding-
        call, so a job still running past the deadline is left to complete
        or fail on its own -- its heartbeat keeps it safe from the reaper
        either way, and the reaper reclaims it if the process is killed
        before it finishes."""
        self._stop.set()
        deadline = time.monotonic() + wait_s
        for t in self._threads:
            remaining = max(0.0, deadline - time.monotonic())
            t.join(timeout=remaining)

    def _run_worker(self) -> None:
        worker_id = str(uuid.uuid4())
        while not self._stop.is_set():
            if self._paused.is_set():
                time.sleep(self._poll_interval_s)
                continue
            try:
                job = self._jobs.claim(worker_id)
            except Exception:
                logger.exception("job claim failed (worker %s)", worker_id)
                time.sleep(self._poll_interval_s)
                continue
            if job is None:
                time.sleep(self._poll_interval_s)
                continue
            self._process_claimed(job, worker_id)

    def _process_claimed(self, job: IngestionJob, worker_id: str) -> None:
        stop_heartbeat = threading.Event()

        def heartbeat_loop() -> None:
            while not stop_heartbeat.wait(self._heartbeat_interval_s):
                try:
                    self._jobs.heartbeat(job.job_id)
                except Exception:
                    logger.exception("heartbeat failed for job %s", job.job_id)

        hb_thread = threading.Thread(target=heartbeat_loop, daemon=True, name=f"heartbeat-{job.job_id}")
        hb_thread.start()
        try:
            result = self._process(job.payload)
            self._jobs.complete(job.job_id, result)
        except Exception as e:  # noqa: BLE001 - isolate one job's failure from the worker loop
            logger.exception("ingestion job %s failed (worker %s)", job.job_id, worker_id)
            self._jobs.fail(job.job_id, str(e))
        finally:
            stop_heartbeat.set()
            hb_thread.join(timeout=5)

    def _run_reaper(self) -> None:
        # Runs at twice the heartbeat timeout's frequency so a stale claim
        # is never left unreclaimed for much longer than the timeout itself.
        while not self._stop.wait(max(1.0, self._heartbeat_timeout_s / 2)):
            try:
                n = self._jobs.reap_stale_claims(self._heartbeat_timeout_s)
                if n:
                    logger.warning("reaped %d stale ingestion job claim(s)", n)
            except Exception:
                logger.exception("reaper pass failed")
