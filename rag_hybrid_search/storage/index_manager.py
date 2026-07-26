import logging
import uuid

from rag_hybrid_search.audit import AuditEvent, AuditLog, now_utc
from rag_hybrid_search.models import Chunk, EmbeddingRecord, IndexStatus
from rag_hybrid_search.storage.base import ChunkStore, VectorStore
from rag_hybrid_search.storage.bm25_index import BM25Index
from rag_hybrid_search.storage.repositories.base import BM25Repository, ComplianceRepository

logger = logging.getLogger(__name__)


class IndexManager:
    def __init__(
        self,
        chunk_store: ChunkStore,
        vector_store: VectorStore,
        bm25_index: BM25Index,
        bm25_repository: BM25Repository,
        compliance_repository: ComplianceRepository,
        audit_log: AuditLog | None = None,
    ):
        self.chunk_store = chunk_store
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        # Incremental BM25 postings + indexed compliance lookups (see
        # storage/repositories/). Postgres-backed or the scanning fallback
        # wrapping bm25_index/chunk_store's original full-scan behavior --
        # IndexManager never knows which.
        self.bm25_repository = bm25_repository
        self.compliance_repository = compliance_repository
        self.audit_log = audit_log

    def index(
        self, chunks: list[Chunk], embeddings: list[EmbeddingRecord], rebuild_bm25: bool = True,
    ) -> IndexStatus:
        try:
            self.vector_store.upsert_many([c.chunk_id for c in chunks], embeddings)
            # Incremental postings for these chunks specifically -- O(new
            # chunks), always current after this call regardless of
            # rebuild_bm25 (which now only controls whether the scanning
            # fallback's local pickle gets rebuilt; see rebuild_bm25_index()).
            self.bm25_repository.record_many(chunks)
            if rebuild_bm25:
                self.rebuild_bm25_index()
        except Exception:
            # Previously swallowed silently with no log at all -- meant a
            # real vector_store/chunk_store write failure (Pinecone or
            # otherwise) produced zero trace of what went wrong, only the
            # generic FAILED status the caller sees.
            logger.exception("IndexManager.index() failed")
            return IndexStatus.FAILED
        self._detect_and_mark_superseded(chunks)
        return IndexStatus.READY

    def remove_document(self, document_id: str, rebuild_bm25: bool = True) -> None:
        chunks = self.chunk_store.get_by_document(document_id)
        chunk_ids = [c.chunk_id for c in chunks]
        self.chunk_store.delete_by_document(document_id)
        if chunk_ids:
            self.vector_store.delete(chunk_ids)
            self.bm25_repository.remove_chunks(chunk_ids)
        if rebuild_bm25:
            self.rebuild_bm25_index()

    def rebuild_bm25_index(self) -> None:
        # Lazy provider, not a materialized list: the Postgres-backed
        # repository's rebuild_full() is a documented no-op that never
        # calls this, so no full-corpus Pinecone scan happens here for that
        # backend. The scanning fallback (no incremental API in rank_bm25)
        # does call it -- that's what actually makes newly-ingested chunks
        # searchable for that backend, same full-corpus cost as before this
        # repository layer existed.
        self.bm25_repository.rebuild_full(self.chunk_store.all)

    def rebuild_all(self) -> None:
        self.rebuild_bm25_index()

    def _detect_and_mark_superseded(self, chunks: list[Chunk]) -> None:
        """Compares each newly-indexed compliance chunk against any other
        indexed chunk sharing the same regulation/authority/jurisdiction/
        article/section/clause identity, and flips is_current/superseded_by
        so only the chunk with the latest effective_date stays current.

        Skipped entirely for chunks with no legal_metadata, no regulation,
        no effective_date, or no article/section -- i.e. every non-compliance
        document behaves exactly as it did before this method existed.
        """
        seen_keys: set[tuple] = set()
        for chunk in chunks:
            lm = chunk.legal_metadata
            if not lm or not lm.regulation or not lm.effective_date or not (lm.article or lm.section):
                continue
            key = (lm.regulation, lm.authority, lm.jurisdiction, lm.article, lm.section, lm.clause)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            field_names = ("regulation", "authority", "jurisdiction", "article", "section", "clause")
            filters = {name: value for name, value in zip(field_names, key) if value is not None}
            # Indexed lookup against the composite index on
            # chunks(organization_id, legal_regulation, ..., legal_clause) --
            # bounded by how many versions of this one clause exist, not
            # corpus size (see storage/repositories/postgres/compliance_repository.py).
            candidates = self.compliance_repository.find_matching(filters)
            dated = [c for c in candidates if c.effective_date is not None]
            if len(dated) < 2:
                continue

            latest_date = max(c.effective_date for c in dated)
            latest_doc_ids = {c.document_id for c in dated if c.effective_date == latest_date}
            # Ambiguous (two docs share the latest date): leave is_current as-is
            # rather than guessing which one wins.
            winner_doc_id = next(iter(latest_doc_ids)) if len(latest_doc_ids) == 1 else None
            if winner_doc_id is None:
                continue

            for candidate in dated:
                should_be_current = candidate.document_id == winner_doc_id
                if candidate.is_current != should_be_current:
                    self.compliance_repository.mark_superseded(
                        candidate.chunk_id,
                        is_current=should_be_current,
                        superseded_by=None if should_be_current else winner_doc_id,
                    )
                    if self.audit_log is not None and not should_be_current:
                        self.audit_log.record(
                            AuditEvent(
                                event_id=str(uuid.uuid4()),
                                event_type="supersession",
                                timestamp=now_utc(),
                                request_id="internal",
                                key_id="system",
                                endpoint="internal:index_manager",
                                action="mark_superseded",
                                status="success",
                                document_id=candidate.document_id,
                                regulation_metadata={**filters, "superseded_by": winner_doc_id},
                            )
                        )

    def verify_sync(self) -> list[str]:
        chunk_ids = {c.chunk_id for c in self.chunk_store.all()}
        bm25_ids = set(self.bm25_index._chunk_ids)
        return sorted(chunk_ids.symmetric_difference(bm25_ids))
