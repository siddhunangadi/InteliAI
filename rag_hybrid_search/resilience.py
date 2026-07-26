"""Generic retry-with-backoff, shared by every outbound-call seam that needs
one (Pinecone index calls today; nvidia.py's own retry loop predates this
and is left as-is rather than churned for no behavioral change).
"""

import logging
import random
import time
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Same shape as providers/nvidia.py's existing retry loop (max_attempts=5,
# full-jitter exponential backoff) -- kept consistent rather than inventing
# a second backoff policy.
_MAX_ATTEMPTS = 4
_BASE_DELAY_S = 0.5


def retry_with_backoff(
    fn: Callable[[], T],
    *,
    max_attempts: int = _MAX_ATTEMPTS,
    base_delay: float = _BASE_DELAY_S,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Call ``fn()``, retrying on ``retry_on`` exceptions with full-jitter
    exponential backoff. Re-raises the last exception once attempts are
    exhausted. Only safe for idempotent calls -- callers pick ``retry_on``
    to exclude anything that isn't (e.g. a 4xx validation error retrying
    won't fix)."""
    for attempt in range(max_attempts):
        try:
            return fn()
        except retry_on as e:
            if attempt == max_attempts - 1:
                raise
            delay = random.uniform(0, base_delay * (2**attempt))
            logger.warning(
                "retrying after transient error (attempt %d/%d, sleeping %.2fs): %s",
                attempt + 1, max_attempts, delay, e,
            )
            time.sleep(delay)
    raise AssertionError("unreachable")  # pragma: no cover


class RetryingProxy:
    """Wraps an object so every method call retries transiently on failure.

    Used for the Pinecone SDK's ``Index`` client (see PineconeConnection),
    which has no retry/backoff of its own -- unlike providers/nvidia.py's
    httpx calls. Every ``index.query()``/``upsert()``/``fetch()``/etc. call
    site in pinecone_vector_store.py/pinecone_chunk_store.py gets retry
    behavior from this one seam, without touching any of them.
    """

    def __init__(self, target: object, *, max_attempts: int = _MAX_ATTEMPTS):
        self._target = target
        self._max_attempts = max_attempts

    def __getattr__(self, name: str):
        attr = getattr(self._target, name)
        if not callable(attr):
            return attr

        def wrapped(*args, **kwargs):
            return retry_with_backoff(
                lambda: attr(*args, **kwargs), max_attempts=self._max_attempts,
            )

        return wrapped
