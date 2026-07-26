from __future__ import annotations


import hashlib
from types import SimpleNamespace

from rag_hybrid_search.providers.base import EmbeddingProvider, GenerationProvider
from rag_hybrid_search.storage.base import ChunkStore, VectorStore
from rag_hybrid_search.storage.bm25_index import BM25Index
from rag_hybrid_search.storage.index_manager import IndexManager
from rag_hybrid_search.storage.pinecone_chunk_store import PineconeChunkStore
from rag_hybrid_search.storage.pinecone_connection import PineconeConnection
from rag_hybrid_search.storage.pinecone_vector_store import PineconeVectorStore
from rag_hybrid_search.storage.repositories.scanning.bm25_repository import ScanningBM25Repository
from rag_hybrid_search.storage.repositories.scanning.chunk_repository import ScanningChunkRepository
from rag_hybrid_search.storage.repositories.scanning.compliance_repository import ScanningComplianceRepository
from rag_hybrid_search.storage.repositories.scanning.document_repository import ScanningDocumentRepository
from rag_hybrid_search.storage.repositories.scanning.unit_of_work import ScanningIngestionUnitOfWork


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic, dependency-free embedding stand-in for tests.

    Produces an 8-dim vector derived from character trigram hashes so that
    textually similar strings land close together in cosine space, which is
    enough to exercise dense retrieval and dedup logic without a real model.
    """

    _DIM = 8

    def embed(self, texts: list[str], input_type: str = "passage") -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self._DIM
        normalized = text.lower()
        for i in range(len(normalized) - 2):
            trigram = normalized[i : i + 3]
            digest = hashlib.sha256(trigram.encode()).digest()
            bucket = digest[0] % self._DIM
            vector[bucket] += 1.0
        norm = sum(v * v for v in vector) ** 0.5
        if norm == 0:
            return vector
        return [v / norm for v in vector]

    @property
    def model_name(self) -> str:
        return "fake-embedding-v1"

    @property
    def dimension(self) -> int:
        return self._DIM


class FakeGenerationProvider(GenerationProvider):
    def __init__(self, fixed_response: str = "fake response"):
        self._fixed_response = fixed_response

    def generate(self, prompt: str, **kwargs) -> str:
        return self._fixed_response


class FakePineconeIndex:
    """In-memory stand-in for a real Pinecone ``Index``, matching the subset
    of the client surface ``PineconeChunkStore``/``PineconeVectorStore`` call
    (``upsert``/``update``/``fetch``/``list``/``query``/``delete``).

    Unlike a bare ``MagicMock``, this actually stores vectors+metadata and
    answers ``query()`` with real cosine similarity, so tests that put a
    chunk and then expect to retrieve/rank it get real behavior instead of a
    canned mock response -- while staying fully hermetic (no network, no
    live Pinecone index needed).
    """

    def __init__(self):
        self._records: dict[str, dict] = {}

    def upsert(self, vectors: list[dict]) -> None:
        for v in vectors:
            self._records[v["id"]] = {
                "values": list(v["values"]),
                "metadata": dict(v.get("metadata") or {}),
            }

    def update(
        self, id: str, values: list[float] | None = None, set_metadata: dict | None = None,
    ) -> None:
        self._records.setdefault(id, {"values": [], "metadata": {}})
        if values is not None:
            self._records[id]["values"] = list(values)
        if set_metadata is not None:
            self._records[id]["metadata"].update(set_metadata)

    def fetch(self, ids: list[str]) -> SimpleNamespace:
        vectors = {
            cid: SimpleNamespace(
                metadata=self._records[cid]["metadata"],
                values=self._records[cid]["values"],
            )
            for cid in ids
            if cid in self._records
        }
        return SimpleNamespace(vectors=vectors)

    def list(self):
        ids = list(self._records.keys())
        yield SimpleNamespace(vectors=[SimpleNamespace(id=cid) for cid in ids])

    def describe_index_stats(self) -> SimpleNamespace:
        return SimpleNamespace(total_vector_count=len(self._records))

    def query(self, vector: list[float], top_k: int, include_metadata: bool = False) -> SimpleNamespace:
        def cosine(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(x * x for x in b) ** 0.5
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)

        scored = [
            (chunk_id, cosine(vector, record["values"]))
            for chunk_id, record in self._records.items()
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        matches = [SimpleNamespace(id=cid, score=score) for cid, score in scored[:top_k]]
        return SimpleNamespace(matches=matches)

    def delete(self, ids: list[str] | None = None, filter: dict | None = None) -> None:
        if ids:
            for cid in ids:
                self._records.pop(cid, None)
            return
        if filter:
            document_id = filter.get("document_id", {}).get("$eq")
            to_delete = [
                cid for cid, record in self._records.items()
                if record["metadata"].get("document_id") == document_id
            ]
            for cid in to_delete:
                del self._records[cid]


def fake_pinecone_stores(embedding_dimension: int = 8) -> tuple[PineconeChunkStore, PineconeVectorStore]:
    """Wire a chunk store + vector store against one shared in-memory fake
    Pinecone index -- mirrors the real architecture, where both classes
    operate against one Pinecone index underneath (see
    ``pinecone_connection.py``), without needing a live index or API key."""
    connection = PineconeConnection.__new__(PineconeConnection)
    connection._client = object()  # truthy sentinel: __new__ skips __init__, so this is unset otherwise
    connection.index = FakePineconeIndex()
    chunk_store = PineconeChunkStore(connection, embedding_dimension=embedding_dimension)
    vector_store = PineconeVectorStore(connection)
    return chunk_store, vector_store


def scanning_repositories(chunk_store: ChunkStore) -> tuple[
    ScanningDocumentRepository, ScanningChunkRepository, ScanningIngestionUnitOfWork
]:
    """IngestionPipeline's default (no-Postgres) repository set for tests --
    same construction api/dependencies.py uses when RAG_SUPABASE_DB_URL is
    unset. Reproduces the original chunk_store.get_document_hash() full-scan
    dedup behavior, no exact-hash pre-filter."""
    documents = ScanningDocumentRepository(chunk_store)
    chunks = ScanningChunkRepository()
    uow = ScanningIngestionUnitOfWork(documents, chunks)
    return documents, chunks, uow


def build_index_manager(
    chunk_store: ChunkStore, vector_store: VectorStore, bm25_index: BM25Index, audit_log=None,
) -> IndexManager:
    """IndexManager wired against the scanning fallback repositories --
    same construction api/dependencies.py uses when RAG_SUPABASE_DB_URL is
    unset. Reproduces the original chunk_store.get_by_legal_metadata()/
    bm25_index.build() full-scan/full-rebuild behavior."""
    return IndexManager(
        chunk_store, vector_store, bm25_index,
        bm25_repository=ScanningBM25Repository(bm25_index),
        compliance_repository=ScanningComplianceRepository(chunk_store),
        audit_log=audit_log,
    )
