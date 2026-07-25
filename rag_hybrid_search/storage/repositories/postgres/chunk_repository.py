from psycopg.rows import dict_row

from rag_hybrid_search.storage.repositories.postgres.connection import ConnectionProvider


class PostgresChunkRepository:
    """Implements ChunkRepository (rag_hybrid_search/storage/repositories/base.py)
    against the ``chunks`` table. Takes a ConnectionProvider, not a DSN --
    never opens its own connection (see connection.py)."""

    def __init__(self, connection_provider: ConnectionProvider, organization_id: str):
        self._connections = connection_provider
        self._organization_id = organization_id

    def filter_new_hashes(self, hashes: list[str]) -> set[str]:
        if not hashes:
            return set()
        with self._connections.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                rows = cur.execute(
                    "select chunk_hash from chunks where organization_id = %s and chunk_hash = any(%s)",
                    (self._organization_id, hashes),
                ).fetchall()
        existing = {r["chunk_hash"] for r in rows}
        return set(hashes) - existing

    def record_many(
        self, document_id: str, chunks: list[tuple[str, str, str, int | None]]
    ) -> None:
        if not chunks:
            return
        with self._connections.connection() as conn:
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
