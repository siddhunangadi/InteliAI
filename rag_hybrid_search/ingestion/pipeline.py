import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import httpx

from rag_hybrid_search.diagnostics import rss_mb
from rag_hybrid_search.ingestion.chunkers.base import Chunker
from rag_hybrid_search.ingestion.dedup import find_duplicates, find_within_batch_duplicates
from rag_hybrid_search.ingestion.loaders.base import Loader
from rag_hybrid_search.models import Chunk, Document, EmbeddingRecord, IndexStatus
from rag_hybrid_search.providers.base import EmbeddingProvider
from rag_hybrid_search.storage.base import ChunkStore
from rag_hybrid_search.storage.index_manager import IndexManager

logger = logging.getLogger(__name__)


class IngestionPipeline:
    def __init__(
        self,
        loader: Loader,
        chunker: Chunker,
        embedding_provider: EmbeddingProvider,
        chunk_store: ChunkStore,
        index_manager: IndexManager,
        dedup_cosine_threshold: float,
        dedup_text_threshold: float,
    ):
        self.loader = loader
        self.chunker = chunker
        self.embedding_provider = embedding_provider
        self.chunk_store = chunk_store
        self.index_manager = index_manager
        self._dedup_cosine_threshold = dedup_cosine_threshold
        self._dedup_text_threshold = dedup_text_threshold

    def ingest(
        self,
        path: str,
        existing_pairs: list[tuple[Chunk, list[float]]] | None = None,
        rebuild_bm25: bool = True,
        known_hashes: dict[str, str] | None = None,
        document: Document | None = None,
    ) -> IndexStatus:
        """Ingest one document.

        ``document``, if given, skips ``loader.load(path)`` -- callers that
        already extracted the document (e.g. a batch script extracting PDFs
        in a process pool, since pdfplumber extraction is CPU-bound Python
        that the GIL serializes across threads) pass it in directly.

        ``existing_pairs``, if given, is the caller's shared dedup cache: it's
        used instead of re-fetching the whole corpus from ``chunk_store``, and
        mutated in place (new chunks appended) so the next call in the same
        batch sees this file's chunks too. Batch callers (see
        api/routes.py upload_documents_async) build this list once and pass
        ``rebuild_bm25=False`` for every file but the last, since re-scanning
        the full corpus and rebuilding BM25 per file is the dominant cost at
        the 1000-file scale this exists for.

        ``known_hashes``, if given, is the caller's shared source_path ->
        document_id cache, same idea as ``existing_pairs`` but for the
        unchanged-file check: ``chunk_store.get_document_hash()`` does a full
        paginated scan of the whole index on every call, so calling it once
        per document in a batch makes ingestion of N documents cost O(N^2)
        index scans. A batch caller builds this dict once (or starts it
        empty for a fresh index) and this method mutates it in place.
        """
        logger.info("ingest: start path=%s rss_mb=%.1f", path, rss_mb())
        if document is None:
            document = self.loader.load(path)
        logger.info(
            "ingest: loaded document_id=%s format=%s chars=%d rss_mb=%.1f",
            document.document_id, document.format, len(document.content), rss_mb(),
        )

        if known_hashes is not None:
            existing_hash = known_hashes.get(path)
        else:
            existing_hash = self.chunk_store.get_document_hash(path)
        if existing_hash == document.document_id:
            logger.info("ingest: unchanged, skipping path=%s", path)
            return IndexStatus.READY
        if existing_hash is not None:
            logger.info("ingest: content changed, removing old document_id=%s", existing_hash)
            self.index_manager.remove_document(existing_hash, rebuild_bm25=rebuild_bm25)

        if known_hashes is not None:
            known_hashes[path] = document.document_id

        new_chunks = self.chunker.chunk(document)
        logger.info(
            "ingest: chunked into %d chunks (strategy=%s) rss_mb=%.1f",
            len(new_chunks), self.chunker.__class__.__name__, rss_mb(),
        )
        if not new_chunks:
            logger.info("ingest: no chunks produced, done path=%s", path)
            return IndexStatus.READY
        logger.debug(
            "ingest: chunk previews %s",
            [(c.chunk_id, c.chunk_index, c.char_count, c.text[:80]) for c in new_chunks],
        )

        # ponytail: NVIDIA's embeddings endpoint 400s past ~96 inputs per request;
        # batch rather than raise the limit, since large regulation docs (annexes,
        # many clauses) routinely exceed it in one shot.
        _EMBED_BATCH_SIZE = 90
        # ponytail: chunkers (e.g. ClauseChunker splitting on Article/Annex
        # boundaries, not size) can produce a chunk over the embedding model's
        # 512-token cap, which 400s the whole batch. Chars/token varies a lot
        # by document density (measured 1.4-2.8 chars/token across the corpus,
        # e.g. table-heavy Basel docs are far denser than prose), so a single
        # global char cap either over-truncates most docs or still fails on
        # the densest ones. 1200 chars covers the common case cheaply; on an
        # actual token-limit 400, _embed_batch_with_shrink retries that one
        # batch with progressively harder truncation instead of guessing.
        # Truncates only what's sent for embedding, not the stored chunk
        # text (citations/context still need the full text).
        _EMBED_CHAR_LIMIT = 1200
        texts = [c.text[:_EMBED_CHAR_LIMIT] for c in new_chunks]
        batches = [texts[s : s + _EMBED_BATCH_SIZE] for s in range(0, len(texts), _EMBED_BATCH_SIZE)]
        if len(batches) == 1:
            embeddings = self._embed_batch_with_shrink(batches[0])
        else:
            # Embedding calls are pure network wait -- a 4000-chunk document
            # is ~45 batch round-trips, and running them one at a time makes
            # the API's latency the whole ingest time. executor.map preserves
            # batch order, so the chunk<->embedding zip below stays correct.
            with ThreadPoolExecutor(max_workers=min(8, len(batches))) as pool:
                embeddings = [e for batch_out in pool.map(self._embed_batch_with_shrink, batches) for e in batch_out]
        logger.info(
            "ingest: embedded %d chunks with provider=%s model=%s dim=%d rss_mb=%.1f",
            len(embeddings), type(self.embedding_provider).__name__,
            self.embedding_provider.model_name, self.embedding_provider.dimension, rss_mb(),
        )
        if existing_pairs is None:
            existing_pairs = self._existing_chunk_embeddings()
        logger.debug("ingest: comparing against %d existing chunks for dedup", len(existing_pairs))

        # Two vectorized passes instead of an O(existing_count * new_count)
        # pure-Python loop: one against the corpus ingested before this
        # document, one for this document's own chunks against each other
        # (a single large document can itself have thousands of chunks --
        # see find_duplicates()'s docstring for why that matters).
        dup_vs_existing = find_duplicates(
            new_chunks, embeddings, existing_pairs,
            self._dedup_cosine_threshold, self._dedup_text_threshold,
        )
        dup_within_doc = find_within_batch_duplicates(
            new_chunks, embeddings, self._dedup_cosine_threshold, self._dedup_text_threshold,
        )

        surviving_chunks: list[Chunk] = []
        surviving_records: list[EmbeddingRecord] = []
        dropped = 0
        for chunk, embedding, is_dup_existing, is_dup_within in zip(
            new_chunks, embeddings, dup_vs_existing, dup_within_doc
        ):
            if is_dup_existing or is_dup_within:
                dropped += 1
                logger.debug("ingest: dropped duplicate chunk_id=%s index=%d", chunk.chunk_id, chunk.chunk_index)
                continue
            record = EmbeddingRecord(
                chunk_id=chunk.chunk_id,
                embedding=embedding,
                embedding_model=self.embedding_provider.model_name,
                embedding_dimension=self.embedding_provider.dimension,
                provider=type(self.embedding_provider).__name__,
                created_at=datetime.now(timezone.utc),
            )
            surviving_chunks.append(chunk)
            surviving_records.append(record)
            existing_pairs.append((chunk, embedding))

        logger.info("ingest: dedup dropped %d/%d chunks, %d survive", dropped, len(new_chunks), len(surviving_chunks))
        if not surviving_chunks:
            logger.info("ingest: nothing new to store, done path=%s", path)
            return IndexStatus.READY

        self.chunk_store.put_many(surviving_chunks, source_path=path)
        logger.info(
            "ingest: stored %d chunks in chunk_store rss_mb=%.1f",
            len(surviving_chunks), rss_mb(),
        )

        status = self.index_manager.index(surviving_chunks, surviving_records, rebuild_bm25=rebuild_bm25)
        logger.info("ingest: index_manager.index() returned rss_mb=%.1f", rss_mb())
        logger.info("ingest: indexed %d chunks, status=%s path=%s", len(surviving_chunks), status, path)
        return status

    def _embed_batch_with_shrink(self, texts: list[str], max_attempts: int = 4) -> list[list[float]]:
        """Embed one batch, retrying with harder truncation on the provider's
        max-token-length 400 (see the token-density comment at the call site
        for why a single global char cap isn't reliable) or with exponential
        backoff on 429 (concurrent workers all hitting NVIDIA at once make
        rate-limiting the expected case, not an edge case, once ingestion is
        actually parallel -- a single 429 shouldn't fail the whole document)."""
        attempt_texts = texts
        for attempt in range(max_attempts):
            try:
                return self.embedding_provider.embed(attempt_texts)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_attempts - 1:
                    wait_s = 2 ** attempt
                    logger.warning("embed: 429 rate-limited, backing off %ds (attempt %d/%d)", wait_s, attempt + 1, max_attempts)
                    time.sleep(wait_s)
                    continue
                if e.response.status_code != 400 or attempt == max_attempts - 1:
                    raise
                shrink_to = max(200, max(len(t) for t in attempt_texts) // 2)
                logger.warning(
                    "embed: 400 (likely token-length), retrying batch truncated to %d chars (attempt %d/%d)",
                    shrink_to, attempt + 1, max_attempts,
                )
                attempt_texts = [t[:shrink_to] for t in attempt_texts]
        raise AssertionError("unreachable")  # loop always returns or raises

    def _existing_chunk_embeddings(self) -> list[tuple[Chunk, list[float]]]:
        # chunk_store already has the embedding for every existing chunk
        # (it was computed once, when that chunk was first ingested) --
        # re-embedding them here on every ingest() call would be pure waste
        # scaling with corpus size, so reuse what's already stored instead.
        return [
            (item.chunk, item.embedding)
            for item in self.chunk_store.all_with_embeddings()
        ]
