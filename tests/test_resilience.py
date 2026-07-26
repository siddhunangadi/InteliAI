import pytest

from rag_hybrid_search.resilience import RetryingProxy, retry_with_backoff


def test_retry_with_backoff_returns_result_on_first_success():
    calls = []

    def fn():
        calls.append(1)
        return "ok"

    assert retry_with_backoff(fn, max_attempts=3, base_delay=0.001) == "ok"
    assert len(calls) == 1


def test_retry_with_backoff_retries_then_succeeds():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return "ok"

    assert retry_with_backoff(fn, max_attempts=5, base_delay=0.001) == "ok"
    assert calls["n"] == 3


def test_retry_with_backoff_raises_after_exhausting_attempts():
    def fn():
        raise ConnectionError("permanent")

    with pytest.raises(ConnectionError):
        retry_with_backoff(fn, max_attempts=3, base_delay=0.001)


class _FakeIndex:
    def __init__(self):
        self.calls = 0

    def query(self, **kwargs):
        self.calls += 1
        if self.calls < 2:
            raise TimeoutError("network blip")
        return {"matches": []}

    def not_callable_attr(self):
        raise AssertionError("should not be called")


def test_retrying_proxy_retries_transient_failures_transparently():
    target = _FakeIndex()
    proxy = RetryingProxy(target, max_attempts=3)
    assert proxy.query(vector=[0.1]) == {"matches": []}
    assert target.calls == 2


def test_retrying_proxy_passes_through_non_callable_attributes():
    class Obj:
        value = 42

    proxy = RetryingProxy(Obj())
    assert proxy.value == 42
