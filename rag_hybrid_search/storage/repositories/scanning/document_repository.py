from rag_hybrid_search.storage.base import ChunkStore


class ScanningDocumentRepository:
    """Implements DocumentRepository by delegating to ChunkStore.get_document_hash()
    -- the original full-corpus-scan behavior, used when no Postgres database
    is configured (Settings.supabase_db_url unset). Exists so IngestionPipeline
    never branches on "is Postgres configured" -- it always gets a
    DocumentRepository, this is just the slow one.

    record() is a no-op: without Postgres there's nowhere to persist a
    document row: for this fallback, chunk_store IS the source of truth,
    same as before this repository layer existed.
    """

    def __init__(self, chunk_store: ChunkStore):
        self._chunk_store = chunk_store

    def get_hash_for_path(self, source_path: str) -> str | None:
        return self._chunk_store.get_document_hash(source_path)

    def record(self, document_id: str, source_path: str, format: str) -> None:
        pass
