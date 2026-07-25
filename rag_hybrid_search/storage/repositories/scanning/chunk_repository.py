class ScanningChunkRepository:
    """Implements ChunkRepository with no exact-hash short-circuit -- every
    candidate hash is reported "new" (nothing is pre-filtered), which
    reproduces the original behavior of relying solely on the vectorized
    near-duplicate check in ingestion/dedup.py. Used when no Postgres
    database is configured; see ScanningDocumentRepository for why.
    """

    def filter_new_hashes(self, hashes: list[str]) -> set[str]:
        return set(hashes)

    def record_many(
        self, document_id: str, chunks: list[tuple[str, str, str, int | None]]
    ) -> None:
        pass
