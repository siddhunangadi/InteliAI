"""Integration tests for PostgresJobRepository against a real Postgres
database. Skipped unless RAG_SUPABASE_DB_URL is set -- same convention as
test_postgres_repositories.py (see that file's module docstring)."""

import os
import uuid

import pytest

from rag_hybrid_search.storage.repositories.postgres.connection import PostgresConnectionPool
from rag_hybrid_search.storage.repositories.postgres.job_repository import PostgresJobRepository

pytestmark = pytest.mark.skipif(
    not os.environ.get("RAG_SUPABASE_DB_URL"),
    reason="RAG_SUPABASE_DB_URL not set -- integration test needs a live Postgres database",
)


@pytest.fixture
def pool():
    p = PostgresConnectionPool(os.environ["RAG_SUPABASE_DB_URL"])
    yield p
    p.close()


@pytest.fixture
def org_id():
    return str(uuid.uuid4())


@pytest.fixture
def repo(pool, org_id):
    with pool.connection() as conn:
        conn.execute("insert into organizations (id, name) values (%s, %s)", (org_id, "test-org"))
        conn.commit()
    yield PostgresJobRepository(pool, org_id)
    with pool.connection() as conn:
        conn.execute("delete from ingestion_jobs where organization_id = %s", (org_id,))
        conn.execute("delete from organizations where id = %s", (org_id,))


def test_enqueue_then_claim_returns_the_job(repo):
    job_id, created = repo.enqueue({"files": ["a"]}, idempotency_key=None)
    assert created is True

    job = repo.claim(worker_id="w1")
    assert job.job_id == job_id
    assert job.status == "processing"
    assert job.payload == {"files": ["a"]}


def test_second_claim_gets_nothing_once_queue_is_empty(repo):
    repo.enqueue({"files": ["a"]}, idempotency_key=None)
    repo.claim(worker_id="w1")
    assert repo.claim(worker_id="w2") is None


def test_idempotency_key_collision_returns_existing_job(repo):
    job_id_1, created_1 = repo.enqueue({"files": ["a"]}, idempotency_key="k1")
    job_id_2, created_2 = repo.enqueue({"files": ["a"]}, idempotency_key="k1")
    assert created_1 is True
    assert created_2 is False
    assert job_id_1 == job_id_2


def test_priority_order_claims_higher_priority_first(repo):
    _low, _ = repo.enqueue({"files": ["low"]}, idempotency_key=None, priority=0)
    high_id, _ = repo.enqueue({"files": ["high"]}, idempotency_key=None, priority=10)

    job = repo.claim(worker_id="w1")
    assert job.job_id == high_id


def test_complete_marks_ready_with_result(repo):
    job_id, _ = repo.enqueue({"files": ["a"]}, idempotency_key=None)
    repo.claim(worker_id="w1")
    repo.complete(job_id, {"results": [{"filename": "a", "status": "ready"}]})

    job = repo.get(job_id)
    assert job.status == "ready"
    assert job.result == {"results": [{"filename": "a", "status": "ready"}]}


def test_fail_under_max_retries_requeues_instead_of_dead_lettering(repo):
    job_id, _ = repo.enqueue({"files": ["a"]}, idempotency_key=None)
    repo.claim(worker_id="w1")
    repo.fail(job_id, "boom")

    job = repo.get(job_id)
    assert job.status == "queued"
    assert job.retry_count == 1
    assert job.error == "boom"


def test_fail_past_max_retries_moves_to_dead_letter(repo, pool, org_id):
    job_id, _ = repo.enqueue({"files": ["a"]}, idempotency_key=None)
    with pool.connection() as conn:
        conn.execute("update ingestion_jobs set max_retries = 0 where id = %s", (job_id,))
        conn.commit()
    repo.claim(worker_id="w1")
    repo.fail(job_id, "boom")

    job = repo.get(job_id)
    assert job.status == "dead_letter"
    assert job in repo.list_dead_letter()


def test_cancel_only_succeeds_while_queued(repo):
    job_id, _ = repo.enqueue({"files": ["a"]}, idempotency_key=None)
    assert repo.cancel(job_id) is True
    assert repo.get(job_id).status == "cancelled"

    job_id_2, _ = repo.enqueue({"files": ["a"]}, idempotency_key=None)
    repo.claim(worker_id="w1")
    assert repo.cancel(job_id_2) is False
    assert repo.get(job_id_2).status == "processing"


def test_reap_stale_claims_requeues_jobs_with_an_expired_heartbeat(repo, pool):
    job_id, _ = repo.enqueue({"files": ["a"]}, idempotency_key=None)
    repo.claim(worker_id="w1")
    with pool.connection() as conn:
        conn.execute(
            "update ingestion_jobs set heartbeat_at = now() - interval '10 minutes' where id = %s",
            (job_id,),
        )
        conn.commit()

    reclaimed = repo.reap_stale_claims(heartbeat_timeout_s=60)
    assert reclaimed == 1
    assert repo.get(job_id).status == "queued"


def test_reap_stale_claims_leaves_fresh_heartbeats_alone(repo):
    job_id, _ = repo.enqueue({"files": ["a"]}, idempotency_key=None)
    repo.claim(worker_id="w1")
    assert repo.reap_stale_claims(heartbeat_timeout_s=120) == 0
    assert repo.get(job_id).status == "processing"
