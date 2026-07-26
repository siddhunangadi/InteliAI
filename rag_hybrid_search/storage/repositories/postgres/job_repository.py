from psycopg.types.json import Jsonb

from rag_hybrid_search.storage.repositories.base import IngestionJob
from rag_hybrid_search.storage.repositories.postgres.connection import ConnectionProvider

_TERMINAL_STATUSES = ("ready", "failed", "dead_letter", "cancelled")


def _row_to_job(row: tuple) -> IngestionJob:
    (job_id, status, payload, result, error, retry_count, max_retries,
     progress_current, progress_total) = row
    return IngestionJob(
        job_id=str(job_id), status=status, payload=payload, result=result, error=error,
        retry_count=retry_count, max_retries=max_retries,
        progress_current=progress_current, progress_total=progress_total,
    )


_SELECT_COLUMNS = (
    "id, status, payload, result, error, retry_count, max_retries, "
    "progress_current, progress_total"
)


class PostgresJobRepository:
    """Implements JobRepository (rag_hybrid_search/storage/repositories/base.py)
    against the ``ingestion_jobs`` table, following the same
    ConnectionProvider-only pattern as every other Postgres repository in
    this package -- never opens its own connection."""

    def __init__(self, connection_provider: ConnectionProvider, organization_id: str):
        self._connections = connection_provider
        self._organization_id = organization_id

    def enqueue(self, payload: dict, *, idempotency_key: str | None, priority: int = 0) -> tuple[str, bool]:
        with self._connections.connection() as conn:
            if idempotency_key is not None:
                existing = conn.execute(
                    "select id from ingestion_jobs where organization_id = %s and idempotency_key = %s",
                    (self._organization_id, idempotency_key),
                ).fetchone()
                if existing is not None:
                    return str(existing[0]), False
            row = conn.execute(
                """
                insert into ingestion_jobs
                    (organization_id, status, priority, payload, idempotency_key, progress_total)
                values (%s, 'queued', %s, %s, %s, %s)
                returning id
                """,
                (
                    self._organization_id, priority, Jsonb(payload), idempotency_key,
                    len(payload.get("files", [])),
                ),
            ).fetchone()
            return str(row[0]), True

    def claim(self, worker_id: str) -> IngestionJob | None:
        with self._connections.connection() as conn:
            row = conn.execute(
                f"""
                update ingestion_jobs set
                    status = 'processing', worker_id = %s,
                    started_at = now(), heartbeat_at = now()
                where id = (
                    select id from ingestion_jobs
                    where organization_id = %s and status = 'queued' and available_at <= now()
                    order by priority desc, created_at asc
                    for update skip locked
                    limit 1
                )
                returning {_SELECT_COLUMNS}
                """,
                (worker_id, self._organization_id),
            ).fetchone()
            return _row_to_job(row) if row is not None else None

    def heartbeat(self, job_id: str) -> None:
        with self._connections.connection() as conn:
            conn.execute(
                "update ingestion_jobs set heartbeat_at = now() where id = %s and status = 'processing'",
                (job_id,),
            )

    def complete(self, job_id: str, result: dict) -> None:
        with self._connections.connection() as conn:
            conn.execute(
                """
                update ingestion_jobs set
                    status = 'ready', result = %s, completed_at = now(),
                    progress_current = progress_total
                where id = %s
                """,
                (Jsonb(result), job_id),
            )

    def fail(self, job_id: str, error: str) -> None:
        with self._connections.connection() as conn:
            row = conn.execute(
                "select retry_count, max_retries from ingestion_jobs where id = %s", (job_id,),
            ).fetchone()
            if row is None:
                return
            retry_count, max_retries = row
            if retry_count < max_retries:
                # Full-jitter exponential backoff, same policy as
                # resilience.retry_with_backoff -- computed in SQL so the
                # delay is anchored to the DB's clock, not the worker's.
                conn.execute(
                    """
                    update ingestion_jobs set
                        status = 'queued', retry_count = retry_count + 1, error = %s,
                        available_at = now() + (least(power(2, retry_count), 300) * random()) * interval '1 second',
                        worker_id = null, heartbeat_at = null
                    where id = %s
                    """,
                    (error, job_id),
                )
            else:
                conn.execute(
                    """
                    update ingestion_jobs set status = 'dead_letter', error = %s, completed_at = now()
                    where id = %s
                    """,
                    (error, job_id),
                )

    def cancel(self, job_id: str) -> bool:
        with self._connections.connection() as conn:
            row = conn.execute(
                "update ingestion_jobs set status = 'cancelled', completed_at = now() "
                "where id = %s and status = 'queued' returning id",
                (job_id,),
            ).fetchone()
            return row is not None

    def get(self, job_id: str) -> IngestionJob | None:
        with self._connections.connection() as conn:
            row = conn.execute(
                f"select {_SELECT_COLUMNS} from ingestion_jobs where id = %s", (job_id,),
            ).fetchone()
            return _row_to_job(row) if row is not None else None

    def reap_stale_claims(self, heartbeat_timeout_s: int) -> int:
        with self._connections.connection() as conn:
            rows = conn.execute(
                """
                update ingestion_jobs set
                    status = 'queued', worker_id = null, heartbeat_at = null
                where status = 'processing'
                    and heartbeat_at < now() - (%s * interval '1 second')
                returning id
                """,
                (heartbeat_timeout_s,),
            ).fetchall()
            return len(rows)

    def list_dead_letter(self, limit: int = 100) -> list[IngestionJob]:
        with self._connections.connection() as conn:
            rows = conn.execute(
                f"""
                select {_SELECT_COLUMNS} from ingestion_jobs
                where organization_id = %s and status = 'dead_letter'
                order by created_at desc limit %s
                """,
                (self._organization_id, limit),
            ).fetchall()
            return [_row_to_job(row) for row in rows]
