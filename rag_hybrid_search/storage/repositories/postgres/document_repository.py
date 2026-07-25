from rag_hybrid_search.storage.repositories.postgres.connection import ConnectionProvider


class PostgresDocumentRepository:
    """Implements DocumentRepository (rag_hybrid_search/storage/repositories/base.py)
    against the ``documents`` table. Takes a ConnectionProvider, not a DSN --
    never opens its own connection (see connection.py)."""

    def __init__(self, connection_provider: ConnectionProvider, organization_id: str):
        self._connections = connection_provider
        self._organization_id = organization_id

    def get_hash_for_path(self, source_path: str) -> str | None:
        with self._connections.connection() as conn:
            row = conn.execute(
                """
                select content_hash from documents
                where organization_id = %s and source_path = %s and status != 'superseded'
                order by created_at desc limit 1
                """,
                (self._organization_id, source_path),
            ).fetchone()
            return row[0] if row is not None else None

    def record(self, document_id: str, source_path: str, format: str) -> None:
        with self._connections.connection() as conn:
            conn.execute(
                """
                insert into documents (organization_id, source_path, format, content_hash, status)
                values (%s, %s, %s, %s, 'indexed')
                on conflict (organization_id, content_hash) do update
                    set status = 'indexed', updated_at = now()
                """,
                (self._organization_id, source_path, format, document_id),
            )
