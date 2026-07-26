from typing import Callable, Iterator

from rag_hybrid_search.models import Chunk
from rag_hybrid_search.storage.bm25_index import BM25Index


class ScanningBM25Repository:
    """Implements BM25Repository by delegating to the local rank_bm25-backed
    BM25Index (pickle file) -- used when no Postgres database is
    configured. rank_bm25 has no incremental API, so record_many()/
    remove_chunks() are no-ops; rebuild_full() (bm25_index.build()+save())
    is what actually makes newly-ingested chunks searchable for this
    backend, same as before this repository layer existed.
    """

    def __init__(self, bm25_index: BM25Index):
        self._bm25_index = bm25_index

    def record_many(self, chunks: list[Chunk]) -> None:
        pass

    def remove_chunks(self, chunk_ids: list[str]) -> None:
        pass

    def rebuild_full(self, get_chunks: Callable[[], Iterator[Chunk]]) -> None:
        self._bm25_index.build(list(get_chunks()))
        self._bm25_index.save()

    def search(self, query: str, k: int) -> list[tuple[str, float]]:
        return self._bm25_index.search(query, k)
