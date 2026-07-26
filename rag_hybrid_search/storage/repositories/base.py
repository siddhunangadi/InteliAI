"""Repository interfaces the ingestion pipeline and IndexManager depend on.

Neither must ever import from ``storage.repositories.postgres`` or
``storage.repositories.scanning`` directly -- those are implementations,
swapped in by the composition root (``api/dependencies.py``). Callers call
repository methods and never know which backend answered them.

``DocumentRepository``/``ChunkRepository`` are used standalone for reads (a
lookup is atomic by itself). ``IngestionUnitOfWork`` groups the *write* side
of an ingest -- recording a document and its chunks together -- behind one
transaction. ``BM25Repository`` and ``ComplianceRepository`` are used
standalone by ``IndexManager`` (not inside the ingestion transaction --
BM25/compliance updates are inherently secondary/eventual steps, same as
before this repository layer existed, just indexed instead of full-scan
now); each write they make (a postings upsert, a supersession flip) is
still atomic per call via the shared connection pool.
"""

from datetime import date
from typing import Callable, Iterator, NamedTuple, Protocol

from rag_hybrid_search.models import Chunk


class DocumentRepository(Protocol):
    def get_hash_for_path(self, source_path: str) -> str | None:
        """Return the content_hash currently indexed for this path, or None
        if it's never been ingested."""
        ...

    def record(self, document_id: str, source_path: str, format: str) -> None:
        """Upsert the document row for a successfully ingested document.
        document_id doubles as content_hash (see ingestion/loaders/base.py)."""
        ...


class ChunkRecord(NamedTuple):
    chunk: Chunk
    chunk_hash: str
    simhash: int


class ChunkRepository(Protocol):
    def filter_new_hashes(self, hashes: list[str]) -> set[str]:
        """Given candidate chunk hashes, return the subset not already
        present in the corpus -- the ones worth running through the (more
        expensive) near-duplicate check at all."""
        ...

    def record_many(self, document_id: str, chunks: list[ChunkRecord]) -> None:
        """Record each newly stored chunk (text, hash, simhash, legal
        metadata) so future ingests' exact-hash and near-dup lookups see
        them."""
        ...

    def find_near_duplicate_candidates(self, simhash: int) -> set[str] | None:
        """Return chunk_ids that share at least one LSH band with
        ``simhash`` -- i.e. likely near-duplicates, found via an indexed
        band lookup, not a full-corpus scan. Returns None if this backend
        can't narrow candidates (the scanning fallback), signaling the
        caller to fall back to comparing against the whole corpus."""
        ...


class IngestionUnitOfWork(Protocol):
    """Groups a document write + its chunk writes into one transaction.

    Usage: ``with ingestion_uow as uow: uow.documents.record(...); uow.chunks.record_many(...)``.
    Re-entrant -- the same instance is reused across ingest() calls, each
    ``with`` block its own transaction.
    """

    documents: DocumentRepository
    chunks: ChunkRepository

    def __enter__(self) -> "IngestionUnitOfWork": ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...


class BM25Repository(Protocol):
    def record_many(self, chunks: list[Chunk]) -> None:
        """Incrementally add postings + doc stats for these newly-indexed
        chunks, and update corpus-wide aggregate stats -- O(new chunks),
        never re-touches existing postings."""
        ...

    def remove_chunks(self, chunk_ids: list[str]) -> None:
        """Incrementally remove postings + doc stats for these chunk ids
        (a document being re-ingested/deleted), updating corpus stats."""
        ...

    def rebuild_full(self, get_chunks: Callable[[], Iterator[Chunk]]) -> None:
        """Rebuild the whole index from every chunk in the corpus.

        Takes a *lazy* provider, not a materialized list: an incremental
        backend never calls it (record_many()/remove_chunks() already keep
        it current, so IndexManager.rebuild_bm25_index() calling this on
        every ingest must not trigger a full-corpus fetch just to discard
        it). The scanning fallback (no incremental API in rank_bm25) does
        call it -- that's the only way it stays queryable at all, same
        full-corpus cost as before this repository layer existed.
        """
        ...

    def search(self, query: str, k: int) -> list[tuple[str, float]]:
        ...


class ComplianceCandidate(NamedTuple):
    chunk_id: str
    document_id: str
    effective_date: date | None
    is_current: bool


class ComplianceRepository(Protocol):
    def find_matching(self, filters: dict[str, str]) -> list[ComplianceCandidate]:
        """Chunks sharing the given regulation/authority/jurisdiction/
        article/section/clause identity, via an indexed lookup -- bounded
        by how many versions of that one clause exist, not corpus size."""
        ...

    def mark_superseded(self, chunk_id: str, is_current: bool, superseded_by: str | None) -> None:
        ...


JobStatus = str  # "queued" | "processing" | "ready" | "failed" | "dead_letter" | "cancelled"


class IngestionJob(NamedTuple):
    job_id: str
    status: JobStatus
    payload: dict
    result: dict | None
    error: str | None
    retry_count: int
    max_retries: int
    progress_current: int
    progress_total: int


class JobRepository(Protocol):
    """Persistent, claim-based ingestion job queue (Postgres ``ingestion_jobs``
    table). Replaces the old in-memory, single-process ``JobStore``:
    job state survives a restart and multiple worker threads/processes can
    safely claim from the same queue (``FOR UPDATE SKIP LOCKED``, no two
    workers ever claim the same row).
    """

    def enqueue(self, payload: dict, *, idempotency_key: str | None, priority: int = 0) -> tuple[str, bool]:
        """Insert a new queued job. If ``idempotency_key`` collides with an
        existing job for this organization, returns that job's id instead of
        inserting a duplicate. Returns (job_id, created) -- created=False on
        an idempotency-key hit."""
        ...

    def claim(self, worker_id: str) -> IngestionJob | None:
        """Atomically claim the highest-priority, oldest eligible queued job
        (``available_at <= now()``), or None if the queue is empty. Sets
        status='processing', records worker_id, starts the heartbeat."""
        ...

    def heartbeat(self, job_id: str) -> None:
        """Extend a claimed job's liveness so the reaper doesn't reclaim it
        mid-processing."""
        ...

    def complete(self, job_id: str, result: dict) -> None:
        ...

    def fail(self, job_id: str, error: str) -> None:
        """Record a failure. Requeues with exponential backoff
        (``available_at = now() + 2**retry_count`` seconds) if under
        max_retries, otherwise marks 'dead_letter'."""
        ...

    def cancel(self, job_id: str) -> bool:
        """Cancel a job that hasn't been claimed yet. Returns False (no-op)
        if the job is already processing/finished -- ingestion isn't
        cheaply interruptible mid-embedding-call, so cancellation only
        covers the queued window."""
        ...

    def get(self, job_id: str) -> IngestionJob | None:
        ...

    def reap_stale_claims(self, heartbeat_timeout_s: int) -> int:
        """Requeue any 'processing' job whose heartbeat is older than
        ``heartbeat_timeout_s`` -- recovers work claimed by a worker that
        crashed or was killed without a graceful shutdown. Returns the
        number reclaimed."""
        ...

    def list_dead_letter(self, limit: int = 100) -> list[IngestionJob]:
        ...
