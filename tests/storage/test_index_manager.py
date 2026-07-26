from datetime import datetime, timezone

import pytest

from rag_hybrid_search.models import Chunk, EmbeddingRecord, IndexStatus
from rag_hybrid_search.storage.bm25_index import BM25Index
from tests.fakes import build_index_manager, fake_pinecone_stores


def make_chunk(chunk_id, document_id="d1", text="hello world"):
    return Chunk(
        chunk_id=chunk_id,
        document_id=document_id,
        chunk_index=0,
        text=text,
        strategy_version="fixed-v1",
        heading=None,
        page=None,
        char_count=len(text),
    )


def make_record(chunk_id, embedding=(1.0, 0.0, 0.0)):
    return EmbeddingRecord(
        chunk_id=chunk_id,
        embedding=list(embedding),
        embedding_model="test-model",
        embedding_dimension=len(embedding),
        provider="test",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def manager(tmp_path):
    chunk_store, vector_store = fake_pinecone_stores(embedding_dimension=3)
    bm25 = BM25Index(index_path=str(tmp_path / "bm25.pkl"))
    return build_index_manager(chunk_store, vector_store, bm25)


def test_index_writes_to_all_stores(manager):
    chunk = make_chunk("c1")
    manager.chunk_store.put(chunk, source_path="/docs/a.md")

    status = manager.index([chunk], [make_record("c1")])

    assert status == IndexStatus.READY
    assert manager.vector_store.query([1.0, 0.0, 0.0], k=1)[0][0] == "c1"
    assert manager.bm25_index.search("hello", k=1)[0][0] == "c1"


def test_remove_document_clears_both_indexes(manager):
    chunk = make_chunk("c1", document_id="d1")
    manager.chunk_store.put(chunk, source_path="/docs/a.md")
    manager.index([chunk], [make_record("c1")])

    manager.remove_document("d1")

    assert manager.chunk_store.get("c1") is None
    assert manager.vector_store.query([1.0, 0.0, 0.0], k=1) == []
    assert manager.bm25_index.search("hello", k=1) == []


def test_verify_sync_reports_no_mismatches_when_healthy(manager):
    chunk = make_chunk("c1")
    manager.chunk_store.put(chunk, source_path="/docs/a.md")
    manager.index([chunk], [make_record("c1")])

    assert manager.verify_sync() == []


def test_verify_sync_detects_bm25_drift(manager):
    chunk = make_chunk("c1")
    manager.chunk_store.put(chunk, source_path="/docs/a.md")
    manager.index([chunk], [make_record("c1")])

    # Simulate drift: rebuild BM25 from an empty chunk list directly,
    # bypassing IndexManager, so ChunkStore and BM25Index disagree.
    manager.bm25_index.build([])

    assert manager.verify_sync() == ["c1"]


def test_postgres_backed_bm25_repository_never_triggers_full_corpus_scan():
    """The core Problem-1/Problem-2 claim for IndexManager: with an
    incremental BM25Repository, index()'s default rebuild_bm25=True must
    never force a full chunk_store.all() scan just to discard the result."""
    from rag_hybrid_search.storage.index_manager import IndexManager

    class _NeverScanChunkStore:
        """Referencing .all (the bound method, to pass as a lazy provider)
        is fine and expected; actually CALLING it is the O(corpus) scan
        this test asserts never happens for an incremental backend."""

        def all(self):
            raise AssertionError("chunk_store.all() must not be called for an incremental BM25 backend")

    class _IncrementalNoOpBM25Repository:
        """Mirrors PostgresBM25Repository's contract: rebuild_full() never
        calls its get_chunks provider, because record_many() (called
        separately, per new chunks) already keeps postings current."""

        def __init__(self):
            self.recorded: list = []

        def record_many(self, chunks):
            self.recorded.extend(chunks)

        def remove_chunks(self, chunk_ids):
            pass

        def rebuild_full(self, get_chunks):
            pass  # deliberately never calls get_chunks()

        def search(self, query, k):
            return []

    chunk_store, vector_store = fake_pinecone_stores()
    bm25_index = BM25Index(index_path="/dev/null/unused.pkl")
    bm25_repository = _IncrementalNoOpBM25Repository()
    manager = IndexManager(
        chunk_store, vector_store, bm25_index,
        bm25_repository=bm25_repository,
        compliance_repository=None,  # not exercised by this test
    )
    manager.chunk_store = _NeverScanChunkStore()  # only rebuild_bm25_index() should touch chunk_store here

    chunk = make_chunk("c1")
    manager.index([chunk], [make_record("c1")])  # rebuild_bm25=True (default)

    assert bm25_repository.recorded == [chunk]
