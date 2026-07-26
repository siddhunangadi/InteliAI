"""Unit tests for WorkerPool against an in-memory fake JobRepository (no
Postgres needed -- these exercise the concurrency/retry/heartbeat/reaper
logic in api/jobs.py, not JobRepository's SQL, which is covered separately
by tests/storage/test_job_repository.py against a real database)."""

import threading
import time
import uuid

import pytest

from api.jobs import WorkerPool
from rag_hybrid_search.storage.repositories.base import IngestionJob


class FakeJobRepository:
    """Thread-safe in-memory stand-in for PostgresJobRepository, implementing
    just enough of the Protocol for WorkerPool's claim/heartbeat/complete/
    fail/reap loop."""

    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: dict[str, dict] = {}
        self.claim_calls = 0

    def add(self, job_id: str, payload: dict, max_retries: int = 5) -> None:
        self._jobs[job_id] = {
            "status": "queued", "payload": payload, "result": None, "error": None,
            "retry_count": 0, "max_retries": max_retries,
            "progress_current": 0, "progress_total": 0, "heartbeat_count": 0,
        }

    def claim(self, worker_id: str):
        with self._lock:
            self.claim_calls += 1
            for job_id, job in self._jobs.items():
                if job["status"] == "queued":
                    job["status"] = "processing"
                    job["worker_id"] = worker_id
                    return IngestionJob(
                        job_id=job_id, status="processing", payload=job["payload"], result=None,
                        error=None, retry_count=job["retry_count"], max_retries=job["max_retries"],
                        progress_current=0, progress_total=0,
                    )
            return None

    def heartbeat(self, job_id: str) -> None:
        with self._lock:
            self._jobs[job_id]["heartbeat_count"] += 1

    def complete(self, job_id: str, result: dict) -> None:
        with self._lock:
            self._jobs[job_id]["status"] = "ready"
            self._jobs[job_id]["result"] = result

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["error"] = error
            if job["retry_count"] < job["max_retries"]:
                job["retry_count"] += 1
                job["status"] = "queued"
            else:
                job["status"] = "dead_letter"

    def reap_stale_claims(self, heartbeat_timeout_s: int) -> int:
        with self._lock:
            n = 0
            for job in self._jobs.values():
                if job["status"] == "processing" and job.get("_stale"):
                    job["status"] = "queued"
                    n += 1
            return n

    def status_of(self, job_id: str) -> str:
        with self._lock:
            return self._jobs[job_id]["status"]


def _wait_until(predicate, timeout=5.0, interval=0.02) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval)
    raise AssertionError("condition not met before timeout")


@pytest.fixture
def repo():
    return FakeJobRepository()


def _pool(repo, process, **overrides) -> WorkerPool:
    kwargs = dict(
        concurrency=2, heartbeat_interval_s=0.05, heartbeat_timeout_s=1, poll_interval_s=0.02,
    )
    kwargs.update(overrides)
    return WorkerPool(repo, process, **kwargs)


def test_worker_processes_a_queued_job(repo):
    job_id = str(uuid.uuid4())
    repo.add(job_id, {"n": 1})
    pool = _pool(repo, process=lambda payload: {"doubled": payload["n"] * 2})
    pool.start()
    try:
        _wait_until(lambda: repo.status_of(job_id) == "ready")
        assert repo._jobs[job_id]["result"] == {"doubled": 2}
    finally:
        pool.shutdown(wait_s=2)


def test_multiple_workers_process_jobs_concurrently(repo):
    job_ids = [str(uuid.uuid4()) for _ in range(6)]
    started = threading.Event()
    concurrent_count = {"current": 0, "max": 0}
    lock = threading.Lock()

    def process(payload):
        with lock:
            concurrent_count["current"] += 1
            concurrent_count["max"] = max(concurrent_count["max"], concurrent_count["current"])
        time.sleep(0.1)
        with lock:
            concurrent_count["current"] -= 1
        return {}

    for job_id in job_ids:
        repo.add(job_id, {})
    pool = _pool(repo, process=process, concurrency=3)
    pool.start()
    try:
        _wait_until(lambda: all(repo.status_of(j) == "ready" for j in job_ids), timeout=5)
        assert concurrent_count["max"] > 1  # actually ran overlapping, not serialized
    finally:
        pool.shutdown(wait_s=2)


def test_failed_job_is_retried_then_moved_to_dead_letter(repo):
    job_id = str(uuid.uuid4())
    repo.add(job_id, {}, max_retries=2)

    def always_fails(_payload):
        raise ValueError("boom")

    pool = _pool(repo, process=always_fails, concurrency=1)
    pool.start()
    try:
        _wait_until(lambda: repo.status_of(job_id) == "dead_letter", timeout=5)
        assert repo._jobs[job_id]["retry_count"] == 2
        assert repo._jobs[job_id]["error"] == "boom"
    finally:
        pool.shutdown(wait_s=2)


def test_heartbeat_is_recorded_while_a_job_runs(repo):
    job_id = str(uuid.uuid4())
    repo.add(job_id, {})

    def slow_process(_payload):
        time.sleep(0.3)
        return {}

    pool = _pool(repo, process=slow_process, concurrency=1, heartbeat_interval_s=0.05)
    pool.start()
    try:
        _wait_until(lambda: repo.status_of(job_id) == "ready", timeout=5)
        assert repo._jobs[job_id]["heartbeat_count"] > 0
    finally:
        pool.shutdown(wait_s=2)


def test_pause_stops_new_claims_until_resumed(repo):
    job_id = str(uuid.uuid4())
    repo.add(job_id, {})
    pool = _pool(repo, process=lambda p: {}, concurrency=1)
    pool.pause()
    pool.start()
    try:
        time.sleep(0.2)
        assert repo.status_of(job_id) == "queued"  # never claimed while paused
        pool.resume()
        _wait_until(lambda: repo.status_of(job_id) == "ready", timeout=5)
    finally:
        pool.shutdown(wait_s=2)


def test_reaper_requeues_a_stale_claim(repo):
    job_id = str(uuid.uuid4())
    repo.add(job_id, {})
    repo._jobs[job_id]["status"] = "processing"
    repo._jobs[job_id]["_stale"] = True

    pool = _pool(repo, process=lambda p: {}, concurrency=1, heartbeat_timeout_s=1)
    pool.start()
    try:
        _wait_until(lambda: repo._jobs[job_id]["status"] == "ready", timeout=5)
    finally:
        pool.shutdown(wait_s=2)
