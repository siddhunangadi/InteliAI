import logging
import random
import threading
import time

import httpx

from rag_hybrid_search.diagnostics import rss_mb
from rag_hybrid_search.providers.base import EmbeddingProvider, GenerationProvider

logger = logging.getLogger(__name__)

_BASE_URL = "https://integrate.api.nvidia.com/v1"

_MODEL_DIMENSIONS = {
    "nvidia/nv-embedqa-e5-v5": 1024,
    "nvidia/nv-embed-v2": 4096,
}


class NvidiaProvider(EmbeddingProvider, GenerationProvider):
    def __init__(
        self,
        api_key: str,
        embedding_model: str = "nvidia/nv-embedqa-e5-v5",
        generation_model: str = "meta/llama-3.1-70b-instruct",
        timeout: float = 60.0,
    ):
        self._api_key = api_key
        self._embedding_model = embedding_model
        self._generation_model = generation_model
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"}, timeout=timeout
        )
        # Measured directly against this account: rapid-fire requests 429
        # repeatedly, but 1s-spaced sequential requests succeeded 3/3 with
        # zero 429s -- this is a burst-rate limiter, not an exhausted quota
        # (retrying harder doesn't help; not bursting in the first place
        # does). Shared across concurrent callers so N worker threads
        # collectively pace themselves to one request in flight at a time,
        # instead of each retrying independently into the same wall.
        self._rate_lock = threading.Lock()
        self._last_call_ts = 0.0
        self._min_interval_s = 2.0

    def _throttle(self) -> None:
        with self._rate_lock:
            wait = self._last_call_ts + self._min_interval_s - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_call_ts = time.monotonic()

    def embed(self, texts: list[str], input_type: str = "passage") -> list[list[float]]:
        self._throttle()
        logger.info("embed: sending request for %d texts rss_mb=%.1f", len(texts), rss_mb())
        response = self._client.post(
            f"{_BASE_URL}/embeddings",
            json={
                "input": texts,
                "model": self._embedding_model,
                "input_type": input_type,
            },
        )
        logger.info(
            "embed: response received status=%d content_length=%s rss_mb=%.1f",
            response.status_code, response.headers.get("content-length"), rss_mb(),
        )
        response.raise_for_status()
        parsed = response.json()
        logger.info("embed: response.json() parsed rss_mb=%.1f", rss_mb())
        data = parsed["data"]
        result = [item["embedding"] for item in data]
        logger.info("embed: built %d embedding lists rss_mb=%.1f", len(result), rss_mb())
        return result

    def generate(self, prompt: str, max_attempts: int = 5, **kwargs) -> str:
        payload = {
            "model": self._generation_model,
            "messages": [{"role": "user", "content": prompt}],
            # 1024 was too tight for the structured {answer, claims[]} JSON
            # output on longer/multi-claim questions -- the response gets
            # cut off mid-object, producing unparseable truncated JSON that
            # falls all the way back to showing the raw text to the user.
            "max_tokens": 2048,
        }
        payload.update(kwargs)
        # Concurrent callers (parallel eval runs, concurrent RAG requests)
        # all hit this endpoint at once -- 429 is the expected case under
        # real concurrency, not an edge case, and previously had no retry
        # at all: one rate-limited request failed the whole answer/judge
        # call. Exponential backoff, same pattern as the embed path.
        for attempt in range(max_attempts):
            self._throttle()
            response = self._client.post(f"{_BASE_URL}/chat/completions", json=payload)
            if response.status_code == 429 and attempt < max_attempts - 1:
                # Full jitter (not just exponential): concurrent workers
                # computing the same 2**attempt all retry at the same
                # instant and collide again -- observed directly (workers
                # backing off "2.0s" simultaneously, then 429ing together
                # on the next attempt too).
                wait_s = random.uniform(0, 2 ** attempt)
                retry_after = response.headers.get("retry-after")
                if retry_after:
                    try:
                        wait_s = max(wait_s, float(retry_after))
                    except ValueError:
                        pass
                logger.warning("generate: 429 rate-limited, backing off %.1fs (attempt %d/%d)", wait_s, attempt + 1, max_attempts)
                time.sleep(wait_s)
                continue
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        response.raise_for_status()  # last attempt: surface the real error rather than looping forever
        return response.json()["choices"][0]["message"]["content"]

    @property
    def model_name(self) -> str:
        return self._embedding_model

    @property
    def dimension(self) -> int:
        return _MODEL_DIMENSIONS.get(self._embedding_model, 1024)
