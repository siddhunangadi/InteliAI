"""Self-check for the Postgres dedup fast-path wired into IngestionPipeline
(see rag_hybrid_search/storage/postgres_dedup.py). Uses a fake in-process
PostgresDedupIndex (no real DB needed) to prove: (1) an exact-duplicate
chunk is dropped via the hash lookup without running the vectorized
near-dup check, and (2) get_document_hash short-circuits re-ingestion of an
unchanged path."""

import pytest

from rag_hybrid_search.ingestion.chunkers.fixed import FixedChunker
from rag_hybrid_search.ingestion.loaders.text import TextLoader
from rag_hybrid_search.ingestion.pipeline import IngestionPipeline
from rag_hybrid_search.models import IndexStatus
from rag_hybrid_search.storage.bm25_index import BM25Index
from rag_hybrid_search.storage.index_manager import IndexManager
from rag_hybrid_search.storage.postgres_dedup import chunk_hash
from tests.fakes import FakeEmbeddingProvider, fake_pinecone_stores


class FakePostgresDedupIndex:
    """Same interface as PostgresDedupIndex, backed by dicts instead of a
    real connection -- lets tests exercise the pipeline's dedup fast-path
    without a live Postgres instance."""

    def __init__(self):
        self.document_hashes: dict[str, str] = {}
        self.chunk_hashes: set[str] = set()
        self.recorded_chunks: list[tuple] = []

    def get_document_hash(self, source_path: str) -> str | None:
        return self.document_hashes.get(source_path)

    def record_document(self, document_id: str, source_path: str, format: str) -> None:
        self.document_hashes[source_path] = document_id

    def filter_new_chunk_hashes(self, hashes: list[str]) -> set[str]:
        return set(hashes) - self.chunk_hashes

    def record_chunks(self, document_id: str, chunks: list[tuple[str, str, str, int | None]]) -> None:
        for chunk_id, chash, text, chunk_index in chunks:
            self.chunk_hashes.add(chash)
        self.recorded_chunks.extend(chunks)


@pytest.fixture
def pipeline_and_dedup(tmp_path):
    chunk_store, vector_store = fake_pinecone_stores()
    bm25 = BM25Index(index_path=str(tmp_path / "bm25.pkl"))
    index_manager = IndexManager(chunk_store, vector_store, bm25)
    postgres_dedup = FakePostgresDedupIndex()
    pipeline = IngestionPipeline(
        loader=TextLoader(),
        chunker=FixedChunker(chunk_size=100, chunk_overlap=0),
        embedding_provider=FakeEmbeddingProvider(),
        chunk_store=chunk_store,
        index_manager=index_manager,
        dedup_cosine_threshold=0.95,
        dedup_text_threshold=0.9,
        postgres_dedup=postgres_dedup,
    )
    return pipeline, postgres_dedup


def test_exact_duplicate_chunk_dropped_via_hash_lookup(tmp_path, pipeline_and_dedup):
    pipeline, postgres_dedup = pipeline_and_dedup
    text = "Article 5: this exact clause text repeats verbatim across documents."
    postgres_dedup.chunk_hashes.add(chunk_hash(text))

    path = tmp_path / "doc.txt"
    path.write_text(text)

    status = pipeline.ingest(str(path))

    assert status == IndexStatus.READY
    assert postgres_dedup.recorded_chunks == []  # nothing new was stored


def test_new_chunk_survives_and_gets_recorded(tmp_path, pipeline_and_dedup):
    pipeline, postgres_dedup = pipeline_and_dedup
    path = tmp_path / "doc.txt"
    path.write_text("Some genuinely new content that hasn't been seen before.")

    pipeline.ingest(str(path))

    assert len(postgres_dedup.recorded_chunks) == 1
    assert postgres_dedup.document_hashes.get(str(path)) is not None


def test_unchanged_document_short_circuits_via_document_hash(tmp_path, pipeline_and_dedup):
    pipeline, postgres_dedup = pipeline_and_dedup
    path = tmp_path / "doc.txt"
    path.write_text("Stable content that doesn't change between ingests.")

    pipeline.ingest(str(path))
    recorded_after_first = len(postgres_dedup.recorded_chunks)

    status = pipeline.ingest(str(path))

    assert status == IndexStatus.READY
    assert len(postgres_dedup.recorded_chunks) == recorded_after_first  # no re-work
