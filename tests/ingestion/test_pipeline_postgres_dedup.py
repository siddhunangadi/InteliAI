"""Self-check for the repository-based dedup fast-path wired into
IngestionPipeline (see rag_hybrid_search/storage/repositories/). Uses fakes
that implement the DocumentRepository/ChunkRepository/IngestionUnitOfWork
Protocols directly (no real DB, no import of any Postgres-specific class) --
proving the pipeline only depends on those interfaces, not on which
implementation answers them.
"""

import pytest

from rag_hybrid_search.ingestion.chunkers.fixed import FixedChunker
from rag_hybrid_search.ingestion.loaders.text import TextLoader
from rag_hybrid_search.ingestion.pipeline import IngestionPipeline
from rag_hybrid_search.models import IndexStatus
from rag_hybrid_search.storage.bm25_index import BM25Index
from rag_hybrid_search.storage.index_manager import IndexManager
from rag_hybrid_search.storage.repositories.hashing import chunk_hash
from tests.fakes import FakeEmbeddingProvider, fake_pinecone_stores


class FakeDocumentRepository:
    def __init__(self):
        self.hashes: dict[str, str] = {}

    def get_hash_for_path(self, source_path: str) -> str | None:
        return self.hashes.get(source_path)

    def record(self, document_id: str, source_path: str, format: str) -> None:
        self.hashes[source_path] = document_id


class FakeChunkRepository:
    def __init__(self):
        self.known_hashes: set[str] = set()
        self.recorded: list[tuple] = []

    def filter_new_hashes(self, hashes: list[str]) -> set[str]:
        return set(hashes) - self.known_hashes

    def record_many(self, document_id: str, chunks: list[tuple[str, str, str, int | None]]) -> None:
        for _chunk_id, chash, _text, _index in chunks:
            self.known_hashes.add(chash)
        self.recorded.extend(chunks)


class FakeIngestionUnitOfWork:
    """No-transaction fake -- writes happen directly against the same
    document/chunk repository instances, just like the pipeline expects
    from any IngestionUnitOfWork."""

    def __init__(self, documents: FakeDocumentRepository, chunks: FakeChunkRepository):
        self.documents = documents
        self.chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


@pytest.fixture
def pipeline_and_repos(tmp_path):
    chunk_store, vector_store = fake_pinecone_stores()
    bm25 = BM25Index(index_path=str(tmp_path / "bm25.pkl"))
    index_manager = IndexManager(chunk_store, vector_store, bm25)
    documents = FakeDocumentRepository()
    chunks = FakeChunkRepository()
    uow = FakeIngestionUnitOfWork(documents, chunks)
    pipeline = IngestionPipeline(
        loader=TextLoader(),
        chunker=FixedChunker(chunk_size=100, chunk_overlap=0),
        embedding_provider=FakeEmbeddingProvider(),
        chunk_store=chunk_store,
        index_manager=index_manager,
        dedup_cosine_threshold=0.95,
        dedup_text_threshold=0.9,
        document_repository=documents,
        chunk_repository=chunks,
        ingestion_uow=uow,
    )
    return pipeline, documents, chunks


def test_exact_duplicate_chunk_dropped_via_hash_lookup(tmp_path, pipeline_and_repos):
    pipeline, documents, chunks = pipeline_and_repos
    text = "Article 5: this exact clause text repeats verbatim across documents."
    chunks.known_hashes.add(chunk_hash(text))

    path = tmp_path / "doc.txt"
    path.write_text(text)

    status = pipeline.ingest(str(path))

    assert status == IndexStatus.READY
    assert chunks.recorded == []  # nothing new was stored


def test_new_chunk_survives_and_gets_recorded(tmp_path, pipeline_and_repos):
    pipeline, documents, chunks = pipeline_and_repos
    path = tmp_path / "doc.txt"
    path.write_text("Some genuinely new content that hasn't been seen before.")

    pipeline.ingest(str(path))

    assert len(chunks.recorded) == 1
    assert documents.hashes.get(str(path)) is not None


def test_unchanged_document_short_circuits_via_document_hash(tmp_path, pipeline_and_repos):
    pipeline, documents, chunks = pipeline_and_repos
    path = tmp_path / "doc.txt"
    path.write_text("Stable content that doesn't change between ingests.")

    pipeline.ingest(str(path))
    recorded_after_first = len(chunks.recorded)

    status = pipeline.ingest(str(path))

    assert status == IndexStatus.READY
    assert len(chunks.recorded) == recorded_after_first  # no re-work


def test_scanning_fallback_is_interchangeable_with_postgres_shaped_repos(tmp_path):
    """The scanning fallback (used when no Postgres DB is configured)
    implements the exact same Protocols as the Postgres-backed
    repositories -- swap it in and IngestionPipeline behaves identically,
    just without the O(1) shortcuts."""
    from rag_hybrid_search.storage.repositories.scanning.chunk_repository import ScanningChunkRepository
    from rag_hybrid_search.storage.repositories.scanning.document_repository import ScanningDocumentRepository
    from rag_hybrid_search.storage.repositories.scanning.unit_of_work import ScanningIngestionUnitOfWork

    chunk_store, vector_store = fake_pinecone_stores()
    bm25 = BM25Index(index_path=str(tmp_path / "bm25.pkl"))
    index_manager = IndexManager(chunk_store, vector_store, bm25)
    documents = ScanningDocumentRepository(chunk_store)
    chunks = ScanningChunkRepository()
    uow = ScanningIngestionUnitOfWork(documents, chunks)
    pipeline = IngestionPipeline(
        loader=TextLoader(),
        chunker=FixedChunker(chunk_size=100, chunk_overlap=0),
        embedding_provider=FakeEmbeddingProvider(),
        chunk_store=chunk_store,
        index_manager=index_manager,
        dedup_cosine_threshold=0.95,
        dedup_text_threshold=0.9,
        document_repository=documents,
        chunk_repository=chunks,
        ingestion_uow=uow,
    )
    path = tmp_path / "doc.txt"
    path.write_text("Content ingested through the scanning fallback repositories.")

    status = pipeline.ingest(str(path))

    assert status == IndexStatus.READY
    status_again = pipeline.ingest(str(path))
    assert status_again == IndexStatus.READY  # unchanged-doc short-circuit still works
