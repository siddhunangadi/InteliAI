"""Postgres-backed dedup index (see docs/superpowers/plans -- Problem 1 & 3
of the storage redesign).

Replaces two full-corpus operations in ``IngestionPipeline.ingest()`` with
indexed lookups against Supabase/Postgres:

- ``get_document_hash``: was ``chunk_store.get_document_hash()``, a full
  paginated scan of the whole Pinecone index. Here it's a single indexed
  ``SELECT`` on ``documents(organization_id, source_path)``.
- ``filter_new_chunk_hashes``: new. Exact-duplicate chunks (identical text,
  e.g. a boilerplate clause repeated across documents) are now caught by an
  O(1) unique-index lookup on ``chunks(organization_id, chunk_hash)`` before
  the O(new x existing) vectorized cosine-similarity dedup ever runs on
  them, shrinking that pass's input size for near-duplicate-but-not-exact
  chunks.

This does not replace ``ChunkStore`` (chunk text/embeddings still live in
Pinecone) -- it's an optional accelerator ``IngestionPipeline`` uses when
configured, and a no-op fallback to the old full-scan behavior when it
isn't (``Settings.supabase_db_url`` unset).
"""

import hashlib
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row


def chunk_hash(text: str) -> str:
    """SHA256 of chunk text, normalized (stripped) so trailing-whitespace
    differences from re-parsing the same PDF don't defeat exact-dup detection."""
    return hashlib.sha256(text.strip().encode()).hexdigest()


class PostgresDedupIndex:
    def __init__(self, dsn: str, organization_id: str):
        self._dsn = dsn
        self._organization_id = organization_id

    @contextmanager
    def _conn(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            yield conn

    def get_document_hash(self, source_path: str) -> str | None:
        """Return the content_hash currently indexed for this path, or None
        if this path has never been ingested. O(1) indexed lookup, replacing
        a full-corpus Pinecone scan."""
        with self._conn() as conn:
            row = conn.execute(
                """
                select content_hash from documents
                where organization_id = %s and source_path = %s and status != 'superseded'
                order by created_at desc limit 1
                """,
                (self._organization_id, source_path),
            ).fetchone()
        return row["content_hash"] if row else None

    def record_document(self, document_id: str, source_path: str, format: str) -> None:
        """Upsert the document row after a successful ingest -- document_id
        doubles as content_hash (see loaders/base.py: sha256 of content)."""
        with self._conn() as conn:
            conn.execute(
                """
                insert into documents (organization_id, source_path, format, content_hash, status)
                values (%s, %s, %s, %s, 'indexed')
                on conflict (organization_id, content_hash) do update
                    set status = 'indexed', updated_at = now()
                """,
                (self._organization_id, source_path, format, document_id),
            )
            conn.commit()

    def filter_new_chunk_hashes(self, hashes: list[str]) -> set[str]:
        """Given candidate chunk hashes, return the subset NOT already
        present in this org's corpus -- i.e. the ones worth running through
        the (expensive) near-duplicate check at all. O(len(hashes)) indexed
        lookup, not O(corpus size)."""
        if not hashes:
            return set()
        with self._conn() as conn:
            rows = conn.execute(
                "select chunk_hash from chunks where organization_id = %s and chunk_hash = any(%s)",
                (self._organization_id, hashes),
            ).fetchall()
        existing = {r["chunk_hash"] for r in rows}
        return set(hashes) - existing

    def record_chunks(self, document_id: str, chunks: list[tuple[str, str, str, int | None]]) -> None:
        """Record (chunk_id, chunk_hash, text, chunk_index) for each newly
        stored chunk, so future ingests' exact-dup lookups see them."""
        if not chunks:
            return
        with self._conn() as conn:
            conn.executemany(
                """
                insert into chunks (id, document_id, organization_id, chunk_index, text, chunk_hash, embedding_status)
                values (%s, %s, %s, %s, %s, %s, 'upserted')
                on conflict (organization_id, chunk_hash) do nothing
                """,
                [
                    (chunk_id, document_id, self._organization_id, chunk_index, text, chash)
                    for chunk_id, chash, text, chunk_index in chunks
                ],
            )
            conn.commit()
