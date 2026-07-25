from rag_hybrid_search.storage.repositories.scanning.chunk_repository import ScanningChunkRepository
from rag_hybrid_search.storage.repositories.scanning.document_repository import ScanningDocumentRepository


class ScanningIngestionUnitOfWork:
    """Implements IngestionUnitOfWork with no transaction -- both
    repositories' writes are no-ops (see their docstrings), so there's
    nothing to commit or roll back. Used when no Postgres database is
    configured.
    """

    def __init__(self, documents: ScanningDocumentRepository, chunks: ScanningChunkRepository):
        self.documents = documents
        self.chunks = chunks

    def __enter__(self) -> "ScanningIngestionUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass
