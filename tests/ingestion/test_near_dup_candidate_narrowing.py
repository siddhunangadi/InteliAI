"""Proves IngestionPipeline's near-duplicate check no longer scans the
whole corpus (audit finding #3) when the ChunkRepository can narrow
candidates via LSH bands, and still falls back to the old full-scan
behavior when it can't (the scanning fallback)."""


from rag_hybrid_search.ingestion.chunkers.fixed import FixedChunker
from rag_hybrid_search.ingestion.loaders.text import TextLoader
from rag_hybrid_search.ingestion.pipeline import IngestionPipeline
from rag_hybrid_search.storage.repositories.base import ChunkRecord
from tests.fakes import FakeEmbeddingProvider, build_index_manager, fake_pinecone_stores


class _CountingChunkStore:
    """Wraps a real fake chunk_store, counting how many times the O(corpus)
    all_with_embeddings() scan is invoked vs. the targeted get_many_with_embeddings()."""

    def __init__(self, inner):
        self._inner = inner
        self.all_with_embeddings_calls = 0
        self.get_many_calls = 0

    def all_with_embeddings(self):
        self.all_with_embeddings_calls += 1
        return self._inner.all_with_embeddings()

    def get_many_with_embeddings(self, chunk_ids):
        self.get_many_calls += 1
        return self._inner.get_many_with_embeddings(chunk_ids)

    def __getattr__(self, name):
        return getattr(self._inner, name)


class _NarrowingChunkRepository:
    """Reports a fixed, small candidate set regardless of corpus size --
    stands in for PostgresChunkRepository's LSH-band-backed lookup without
    needing a real database."""

    def __init__(self, candidate_ids: set[str]):
        self._candidate_ids = candidate_ids
        self.recorded: list[ChunkRecord] = []

    def filter_new_hashes(self, hashes):
        return set(hashes)

    def record_many(self, document_id, chunks):
        self.recorded.extend(chunks)

    def find_near_duplicate_candidates(self, simhash):
        return self._candidate_ids


class _NoNarrowingChunkRepository:
    """The scanning fallback's contract: no LSH support, always signals
    "fall back to full scan" via None."""

    def filter_new_hashes(self, hashes):
        return set(hashes)

    def record_many(self, document_id, chunks):
        pass

    def find_near_duplicate_candidates(self, simhash):
        return None


class _NoOpDocumentRepository:
    def get_hash_for_path(self, source_path):
        return None

    def record(self, document_id, source_path, format):
        pass


class _NoOpUnitOfWork:
    def __init__(self, documents, chunks):
        self.documents = documents
        self.chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def _build_pipeline(tmp_path, chunk_repository):
    chunk_store, vector_store = fake_pinecone_stores()
    from rag_hybrid_search.storage.bm25_index import BM25Index

    bm25 = BM25Index(index_path=str(tmp_path / "bm25.pkl"))
    index_manager = build_index_manager(chunk_store, vector_store, bm25)
    documents = _NoOpDocumentRepository()
    uow = _NoOpUnitOfWork(documents, chunk_repository)
    counting_store = _CountingChunkStore(chunk_store)
    pipeline = IngestionPipeline(
        loader=TextLoader(),
        chunker=FixedChunker(chunk_size=200, chunk_overlap=0),
        embedding_provider=FakeEmbeddingProvider(),
        chunk_store=counting_store,
        index_manager=index_manager,
        dedup_cosine_threshold=0.95,
        dedup_text_threshold=0.9,
        document_repository=documents,
        chunk_repository=chunk_repository,
        ingestion_uow=uow,
    )
    return pipeline, counting_store, chunk_store


def _seed_existing_chunk(chunk_store, embedding_provider, tmp_path, text: str):
    """Ingest one prior chunk directly against chunk_store so there's an
    existing corpus entry the near-dup check could (wrongly) scan."""
    from rag_hybrid_search.models import Chunk

    chunk = Chunk(
        chunk_id="existing-chunk-1", document_id="doc-existing", chunk_index=0,
        text=text, strategy_version="fixed-v1", char_count=len(text),
    )
    chunk_store.put(chunk, source_path="/existing.txt")
    embedding = embedding_provider.embed([text])[0]
    from rag_hybrid_search.models import EmbeddingRecord
    from datetime import datetime, timezone

    chunk_store.put_many_with_embeddings(
        [chunk],
        [EmbeddingRecord(
            chunk_id=chunk.chunk_id, embedding=embedding, embedding_model="fake",
            embedding_dimension=len(embedding), provider="fake", created_at=datetime.now(timezone.utc),
        )],
    )


def test_narrowed_candidates_skip_full_corpus_scan(tmp_path):
    embedding_provider = FakeEmbeddingProvider()
    chunk_repository = _NarrowingChunkRepository(candidate_ids={"existing-chunk-1"})
    pipeline, counting_store, chunk_store = _build_pipeline(tmp_path, chunk_repository)
    _seed_existing_chunk(chunk_store, embedding_provider, tmp_path, "The quick brown fox jumps over the lazy dog")

    path = tmp_path / "new.txt"
    path.write_text("Some genuinely new, unrelated content about quarterly revenue.")
    pipeline.ingest(str(path))

    assert counting_store.get_many_calls >= 1
    assert counting_store.all_with_embeddings_calls == 0, (
        "narrowed candidate lookup must not fall back to the O(corpus) scan"
    )


def test_no_narrowing_support_falls_back_to_full_scan(tmp_path):
    chunk_repository = _NoNarrowingChunkRepository()
    pipeline, counting_store, chunk_store = _build_pipeline(tmp_path, chunk_repository)
    _seed_existing_chunk(chunk_store, FakeEmbeddingProvider(), tmp_path, "The quick brown fox jumps over the lazy dog")

    path = tmp_path / "new.txt"
    path.write_text("Some genuinely new, unrelated content about quarterly revenue.")
    pipeline.ingest(str(path))

    assert counting_store.all_with_embeddings_calls >= 1, (
        "scanning fallback (find_near_duplicate_candidates -> None) must still work correctly"
    )
