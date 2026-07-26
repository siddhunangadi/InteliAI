from typing import Protocol

from rag_hybrid_search.models import RetrievedChunk
from rag_hybrid_search.storage.base import ChunkStore


class _SearchableBM25(Protocol):
    """Either BM25Index (local rank_bm25) or a BM25Repository implementation
    (rag_hybrid_search/storage/repositories/base.py) -- both expose the same
    search(query, k) -> [(chunk_id, score)] shape, so SparseRetriever
    doesn't need to know which it got."""

    def search(self, query: str, k: int) -> list[tuple[str, float]]: ...


class SparseRetriever:
    def __init__(self, chunk_store: ChunkStore, bm25_index: _SearchableBM25):
        self._chunk_store = chunk_store
        self._bm25_index = bm25_index

    def search(self, query: str, k: int) -> list[RetrievedChunk]:
        raw_results = self._bm25_index.search(query, k)

        results = []
        for chunk_id, score in raw_results:
            chunk = self._chunk_store.get(chunk_id)
            if chunk is None:
                continue
            results.append(
                RetrievedChunk(
                    chunk=chunk,
                    dense_score=None,
                    bm25_score=score,
                    rrf_score=0.0,
                    rerank_score=None,
                    final_rank=0,
                )
            )
        return results
