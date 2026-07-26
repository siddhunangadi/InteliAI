from psycopg.rows import dict_row

from rag_hybrid_search.storage.repositories.base import ComplianceCandidate
from rag_hybrid_search.storage.repositories.postgres.connection import ConnectionProvider

_FILTER_COLUMNS = {
    "regulation": "legal_regulation",
    "authority": "legal_authority",
    "jurisdiction": "legal_jurisdiction",
    "article": "legal_article",
    "section": "legal_section",
    "clause": "legal_clause",
}


class PostgresComplianceRepository:
    """Implements ComplianceRepository against the composite index on
    chunks(organization_id, legal_regulation, legal_authority,
    legal_jurisdiction, legal_article, legal_section, legal_clause) --
    bounded by how many versions of one clause identity exist, not corpus
    size."""

    def __init__(self, connection_provider: ConnectionProvider, organization_id: str):
        self._connections = connection_provider
        self._organization_id = organization_id

    def find_matching(self, filters: dict[str, str]) -> list[ComplianceCandidate]:
        conditions = ["organization_id = %s"]
        params: list = [self._organization_id]
        for key, value in filters.items():
            if key not in _FILTER_COLUMNS:
                raise ValueError(f"unknown compliance filter key: {key!r}")
            conditions.append(f"{_FILTER_COLUMNS[key]} = %s")
            params.append(value)
        query = (
            "select id, document_id, legal_effective_date, legal_is_current "
            "from chunks where " + " and ".join(conditions)
        )
        with self._connections.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                rows = cur.execute(query, params).fetchall()
        return [
            ComplianceCandidate(
                # chunks.id is a uuid column -- psycopg adapts it to
                # uuid.UUID by default; cast to str to match the Protocol
                # contract (and Chunk.chunk_id's str type everywhere else).
                chunk_id=str(r["id"]),
                document_id=r["document_id"],
                effective_date=r["legal_effective_date"],
                is_current=r["legal_is_current"],
            )
            for r in rows
        ]

    def mark_superseded(self, chunk_id: str, is_current: bool, superseded_by: str | None) -> None:
        with self._connections.connection() as conn:
            conn.execute(
                "update chunks set legal_is_current = %s, legal_superseded_by = %s where id = %s",
                (is_current, superseded_by, chunk_id),
            )
