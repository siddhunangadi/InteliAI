from rag_hybrid_search.storage.repositories.base import ChunkRecord


class ScanningChunkRepository:
    """Implements ChunkRepository with no exact-hash short-circuit -- every
    candidate hash is reported "new" (nothing is pre-filtered), which
    reproduces the original behavior of relying solely on the vectorized
    near-duplicate check in ingestion/dedup.py. find_near_duplicate_candidates()
    returns None (no LSH-based narrowing available), signaling the pipeline
    to fall back to comparing against the whole corpus, same as before this
    repository layer existed. Used when no Postgres database is configured;
    see ScanningDocumentRepository for why.
    """

    def filter_new_hashes(self, hashes: list[str]) -> set[str]:
        return set(hashes)

    def record_many(self, document_id: str, chunks: list[ChunkRecord]) -> None:
        pass

    def find_near_duplicate_candidates(self, simhash: int) -> set[str] | None:
        return None
