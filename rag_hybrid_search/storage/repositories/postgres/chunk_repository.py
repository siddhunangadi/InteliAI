from psycopg.rows import dict_row

from rag_hybrid_search.storage.repositories.base import ChunkRecord
from rag_hybrid_search.storage.repositories.hashing import simhash_bands
from rag_hybrid_search.storage.repositories.postgres.connection import ConnectionProvider

_NUM_BANDS = 8
_BAND_BITS = 8


def _to_signed_bigint(value: int) -> int:
    """simhash() returns an unsigned 64-bit int; chunks.simhash is a
    (signed) bigint, so values >= 2**63 overflow it. Two's-complement
    wraparound into the signed range -- lossless and never read back into
    Python (bands are computed from the original unsigned value at write
    time), so this only affects what's stored, not any comparison."""
    return value - (1 << 64) if value >= (1 << 63) else value


class PostgresChunkRepository:
    """Implements ChunkRepository (rag_hybrid_search/storage/repositories/base.py)
    against the ``chunks`` and ``chunk_simhash_bands`` tables. Takes a
    ConnectionProvider, not a DSN -- never opens its own connection (see
    connection.py)."""

    def __init__(self, connection_provider: ConnectionProvider, organization_id: str):
        self._connections = connection_provider
        self._organization_id = organization_id

    def filter_new_hashes(self, hashes: list[str]) -> set[str]:
        if not hashes:
            return set()
        with self._connections.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                rows = cur.execute(
                    "select chunk_hash from chunks where organization_id = %s and chunk_hash = any(%s)",
                    (self._organization_id, hashes),
                ).fetchall()
        existing = {r["chunk_hash"] for r in rows}
        return set(hashes) - existing

    def record_many(self, document_id: str, chunks: list[ChunkRecord]) -> None:
        if not chunks:
            return
        with self._connections.connection() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                insert into chunks (
                    id, document_id, organization_id, chunk_index, text, chunk_hash, simhash,
                    heading, page, char_count, strategy_version,
                    legal_regulation, legal_authority, legal_jurisdiction, legal_article,
                    legal_section, legal_clause, legal_version, legal_effective_date,
                    legal_document_type, legal_risk_category, legal_is_current, legal_superseded_by,
                    embedding_status
                )
                values (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    'upserted'
                )
                on conflict (organization_id, chunk_hash) do nothing
                """,
                [
                    (
                        record.chunk.chunk_id, document_id, self._organization_id,
                        record.chunk.chunk_index, record.chunk.text, record.chunk_hash,
                        _to_signed_bigint(record.simhash),
                        record.chunk.heading, record.chunk.page, record.chunk.char_count,
                        record.chunk.strategy_version,
                        *_legal_fields(record.chunk),
                    )
                    for record in chunks
                ],
            )
            band_rows = [
                (self._organization_id, band_index, band_value, record.chunk.chunk_id)
                for record in chunks
                for band_index, band_value in enumerate(simhash_bands(record.simhash, _NUM_BANDS, _BAND_BITS))
            ]
            if band_rows:
                cur.executemany(
                    """
                    insert into chunk_simhash_bands (organization_id, band_index, band_value, chunk_id)
                    values (%s, %s, %s, %s)
                    on conflict do nothing
                    """,
                    band_rows,
                )

    def find_near_duplicate_candidates(self, simhash: int) -> set[str]:
        bands = simhash_bands(simhash, _NUM_BANDS, _BAND_BITS)
        # (band_index, band_value) IN ((%s,%s), (%s,%s), ...) -- a fixed,
        # small number of pairs (one per band), so this is still an
        # indexed lookup per pair, not a scan.
        placeholders = ", ".join(["(%s, %s)"] * len(bands))
        params: list = [self._organization_id]
        for band_index, band_value in enumerate(bands):
            params.extend((band_index, band_value))
        with self._connections.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                rows = cur.execute(
                    f"""
                    select distinct chunk_id from chunk_simhash_bands
                    where organization_id = %s and (band_index, band_value) in ({placeholders})
                    """,
                    params,
                ).fetchall()
        return {str(r["chunk_id"]) for r in rows}


def _legal_fields(chunk) -> tuple:
    lm = chunk.legal_metadata
    if lm is None:
        # legal_is_current is NOT NULL (default true) -- every other
        # legal_* column is nullable, so only this one needs a non-None
        # default for a non-legal chunk, matching LegalMetadata's own
        # is_current=True default.
        return (None, None, None, None, None, None, None, None, None, None, True, None)
    return (
        lm.regulation, lm.authority, lm.jurisdiction, lm.article,
        lm.section, lm.clause, lm.version, lm.effective_date,
        lm.document_type, lm.risk_category, lm.is_current, lm.superseded_by,
    )
