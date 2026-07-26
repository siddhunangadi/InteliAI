# Production Readiness Report — InteliAI RAG Hybrid Search

Read-only audit. No code was changed producing this report — no bug found here rises to "critical" (data loss / incorrect results / crash); every finding below is a performance or architectural gap, tracked as debt, not fixed inline per the audit's scope.

Method: static analysis of the actual implementation (file/line citations throughout) plus the existing per-stage latency instrumentation already built into the pipeline (`RetrievalTrace`, `rag_hybrid_search/trace.py`). No live load test was run against a real Pinecone/NVIDIA/Postgres backend in this session — every millisecond figure below is either (a) read directly from a documented measurement already in the codebase's comments/commit history, or (b) an estimate explicitly labeled as such, derived from the code path's actual call count and known per-call cost ranges. Where I say "estimate," treat it as directional, not a benchmark result.

---

## 1. Retrieval Latency Breakdown

`HybridRetriever.retrieve()` (`rag_hybrid_search/retrieval/retriever.py:70-137`) already instruments every stage via `RetrievalTrace` (`trace.dense_latency_ms`, `bm25_latency_ms`, `fusion_latency_ms`, `rerank_latency_ms`), and `DenseRetriever.search()` separately traces query-embedding time. That instrumentation is the ground truth for a real run; here's what it decomposes to and what each number is actually paying for:

| Stage | What it does | Estimated latency (default config) | Dominant cost |
|---|---|---|---|
| Query embedding | 1 NVIDIA embed call for the question | **150–400ms**, but see finding **F1** below — can balloon to seconds under any concurrent ingestion or answer traffic | Network RTT + the global NVIDIA lock |
| Dense (Pinecone) search | 1 `index.query()` + **up to `dense_k` (default 10) separate `index.fetch()` calls**, one per hit (`dense.py:35`, `PineconeChunkStore.get()`) | query: ~50–150ms; **hydration: 10 × 20–60ms serial-ish fetches** (see **F2**) | The per-hit fetch loop, not the query itself |
| Sparse (BM25) search | Postgres path: 2 round-trips (corpus stats + a well-indexed scored query, `bm25_repository.py:139-179`) **then the same per-hit `chunk_store.get()` fetch loop** as dense (`sparse.py:26`) | SQL: ~5–20ms; **hydration: 10 more Pinecone fetches** | Same **F2** pattern, doubled |
| RRF fusion | Pure Python, dict merge + sort over ≤20 candidates | **<1ms** | negligible |
| Metadata filtering (compliance queries only) | `query_router.route_query()` calls `chunk_store.get_by_legal_metadata()`, which is a **full corpus scan** on `PineconeChunkStore` (cached 300s, invalidated on every write) | **cache hit: ~0ms; cache miss: seconds-to-minutes at real corpus size** (documented in `pinecone_chunk_store.py`'s own comments: "~450 sequential round-trips for 45k vectors" before it was made concurrent — still a full scan, just parallelized) | See **F3** |
| Reranking | Default backend is `PassthroughReranker` — in-memory sort, no model, no network call | **<1ms** | n/a (see Phase 3) |
| Context assembly | Dedup + char-budget truncation, pure Python over ≤10 chunks | **<1ms** | negligible |
| Prompt construction | String join | **<1ms** | negligible |
| Generation (not requested, but the actual end-to-end floor) | 1 NVIDIA chat completion call, `max_tokens=2048` | **2–8s** typical, serialized against every other NVIDIA call process-wide | **F1** |

**Slowest stage, ranked:**

1. **Generation** (out of this audit's explicit scope, but it's the real floor of `/answer` latency — seconds, not milliseconds, and every other stage here is noise next to it).
2. **Dense + sparse hydration (F2)**: up to 20 sequential-per-result Pinecone `fetch()` calls just to turn `(chunk_id, score)` pairs into full `Chunk` objects. This is the slowest stage genuinely *inside* this audit's scope.
3. **Query embedding**, inflated by the global NVIDIA lock (F1) whenever ingestion is running concurrently.
4. Everything else (fusion/prune/context/prompt) is sub-millisecond and not a real concern at any conceivable corpus size — these are pure in-memory operations over a bounded (≤20-chunk) working set.

### Finding F1 — Global NVIDIA request lock serializes embedding, generation, and rerank across the entire process

`rag_hybrid_search/providers/_nvidia_throttle.py:24-34`: `slot()` is a single process-wide `threading.Lock`, held for the **entire request/response round trip**, not just the send. Every `NvidiaProvider.embed()` and `.generate()` call — and every `NvidiaRerankProvider` call if that backend is selected — funnels through this one lock. This is a deliberate, documented choice (the module docstring explains start-time-only pacing still produced 429s under concurrency), and it is correct for *rate-limit avoidance*. But its side effect is that **there is never more than one in-flight NVIDIA call, system-wide, no matter how many worker threads, retrieval sub-queries, or concurrent `/answer` requests are in flight.**

Concretely: `WorkerPool`'s 4 concurrent ingestion workers, each doing per-document `ThreadPoolExecutor(max_workers=8)` batch-embedding (`ingestion/pipeline.py:148`), all collapse to one NVIDIA call at a time. A `/answer` request's query-embedding call queues behind any of those. A generation call (2-8s) blocks every other embedding *and* generation call in the process for its full duration. This is the single largest latency amplifier in the system under any real concurrent load, and it is invisible in a single-request benchmark — it only shows up under concurrency, which is exactly the scenario Phase 5/6 below need to reason about.

### Finding F2 — Chunk hydration is N+1, not batched

`DenseRetriever.search()` (`dense.py:34-38`) and `SparseRetriever.search()` (`sparse.py:25-29`) each call `chunk_store.get(chunk_id)` **once per hit** in a Python loop. `PineconeChunkStore.get()` (`pinecone_chunk_store.py`) issues `index.fetch(ids=[chunk_id])` — a single-id fetch — per call. At `dense_k=10, sparse_k=10` (defaults), that's **20 separate Pinecone network round-trips per retrieval**, done serially in a loop, when `ChunkStore.get_many_with_embeddings(chunk_ids)` already exists on the same class (used elsewhere, e.g. near-dup candidate fetching) and would collapse this to 1-2 batched `fetch()` calls. This is not a correctness bug — every test passes, results are right — but it's a clean, mechanical latency win sitting unused right next to the code that needs it.

### Finding F3 — Compliance/metadata query routing bypasses the repository layer built to speed it up

`query_router.route_query()` (`compliance/query_router.py:87,95`) calls `chunk_store.get_by_legal_metadata()` directly for `structured`/`metadata`/`mixed` intent questions. That method lives on `PineconeChunkStore` and is a full corpus scan (cached, TTL 300s, invalidated by every write). The prior milestone built `ComplianceRepository`/`PostgresComplianceRepository` with an **indexed** composite lookup specifically for compliance metadata — but it's only wired into `IndexManager._detect_and_mark_superseded()` (ingest-time supersession detection), never into the query-time path. A compliance-heavy query load (which this app is explicitly built for — GDPR/HIPAA/clause-reference questions are the primary use case per `query_router.py`'s own classifier) pays the full-scan cost query-router was presumably meant to avoid, except when the 5-minute cache happens to be warm.

---

## 2. Retrieval Quality Assessment

**Dense retrieval:** Standard cosine-similarity kNN via Pinecone, `dense_k=10`. Sound, no issues found. Embedding truncation at ingest time (`_EMBED_CHAR_LIMIT=1200` chars, `pipeline.py:138`) means very long chunks are embedded on a *truncated* view of their own text — the full text is still stored and shown to the LLM, but the *vector* only reflects the first ~1200 characters. For chunk_size=500 (default), this never triggers (chunks are shorter than the limit). It only matters for non-default chunkers (e.g. `ClauseChunker`) that can produce longer chunks — worth knowing, not currently a live problem at default config.

**Sparse (BM25) retrieval:** Classic Okapi BM25, correctly implemented (`bm25_repository.py`'s SQL matches the standard formula), `sparse_k=10`. No issues.

**Hybrid fusion (RRF):** `weighted_rrf()` (`fusion.py`) is a reasonable weighted variant (`rrf_dense_weight=0.7`, `rrf_sparse_weight=0.3`, `k=60` defaults) — dense-leaning, which is a defensible default for a semantically-rich compliance corpus, though it's a fixed global weighting with no per-query adaptation (e.g. a bare clause-number query like "what does Article 83(5) say" is arguably almost pure keyword/structured lookup and gets no special fusion treatment *unless* it hits `query_router`'s `structured` classification first, which bypasses fusion entirely for that case — see below).

**Chunk ranking / duplicate removal:** `_dedup_and_budget()` (`context_builder.py:26-47`) dedupes by `chunk_id` before building the prompt — correct, but it's a *within-single-retrieval* dedup only. For multi-subquery (comparative) questions, `_merge_multi_query_results()` (`rag_pipeline.py:139-203`) already dedupes across subqueries with a log-scaled frequency bonus before that — reasonable design, rewards chunks that surface under multiple independent queries without let a merely-repeated-but-weak chunk dominate a genuinely strong single match.

**Metadata filtering:** Works correctly for `structured`/`metadata`/`mixed` intents (F3's cost concern aside) — chunk-level regulation/authority/jurisdiction/article/section/clause filters are applied. One real quality gap: **`metadata`/`mixed` intent still runs the full hybrid retriever and post-filters its output** (`query_router.py:94-98`, explicitly flagged in its own docstring as a "v1 simplification... deferred"). If none of the top-`dense_k`/`sparse_k` hybrid results happen to match the metadata filter, the post-filter can zero out an otherwise-answerable query — the retriever never knew to *search within* the filtered set, only to filter *after* the fact. This is a real, if edge-case, quality gap for narrow-jurisdiction/narrow-regulation questions on a large multi-regulation corpus.

**Context ordering:** `final_rank`-based ordering throughout, consistent from fusion → rerank → merge → context build. No issues.

**Overall verdict:** the retrieval *logic* (fusion math, dedup, ranking) is sound and well-tested (existing test suite covers RRF, dedup, pruning explicitly). The weaknesses are at the *edges*: default reranking provides no real signal (Phase 3), metadata-scoped queries can silently under-retrieve (above), and the compliance-query fast path that exists in the schema isn't reachable from the query path that would benefit from it (F3).

---

## 3. Reranking Audit

**Current state:** `rerank_backend` defaults to `"passthrough"` (`config.py:47`, `dependencies.py:229-251`). `PassthroughReranker` (`passthrough_rerank.py`) does no scoring at all — it just truncates the RRF-fused list to `rerank_top_n` (default 5) in existing RRF order. Consequently `rerank_score` is `None` for every chunk in the default deployment, which means **`prune_by_score_margin()` (`context_pruning.py:29-31`) is a documented no-op in the default configuration** — it's written, tested, and completely inert unless `rerank_backend` is changed. This is worth flagging on its own: a real piece of quality-control logic exists in the codebase but never runs at default settings.

**Would a reranker meaningfully improve quality?** Yes, for the same reason it does in essentially every hybrid-RAG system: RRF fusion is a *rank-position* heuristic (1/(k+rank)), blind to actual semantic relevance beyond ordinal position in each of the two lists. A cross-encoder or hosted reranker scores query-chunk pairs directly and reliably reorders cases where a dense-retrieval-#8 result is actually more relevant than a dense-#2 that only ranked high because of surface lexical overlap. For a compliance corpus specifically — where a clause 3 sections away can look lexically similar to the one actually being asked about — this class of error is exactly what a reranker is good at catching, and the codebase already has two real implementations ready to enable (`CrossEncoderReranker`, `NvidiaRerankProvider`), just not defaulted on.

**At what corpus size does it become beneficial?** Reranking quality benefit is corpus-*diversity*, not corpus-*size*, driven: it starts mattering as soon as a single query's fused candidate set (`rerank_fused_top_n=8` by default) contains multiple documents with overlapping terminology — which for a multi-regulation compliance corpus (GDPR + HIPAA + SOC2 + ... all discussing overlapping concepts like "data breach notification") is true almost immediately, even at a few hundred chunks. This isn't a "wait until you have a million chunks" concern — the ambiguity a reranker resolves is present as soon as the corpus has more than one regulation in it, which per the app's own design (multi-regulation compliance) is the expected steady state, not an edge case.

**Would the latency trade-off be justified?**
- `CrossEncoderReranker` (local sentence-transformers/torch): adds model-inference latency (typically tens-to-low-hundreds of ms for 8 candidates on CPU) but **also adds a torch/sentence-transformers import and model load at startup**, which `dependencies.py`'s own comments say causes an OOM crash on a 512Mi free-tier instance. Only viable with real memory headroom.
- `NvidiaRerankProvider`: adds one more NVIDIA network call — and per **F1**, that call queues behind the global lock alongside every embedding/generation call already competing for it. Its request/response contract is also explicitly documented as "unverified against a live call" (`nvidia_rerank.py`) — not smoke-tested.

**Recommendation: add lightweight reranking (`cross_encoder` backend), conditional on deployment memory headroom — do not default it on a memory-constrained instance.**

Reasoning: the quality gap is real and present at today's corpus size (multi-regulation, not "someday at scale"), and `CrossEncoderReranker` already exists, is already tested, and doesn't compete for the NVIDIA lock (F1) the way the hosted option would. The blocker isn't engineering effort, it's operational — this only makes sense on an instance with enough memory to load a cross-encoder model without OOMing at startup, which is a deployment/infra decision, not a code change. If the production instance already has that headroom, enabling it is close to free relative to generation latency (seconds) and closes a real, present quality gap. If memory is still constrained, the honest answer is: keep passthrough, but know that `prune_by_score_margin` is dead code until this changes, and budget for the cross-encoder path once the instance is upgraded — don't reach for the hosted NVIDIA reranker as a "free" alternative, since it inherits F1's serialization cost.

---

## 4. Context Assembly Audit

`build_context()` (`context_builder.py:50-114`) + `_dedup_and_budget()` (`:26-47`) + `prune_by_score_margin()` (`context_pruning.py`):

- **Chunk ordering:** correct, `final_rank`-driven throughout, consistent between FLAT and GROUPED layouts.
- **Duplicate removal:** correct and cheap (`chunk_id`-keyed, O(n) over ≤20 candidates) — not a concern at any realistic per-request candidate count.
- **Token budgeting:** `approx_token_budget=2000` (hardcoded default in `build_context()`'s signature, not exposed via `Settings`), estimated as `chars // 4`. This is an approximation (documented as such), not a real tokenizer — for content that's unusually token-dense (tables, legal citations, numbered lists — exactly what a compliance corpus has a lot of) the 4-chars/token heuristic under-counts actual tokens, risking a prompt that's larger than intended. Not measured directly in this audit; flagged as a plausible drift source given the corpus's stated composition (Basel/CFR tables, per the dedup module's own comments about "table-heavy Basel docs").
- **Metadata formatting:** minimal — `[d1]\ntext` per chunk, or a subquery-grouped variant. No chunk metadata (heading, page, document type) is included in what's sent to the LLM, only in the citation-mapping side-channel (`build_citations`). This is a design choice, not obviously wrong, but means the model never sees, e.g., which document a chunk came from when reasoning about it — only the label.
- **Prompt construction:** `build_prompt()` (not fully audited here — out of the traced hot path, sub-millisecond regardless of content since it's a template fill).
- **The dead no-op (repeated from Phase 3):** `prune_by_score_margin` doesn't fire at default settings because `PassthroughReranker` never populates `rerank_score`. If reranking is enabled (Phase 3's recommendation), this stage becomes live and should be re-validated against real score distributions from whichever reranker is chosen — its margin threshold (`context_prune_margin=0.3`) was presumably tuned against *some* backend's score range, worth confirming which.

**Can context quality be improved?** Yes, primarily via Phase 3's reranking recommendation (the highest-leverage change — everything downstream of it, including pruning, currently inherits its inertness) and secondarily by replacing the char-based token estimate with a real tokenizer count if prompt-budget overruns are ever observed in practice (not confirmed in this audit, flagged as a plausible risk given corpus composition, not a measured problem).

---

## 5. Estimated Indexing Times

**Assumptions, stated explicitly (no PDF fixtures were run through the pipeline in this session):**
- Deployment: Postgres configured (`WorkerPool`, `RAG_WORKER_CONCURRENCY=4` default), `NvidiaProvider` for embeddings.
- A "typical" PDF: ~10 pages, ~3,000 chars/page ≈ 30,000 chars total, extracted via the column-aware `pdfplumber`-based loader.
- `RecursiveChunker` defaults (`chunk_size=500, chunk_overlap=150`, effective stride ~350 chars) → **≈85 chunks/PDF**. A clause-heavy regulation document routed through `ClauseChunker` would chunk differently (more, smaller chunks); this estimate uses the general-document default.
- Embedding batch size 90 texts/request (`_EMBED_BATCH_SIZE`, `pipeline.py:126`) → **1 batch call per PDF** at this chunk count.
- **F1 applies throughout**: every embed call is serialized against every other NVIDIA call in the process, regardless of `WorkerPool` concurrency.
- Per-stage cost estimates (labeled, not measured): PDF parse+chunk ≈0.5-1.5s CPU-bound (pdfplumber table-aware extraction, GIL-serialized — concurrent workers do *not* parallelize this within one process the way I/O-bound stages do); 1 embed batch call ≈1.5-3s (NVIDIA network RTT for a 90-text batch); vector upsert ≈85 individual `index.update()` calls at ~20 concurrent (`_MAX_CONCURRENT_UPDATES=20`, `pinecone_vector_store.py:11`) ≈0.5-1.5s wall time for the concurrent batch, **doubled in effect by F2's sibling finding — dead `index_combined` fast path (below)**; BM25 postings write ≈1 indexed SQL insert batch, <200ms; compliance detection ≈0-1 indexed lookup per compliance chunk, negligible for general docs.

| PDFs | Upload response time | Queue wait (idle queue) | Parse+chunk (serial, single worker's share) | Embedding (F1-serialized across ALL workers) | Vector upsert + BM25 + compliance | **Total wall-clock to all `ready`** |
|---|---|---|---|---|---|---|
| 1 | <2s (bytes written, job enqueued, 202 returned) | ~0s | ~1s | ~2s | ~1.5s | **~5s** |
| 2 | <2s | ~0-2s (2nd worker starts immediately, 4 workers idle) | ~1s each, parallel | **~4s** (2 embed calls, serialized by F1, not 2s parallel) | ~1.5s each, can overlap across workers | **~7-8s** |
| 4 | <2s | ~0s (fits in 4 workers) | ~1s, parallel | **~8s** (4 embed calls, F1-serialized to one at a time) | overlaps with other workers' non-embedding stages | **~10-12s** |
| 10 | <2s | first 4 start immediately, next 6 queue behind worker availability | parallel across available workers | **~20s** (10 embed calls × ~2s, F1-serialized regardless of 4 workers) | overlaps | **~22-25s** |
| 50 | <2s | queues behind 4-worker throughput | parallel, bounded by worker count | **~100s** (50 × ~2s, still one-at-a-time through F1) | overlaps | **~105-115s (~2 min)** |
| 100 | <2s | same | parallel, bounded by worker count | **~200-300s** (100 × ~2-3s serialized) | overlaps | **~210-320s (~3.5-5.5 min)** |

**The dominant term at every scale above 1 PDF is the embedding stage, and specifically F1** — note that the "4 workers" concurrency setting barely moves the needle on total wall-clock time once more than ~1 document is in flight, because **F1 collapses embedding throughput to roughly one batch call at a time no matter how many workers exist.** Parsing/chunking and vector-upsert *do* parallelize correctly across `WorkerPool`'s workers; embedding does not. This is the headline finding of Phase 5: **the worker queue built in the prior milestone provides real concurrency for I/O against Pinecone/Postgres, but delivers close to zero throughput benefit for the embedding stage specifically**, because of a constraint (F1) that predates and is orthogonal to the worker queue.

---

## 6. Scaling Projection

| Corpus size | What breaks first | Why |
|---|---|---|
| 1,000 PDFs (~85k chunks) | Nothing structural yet — ingestion just takes proportionally longer (F1-bound, ~1,000 × 2-3s ≈ 35-50 min total embedding time, spread over however long uploads trickle in). Query-time: BM25/dense/compliance-indexed lookups are all still O(1)-ish per the prior milestone's indexing work. | F1 is a throughput ceiling, not a scale-dependent one — it's exactly as bad at 1,000 docs as at 10. |
| 10,000 PDFs (~850k chunks) | **`PineconeChunkStore._scan_all()`'s full-corpus scan** (`get_by_document`, `get_document_hash` for the scanning-fallback dedup path, `get_by_legal_metadata` for F3's query-time compliance path, `get_document_summaries` for the citation filename map) starts being genuinely slow even with concurrent paging and the 300s cache — a cache miss means minutes, and F3 means every non-cached compliance-scoped question pays it. | This is exactly the O(corpus) surface the prior two milestones deliberately left on the *write* path (fixed) but the *query-time metadata filter path* (F3) still has it. |
| 100,000 PDFs (~8.5M chunks) | **Postgres connection pool** (`max_size=10`, shared by every repository *and* now every worker thread) becomes a real contention point under concurrent ingestion + query traffic — flagged as technical debt in the worker-queue milestone's own self-review, not new to this audit. BM25's SQL scoring query (`bm25_repository.py`) does a `join` across `bm25_postings`/`bm25_doc_stats` per query term — still indexed, but worth re-profiling at this row count (postings table would be on the order of 8.5M+ rows depending on unique term count per chunk). | Both are foreseeable, both already partially disclosed in prior milestones' self-reviews, neither yet measured against real data at this scale. |
| 1,000,000 PDFs (~85M chunks) | **Single-instance deployment model itself** (`Metrics`, `RateLimiter`, and — pre-this-milestone — `JobStore` were all explicitly `ponytail:`-flagged as single-instance-only) becomes the real ceiling: one process, one Postgres pool, one NVIDIA API key with F1's global lock, no horizontal scaling path for the embedding throughput bottleneck (running multiple *processes* wouldn't even help — F1 is per-process, so multiple processes would remove the artificial serialization but multiply real 429 risk against NVIDIA's actual per-account rate limit, which is the thing F1 was built to respect in the first place). At this scale, the architecture needs a genuinely different embedding-throughput strategy (e.g., a provider-side batch/async embedding API, multiple API keys/accounts, or a different embedding provider with higher rate limits) before anything else here matters. | This is the natural ceiling of "one account, one process" — not a bug, a scale boundary the current design was never meant to cross. |

**Next bottleneck after the changes already made (worker queue + retry hardening):** unambiguously **F1, the global NVIDIA request lock**. The prior milestone correctly identified and fixed the *durability/concurrency-safety* gap (job queue) and the *reliability* gap (retry/timeout). It did not touch — and the worker queue's own design didn't need to touch — the *throughput* ceiling, which was never in that milestone's scope. It's the load-bearing finding of this audit.

---

## 7. Remaining Bottlenecks (Ranked)

1. **F1 — global NVIDIA lock serializes all embedding/generation/rerank calls process-wide.** Dominates every latency and throughput number in this report once more than one request/job is in flight. Highest-leverage fix available, not attempted here per audit scope.
2. **F2 — N+1 Pinecone fetch per retrieved chunk** (dense + sparse hydration). Mechanical, low-risk fix already has the right primitive (`get_many_with_embeddings`) sitting unused nearby.
3. **Dead `index_combined`/`supports_combined_write` fast path** (`index_manager.py:58-90`) — built, never called from `IngestionPipeline`. Using it would collapse chunk-metadata-write + vector-write from two round-trips per chunk (placeholder upsert + per-id update) to one batched upsert per batch of 100.
4. **F3 — compliance/metadata queries bypass the indexed `ComplianceRepository`**, falling back to `PineconeChunkStore`'s full-scan `get_by_legal_metadata()` instead.
5. **Postgres pool `max_size=10`, shared across all repositories and worker threads** — already disclosed as debt in the worker-queue milestone, reconfirmed here as the next thing to measure once concurrent load is real.
6. **Reranking is a no-op at default config** (Phase 3) — `prune_by_score_margin` inert as a consequence.
7. Char-based token budget estimate (`_CHARS_PER_TOKEN_ESTIMATE=4`) — plausible but unverified drift source for token-dense compliance content.

## 8. Overall Production Readiness Score: **6.5 / 10**

**What earns the points:** correctness is solid (dedup, RRF, fusion, pruning logic, citation verification — all tested, no correctness bugs found in this audit), the storage/repository architecture from the prior two milestones is genuinely sound (indexed dedup, incremental BM25, claim-based durable job queue, retry/timeout hardening), and the codebase is honest with itself — nearly every gap found in this audit was either already disclosed in a prior milestone's self-review or is visible in a `ponytail:`-tagged comment admitting the simplification. That's a codebase that knows its own limitations, which is worth more than it sounds.

**What holds it back from higher:** one architectural constraint (F1) that silently caps real-world throughput and inflates latency under any concurrency, discovered by this audit rather than previously disclosed — meaning the "the worker queue gives you concurrent ingestion" claim from the prior milestone is *true for I/O but not for the stage that actually dominates ingestion time*. That's a meaningful gap between documented capability and actual behavior under load, and it's exactly the kind of thing a load test (not yet run) would have caught immediately. Until F1 is addressed or at minimum load-tested to confirm/refute this audit's estimates, I'd treat "production-ready" as true for correctness and durability, **not yet validated for throughput under concurrent load** — which is precisely what Phase 5/6 were unable to confirm directly (no live benchmark was run) and had to estimate from code paths instead.

**Recommended next step, in order:** (1) run an actual load test against a real Pinecone/NVIDIA/Postgres backend to confirm or correct this audit's F1-dominated estimates — everything above is code-path reasoning, not measurement; (2) if confirmed, address F1 before anything else in this list, since it's the one finding that changes the shape of every other number in this report.
