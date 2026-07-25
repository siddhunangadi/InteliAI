"""Repository interfaces the ingestion pipeline depends on.

``IngestionPipeline`` (and every future consumer -- retrieval, the worker
queue, compliance indexing) must only ever import from this module for its
storage dependencies, never from ``storage.repositories.postgres`` or
``storage.repositories.scanning`` directly. Those are implementations,
swapped in by the composition root (``api/dependencies.py``); the pipeline
calls repository methods and never knows which backend answered them
(Postgres-backed, or the full-scan fallback used when no database is
configured).

``DocumentRepository``/``ChunkRepository`` are used standalone for reads
(no transaction needed -- a lookup is atomic by itself). ``IngestionUnitOfWork``
groups the *write* side of an ingest -- recording a document and its chunks
together -- behind one transaction, so a crash between the two writes can't
leave a document row with no matching chunks. The same shape (a UnitOfWork
exposing one repository per aggregate touched in that transaction) is what
Problems 2-5 (BM25 postings, compliance metadata, audit log, job queue)
should extend, not reinvent.
"""

from typing import Protocol


class DocumentRepository(Protocol):
    def get_hash_for_path(self, source_path: str) -> str | None:
        """Return the content_hash currently indexed for this path, or None
        if it's never been ingested."""
        ...

    def record(self, document_id: str, source_path: str, format: str) -> None:
        """Upsert the document row for a successfully ingested document.
        document_id doubles as content_hash (see ingestion/loaders/base.py)."""
        ...


class ChunkRepository(Protocol):
    def filter_new_hashes(self, hashes: list[str]) -> set[str]:
        """Given candidate chunk hashes, return the subset not already
        present in the corpus -- the ones worth running through the (more
        expensive) near-duplicate check at all."""
        ...

    def record_many(
        self, document_id: str, chunks: list[tuple[str, str, str, int | None]]
    ) -> None:
        """Record (chunk_id, chunk_hash, text, chunk_index) for each newly
        stored chunk."""
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
