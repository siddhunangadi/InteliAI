"""Proves the scanning fallback repositories (used when no Postgres
database is configured) reproduce the exact behavior IndexManager/
IngestionPipeline had before this repository layer existed."""

from rag_hybrid_search.storage.bm25_index import BM25Index
from rag_hybrid_search.storage.repositories.scanning.bm25_repository import ScanningBM25Repository
from rag_hybrid_search.storage.repositories.scanning.compliance_repository import ScanningComplianceRepository
from tests.fakes import fake_pinecone_stores


def _make_chunk(chunk_id, text="hello world", **legal_kwargs):
    from rag_hybrid_search.compliance.regulation_models import LegalMetadata
    from rag_hybrid_search.models import Chunk

    legal_metadata = None
    if legal_kwargs:
        legal_kwargs.setdefault("document_id", "d1")
        legal_metadata = LegalMetadata(document_title="t", **legal_kwargs)
    return Chunk(
        chunk_id=chunk_id, document_id=legal_kwargs.get("document_id", "d1"), chunk_index=0,
        text=text, strategy_version="fixed-v1", char_count=len(text), legal_metadata=legal_metadata,
    )


def test_scanning_bm25_repository_record_and_remove_are_noops(tmp_path):
    bm25_index = BM25Index(index_path=str(tmp_path / "bm25.pkl"))
    repo = ScanningBM25Repository(bm25_index)

    repo.record_many([_make_chunk("c1")])
    repo.remove_chunks(["c1"])

    # No local pickle rebuild happened as a side effect of these calls --
    # search() is still empty until rebuild_full() runs.
    assert repo.search("hello", k=1) == []


def test_scanning_bm25_repository_rebuild_full_makes_chunks_searchable(tmp_path):
    bm25_index = BM25Index(index_path=str(tmp_path / "bm25.pkl"))
    repo = ScanningBM25Repository(bm25_index)
    chunk = _make_chunk("c1", text="hello world")

    repo.rebuild_full(lambda: iter([chunk]))

    results = repo.search("hello", k=1)
    assert results and results[0][0] == "c1"


def test_scanning_compliance_repository_delegates_to_chunk_store():
    chunk_store, _ = fake_pinecone_stores()
    chunk = _make_chunk(
        "c1", document_id="d1", regulation="GDPR", authority="EU", jurisdiction="EU",
        article="5", effective_date="2023-01-01",
    )
    chunk_store.put(chunk, source_path="/a.pdf")
    repo = ScanningComplianceRepository(chunk_store)

    candidates = repo.find_matching({"regulation": "GDPR", "authority": "EU", "jurisdiction": "EU", "article": "5"})

    assert len(candidates) == 1
    assert candidates[0].chunk_id == "c1"
    assert candidates[0].document_id == "d1"
    assert candidates[0].is_current is True


def test_scanning_compliance_repository_mark_superseded_updates_chunk_store():
    chunk_store, _ = fake_pinecone_stores()
    chunk = _make_chunk(
        "c1", document_id="d1", regulation="GDPR", authority="EU", jurisdiction="EU",
        article="5", effective_date="2020-01-01",
    )
    chunk_store.put(chunk, source_path="/a.pdf")
    repo = ScanningComplianceRepository(chunk_store)

    repo.mark_superseded("c1", is_current=False, superseded_by="d2")

    updated = chunk_store.get("c1")
    assert updated.legal_metadata.is_current is False
    assert updated.legal_metadata.superseded_by == "d2"
