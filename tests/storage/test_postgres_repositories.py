"""Integration tests for the Postgres-backed repositories, against a real
Supabase/Postgres database. Skipped unless RAG_SUPABASE_DB_URL is set --
this environment doesn't have the DB password (not retrievable via the
Supabase API/MCP for security; see .env.development for where to get it),
so these don't run in CI here, but are complete and correct against the
live schema (verified manually via the Supabase MCP's execute_sql during
development -- see the PR description for the verification transcript).

Each test uses its own random organization_id so tests can run concurrently
and clean up after themselves without affecting each other.
"""

import os
import uuid
from datetime import date

import pytest

from rag_hybrid_search.models import Chunk
from rag_hybrid_search.storage.repositories.base import ChunkRecord
from rag_hybrid_search.storage.repositories.hashing import chunk_hash, simhash
from rag_hybrid_search.storage.repositories.postgres.bm25_repository import PostgresBM25Repository
from rag_hybrid_search.storage.repositories.postgres.chunk_repository import PostgresChunkRepository
from rag_hybrid_search.storage.repositories.postgres.compliance_repository import PostgresComplianceRepository
from rag_hybrid_search.storage.repositories.postgres.connection import PostgresConnectionPool
from rag_hybrid_search.storage.repositories.postgres.document_repository import PostgresDocumentRepository

pytestmark = pytest.mark.skipif(
    not os.environ.get("RAG_SUPABASE_DB_URL"),
    reason="RAG_SUPABASE_DB_URL not set -- integration test needs a live Postgres database",
)


@pytest.fixture
def pool():
    p = PostgresConnectionPool(os.environ["RAG_SUPABASE_DB_URL"])
    yield p
    p.close()


@pytest.fixture
def organization_id(pool):
    org_id = str(uuid.uuid4())
    with pool.connection() as conn:
        conn.execute("insert into organizations (id, name) values (%s, %s)", (org_id, "test-org"))
    yield org_id
    with pool.connection() as conn:
        for table in (
            "chunk_simhash_bands", "bm25_postings", "bm25_doc_stats", "bm25_corpus_stats",
            "chunks", "documents",
        ):
            conn.execute(f"delete from {table} where organization_id = %s", (org_id,))
        conn.execute("delete from organizations where id = %s", (org_id,))


def _chunk(chunk_id, document_id, text, chunk_index=0, **legal_kwargs):
    legal_metadata = None
    if legal_kwargs:
        from rag_hybrid_search.compliance.regulation_models import LegalMetadata
        legal_metadata = LegalMetadata(document_id=document_id, document_title="t", **legal_kwargs)
    return Chunk(
        chunk_id=chunk_id, document_id=document_id, chunk_index=chunk_index,
        text=text, strategy_version="fixed-v1", char_count=len(text), legal_metadata=legal_metadata,
    )


def test_document_repository_records_and_looks_up_by_path(pool, organization_id):
    repo = PostgresDocumentRepository(pool, organization_id)
    assert repo.get_hash_for_path("/a.pdf") is None

    repo.record("doc-hash-1", "/a.pdf", "pdf")

    assert repo.get_hash_for_path("/a.pdf") == "doc-hash-1"


def test_chunk_repository_exact_hash_dedup_is_indexed(pool, organization_id):
    repo = PostgresChunkRepository(pool, organization_id)
    PostgresDocumentRepository(pool, organization_id).record("doc-1", "/a.txt", "text")
    chunk = _chunk(str(uuid.uuid4()), "doc-1", "the quick brown fox")
    chash = chunk_hash(chunk.text)
    shash = simhash(chunk.text)

    assert repo.filter_new_hashes([chash]) == {chash}

    repo.record_many("doc-1", [ChunkRecord(chunk=chunk, chunk_hash=chash, simhash=shash)])

    assert repo.filter_new_hashes([chash]) == set()  # now known, filtered out


def test_chunk_repository_near_duplicate_candidates_via_lsh_bands(pool, organization_id):
    repo = PostgresChunkRepository(pool, organization_id)
    doc_repo = PostgresDocumentRepository(pool, organization_id)
    doc_repo.record("doc-1", "/a.txt", "text")
    doc_repo.record("doc-2", "/b.txt", "text")
    original_text = "The quick brown fox jumps over the lazy dog in the park every morning"
    near_dup_text = "The quick brown fox jumps over the lazy dog at the park every morning"
    unrelated_text = "This is a completely unrelated sentence about baking sourdough bread"

    original = _chunk(str(uuid.uuid4()), "doc-1", original_text)
    unrelated = _chunk(str(uuid.uuid4()), "doc-2", unrelated_text)
    repo.record_many("doc-1", [ChunkRecord(chunk=original, chunk_hash=chunk_hash(original.text), simhash=simhash(original.text))])
    repo.record_many("doc-2", [ChunkRecord(chunk=unrelated, chunk_hash=chunk_hash(unrelated.text), simhash=simhash(unrelated.text))])

    candidates = repo.find_near_duplicate_candidates(simhash(near_dup_text))

    assert original.chunk_id in candidates
    assert unrelated.chunk_id not in candidates


def test_bm25_repository_incremental_record_and_search(pool, organization_id):
    repo = PostgresBM25Repository(pool, organization_id)
    chunk_repo = PostgresChunkRepository(pool, organization_id)
    doc_repo = PostgresDocumentRepository(pool, organization_id)
    doc_repo.record("doc-1", "/a.txt", "text")
    doc_repo.record("doc-2", "/b.txt", "text")
    fox_chunk = _chunk(str(uuid.uuid4()), "doc-1", "the quick brown fox jumps over the lazy dog")
    bread_chunk = _chunk(str(uuid.uuid4()), "doc-2", "completely unrelated sentence about baking bread")
    chunk_repo.record_many("doc-1", [ChunkRecord(chunk=fox_chunk, chunk_hash=chunk_hash(fox_chunk.text), simhash=simhash(fox_chunk.text))])
    chunk_repo.record_many("doc-2", [ChunkRecord(chunk=bread_chunk, chunk_hash=chunk_hash(bread_chunk.text), simhash=simhash(bread_chunk.text))])

    repo.record_many([fox_chunk, bread_chunk])

    results = repo.search("quick fox", k=10)
    result_ids = [chunk_id for chunk_id, _score in results]

    assert fox_chunk.chunk_id in result_ids
    assert bread_chunk.chunk_id not in result_ids


def test_bm25_repository_record_many_is_incremental_not_a_rebuild(pool, organization_id):
    """The core Problem-1 claim: adding a second document's chunks must not
    re-touch the first document's postings/stats -- corpus stats accumulate,
    they don't get recomputed from scratch."""
    repo = PostgresBM25Repository(pool, organization_id)
    chunk_repo = PostgresChunkRepository(pool, organization_id)
    doc_repo = PostgresDocumentRepository(pool, organization_id)
    doc_repo.record("doc-1", "/a.txt", "text")
    doc_repo.record("doc-2", "/b.txt", "text")
    first = _chunk(str(uuid.uuid4()), "doc-1", "alpha beta gamma")
    chunk_repo.record_many("doc-1", [ChunkRecord(chunk=first, chunk_hash=chunk_hash(first.text), simhash=simhash(first.text))])
    repo.record_many([first])

    with pool.connection() as conn:
        row = conn.execute(
            "select total_chunks, total_length from bm25_corpus_stats where organization_id = %s",
            (organization_id,),
        ).fetchone()
    assert row == (1, 3)

    second = _chunk(str(uuid.uuid4()), "doc-2", "delta epsilon")
    chunk_repo.record_many("doc-2", [ChunkRecord(chunk=second, chunk_hash=chunk_hash(second.text), simhash=simhash(second.text))])
    repo.record_many([second])

    with pool.connection() as conn:
        row = conn.execute(
            "select total_chunks, total_length from bm25_corpus_stats where organization_id = %s",
            (organization_id,),
        ).fetchone()
    assert row == (2, 5)  # accumulated, not recomputed


def test_bm25_repository_remove_chunks_decrements_corpus_stats(pool, organization_id):
    repo = PostgresBM25Repository(pool, organization_id)
    chunk_repo = PostgresChunkRepository(pool, organization_id)
    PostgresDocumentRepository(pool, organization_id).record("doc-1", "/a.txt", "text")
    chunk = _chunk(str(uuid.uuid4()), "doc-1", "alpha beta gamma")
    chunk_repo.record_many("doc-1", [ChunkRecord(chunk=chunk, chunk_hash=chunk_hash(chunk.text), simhash=simhash(chunk.text))])
    repo.record_many([chunk])

    repo.remove_chunks([chunk.chunk_id])

    with pool.connection() as conn:
        row = conn.execute(
            "select total_chunks, total_length from bm25_corpus_stats where organization_id = %s",
            (organization_id,),
        ).fetchone()
    assert row == (0, 0)
    assert repo.search("alpha", k=10) == []


def test_compliance_repository_find_matching_and_mark_superseded(pool, organization_id):
    repo = PostgresComplianceRepository(pool, organization_id)
    chunk_repo = PostgresChunkRepository(pool, organization_id)
    doc_repo = PostgresDocumentRepository(pool, organization_id)

    old = _chunk(
        str(uuid.uuid4()), "doc-v1", "old clause text",
        regulation="GDPR", authority="EU", jurisdiction="EU", article="5",
        effective_date=date(2020, 1, 1),
    )
    new = _chunk(
        str(uuid.uuid4()), "doc-v2", "new clause text",
        regulation="GDPR", authority="EU", jurisdiction="EU", article="5",
        effective_date=date(2023, 6, 1),
    )
    doc_repo.record("doc-v1", "/v1.pdf", "pdf")
    doc_repo.record("doc-v2", "/v2.pdf", "pdf")
    chunk_repo.record_many("doc-v1", [ChunkRecord(chunk=old, chunk_hash=chunk_hash(old.text), simhash=0)])
    chunk_repo.record_many("doc-v2", [ChunkRecord(chunk=new, chunk_hash=chunk_hash(new.text), simhash=0)])

    candidates = repo.find_matching({"regulation": "GDPR", "authority": "EU", "jurisdiction": "EU", "article": "5"})
    assert {c.document_id for c in candidates} == {"doc-v1", "doc-v2"}

    repo.mark_superseded(old.chunk_id, is_current=False, superseded_by="doc-v2")

    updated = repo.find_matching({"regulation": "GDPR", "authority": "EU", "jurisdiction": "EU", "article": "5"})
    old_row = next(c for c in updated if c.chunk_id == old.chunk_id)
    assert old_row.is_current is False


def test_compliance_repository_rejects_unknown_filter_key(pool, organization_id):
    repo = PostgresComplianceRepository(pool, organization_id)
    with pytest.raises(ValueError):
        repo.find_matching({"not_a_real_field": "x"})
