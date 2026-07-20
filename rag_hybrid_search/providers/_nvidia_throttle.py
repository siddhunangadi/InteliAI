"""Shared request pacing for all NVIDIA API calls (chat/completions,
embeddings, reranking) against one account -- generation, embedding, and
rerank each go through a *different* class with its own httpx.Client, but
all three share the same account-level burst-rate limit. Throttling only
inside NvidiaProvider left NvidiaRerankProvider free to burst and still
429 the account out from under both. One process-global limiter, since
every provider instance in a process shares the API key.

Measured directly against a live account: rapid-fire requests 429
repeatedly; ~2s-spaced sequential requests succeeded. This paces requests
to that measured safe rate instead of retrying into the same wall.
"""
import threading
import time

_lock = threading.Lock()
_last_call_ts = 0.0
MIN_INTERVAL_S = 2.0


def throttle() -> None:
    global _last_call_ts
    with _lock:
        wait = _last_call_ts + MIN_INTERVAL_S - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call_ts = time.monotonic()
