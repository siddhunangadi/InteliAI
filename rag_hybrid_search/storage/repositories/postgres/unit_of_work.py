from contextlib import contextmanager

from rag_hybrid_search.storage.repositories.postgres.chunk_repository import PostgresChunkRepository
from rag_hybrid_search.storage.repositories.postgres.connection import PostgresConnectionPool
from rag_hybrid_search.storage.repositories.postgres.document_repository import PostgresDocumentRepository


@contextmanager
def _yield_without_closing(conn):
    yield conn


class _FixedConnection:
    """ConnectionProvider that always yields the same open connection --
    used so the document/chunk repositories inside one unit-of-work share a
    single transaction instead of each grabbing their own pooled connection."""

    def __init__(self, conn):
        self._conn = conn

    def connection(self):
        return _yield_without_closing(self._conn)


class PostgresIngestionUnitOfWork:
    """Implements IngestionUnitOfWork: entering opens one connection from
    the shared pool and holds it for the duration of the ``with`` block;
    exiting commits (or rolls back, on exception) and returns the
    connection to the pool -- so a document row and its chunk rows are
    written atomically, never partially.

    Re-entrant: the same instance is reused across ingest() calls, each
    ``with`` block acquiring a fresh connection from the pool.
    """

    def __init__(self, pool: PostgresConnectionPool, organization_id: str):
        self._pool = pool
        self._organization_id = organization_id
        self._conn_ctx = None
        self.documents: PostgresDocumentRepository | None = None
        self.chunks: PostgresChunkRepository | None = None

    def __enter__(self) -> "PostgresIngestionUnitOfWork":
        self._conn_ctx = self._pool.raw_connection_context()
        conn = self._conn_ctx.__enter__()
        provider = _FixedConnection(conn)
        self.documents = PostgresDocumentRepository(provider, self._organization_id)
        self.chunks = PostgresChunkRepository(provider, self._organization_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Delegates commit-on-success / rollback-on-exception / release to
        # the pool's own connection() context manager (psycopg_pool's
        # default transaction semantics for a checked-out connection).
        self._conn_ctx.__exit__(exc_type, exc_val, exc_tb)
        self._conn_ctx = None
        self.documents = None
        self.chunks = None
