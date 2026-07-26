from rag_hybrid_search.storage.base import ChunkStore
from rag_hybrid_search.storage.repositories.base import ComplianceCandidate


class ScanningComplianceRepository:
    """Implements ComplianceRepository by delegating to
    ChunkStore.get_by_legal_metadata()/update_legal_metadata() -- the
    original full-corpus-scan behavior, used when no Postgres database is
    configured."""

    def __init__(self, chunk_store: ChunkStore):
        self._chunk_store = chunk_store

    def find_matching(self, filters: dict[str, str]) -> list[ComplianceCandidate]:
        chunks = self._chunk_store.get_by_legal_metadata(filters)
        return [
            ComplianceCandidate(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                effective_date=c.legal_metadata.effective_date if c.legal_metadata else None,
                is_current=c.legal_metadata.is_current if c.legal_metadata else True,
            )
            for c in chunks
        ]

    def mark_superseded(self, chunk_id: str, is_current: bool, superseded_by: str | None) -> None:
        self._chunk_store.update_legal_metadata(chunk_id, is_current=is_current, superseded_by=superseded_by)
