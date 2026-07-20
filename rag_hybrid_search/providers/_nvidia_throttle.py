"""Shared request pacing for all NVIDIA API calls (chat/completions,
embeddings, reranking) against one account -- generation, embedding, and
rerank each go through a *different* class with its own httpx.Client, but
all three share the same account-level rate limit. One process-global
limiter, since every provider instance in a process shares the API key.

``slot()`` holds the lock for the *entire* request (send through response),
not just its start time: pacing only send-times still allows N requests to
be genuinely in-flight concurrently whenever a response takes longer than
the pacing interval (LLM generation routinely does, 5-15s) -- verified
directly, spacing sends 2s apart still produced repeated 429s. Holding the
lock for the full round trip guarantees exactly one NVIDIA request in
flight system-wide at any time, which a plain start-time pacer cannot.
"""
import threading
import time
from contextlib import contextmanager

_lock = threading.Lock()
_last_release_ts = 0.0
MIN_GAP_S = 0.5


@contextmanager
def slot():
    global _last_release_ts
    with _lock:
        wait = _last_release_ts + MIN_GAP_S - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            yield
        finally:
            _last_release_ts = time.monotonic()
