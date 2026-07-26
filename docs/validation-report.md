# Production Performance Validation Report

Follow-up to `docs/production-readiness-report.md`. That report's findings were code-path estimates; this one replaces every one of them with a real measurement, run against a live NVIDIA account, a live Pinecone account (free-tier, fresh — the original account's monthly write-unit quota was exhausted mid-session and had to be swapped, see below), and the real `inteliai-rag` Supabase/Postgres project via MCP. Benchmark scripts, corpus, and raw output are described inline; no numbers in this report are estimated.

**Scope note:** no `RAG_SUPABASE_DB_URL` was available, so the ingestion/retrieval benchmarks ran against the **scanning-fallback** (no-Postgres) repository path, not the Postgres-backed `WorkerPool`/incremental-BM25 path built in the worker-queue milestone. Where that matters, it's called out per finding. F4's Postgres-side numbers are real, pulled directly from the live schema via Supabase MCP `execute_sql`/`EXPLAIN ANALYZE`.

**One correctness bug was found and fixed during this validation** (not a performance finding) — see "Bug found and fixed," below, before the findings table. Per the working agreement for this audit, no other code was changed; every other finding here is reported, not fixed.

---

## Bug found and fixed (not part of the original 4 findings)

Running the real ingestion load test crashed on the second document with a numpy `ValueError: matmul... size 0 is different from 1024`. Root cause: `PineconeChunkStore._scan_all()` caches scan results with each entry's *embedding* slot set to a placeholder `[]` (real embeddings are deliberately not cached — documented as such in the class's own comment). `all_with_embeddings()` is supposed to always bypass that cache and take the real, uncached fetch path (also documented) — but the code never actually enforced that. A metadata-only scan (`get_document_hash()`, called at the start of every `ingest()`) that ran to completion within the 300s cache TTL would warm the cache with `[]`-embedding entries, and a same-request `all_with_embeddings()` call moments later (dedup's near-duplicate candidate fetch) would silently get back `[]` for every chunk's embedding instead of the real vector — crashing the dedup cosine-similarity matmul.

This meant: **in the scanning-fallback (no-Postgres) deployment mode, ingesting a second document into a non-empty corpus crashed, essentially always**, for any deployment actually using that supported configuration. Fixed with a 5-line change (`_scan_all(force_refresh: bool)`, `all_with_embeddings()` passes `force_refresh=True`) matching the behavior the code already documented as intended. Commit `e1c55093`. Clears 3 of the 7 previously-documented pre-existing test failures as a side effect (they were this same bug). Regression test added (`test_all_with_embeddings_ignores_a_metadata_only_scan_cached_moments_earlier`).

---

## Finding F1 — Global NVIDIA lock

### ✅ CONFIRMED

**Measured value:** Effective throughput pinned at **1.10–1.19 req/s regardless of concurrency** (N=1: 1.13 req/s, N=2: 1.19 req/s, N=4: 1.10 req/s, N=8: 1.14 req/s). Wall-clock time at each N tracked the "fully serialized" prediction (N × single-call baseline) within 0.8–9.3%:

| N concurrent embed() calls | Baseline single-call (median of 3) | Measured wall time | Predicted if fully serialized (N × baseline) | Predicted if fully parallel (baseline) | Measured vs serialized prediction |
|---|---|---|---|---|---|
| 1 | 835.4ms | 888.8ms | 835.4ms | 835.4ms | +6.4% |
| 2 | — | 1684.1ms | 1670.8ms | 835.4ms | +0.8% |
| 4 | — | 3651.5ms | 3341.6ms | 835.4ms | +9.3% |
| 8 | — | 7017.5ms | 6683.2ms | 835.4ms | +5.0% |

**Expected value (from the original report):** throughput should scale roughly linearly with concurrency up to the account's real rate limit if the lock weren't the bottleneck (e.g., N=8 → ~8-9 req/s).

**Difference:** at N=8, measured throughput (1.14 req/s) is **88% lower** than the fully-parallel theoretical ceiling (~9.58 req/s) — an **8.4x** slowdown attributable entirely to the lock, not to NVIDIA's actual rate limit (which was never hit — no 429s occurred during this test).

**Root cause:** `_nvidia_throttle.slot()` (`rag_hybrid_search/providers/_nvidia_throttle.py:24-34`) is a single process-wide lock held for the full request/response round trip. Confirmed by direct measurement of the real object, not inferred.

**Potential improvement:** replace the single global lock with a bounded semaphore sized to NVIDIA's actual concurrent-request limit (not measured in this session — would need a separate test intentionally probing for 429s at increasing concurrency to find the real ceiling) instead of a hard 1-at-a-time gate. The lock's own docstring already explains *why* naive start-time-only pacing failed (429s at 2s spacing) — the fix isn't "remove the lock," it's "widen it correctly."

**Estimated ROI:** high. This is the single largest, most broadly-applicable throughput fix available — it affects every embedding call, every generation call, and every concurrent retrieval or ingestion job in the system, confirmed by direct measurement, not inference.

---

## Finding F2 — N+1 Pinecone fetch

### ✅ CONFIRMED

**Measured value (real 58-vector corpus, 4 real queries):**

| Path | Pinecone calls per query | Median retrieval latency |
|---|---|---|
| Current (`dense.py`'s per-hit `chunk_store.get()` loop) | 1 query + 10 individual `fetch()` = **11 calls** | **3552.0ms** |
| Batched prototype (1 `fetch(ids=[...])` for all hits) | 1 query + 1 batched `fetch()` = **2 calls** | **2799.1ms** |

**Expected value (from the original report):** dense hydration alone estimated at ~50-150ms (query) + ~200-600ms (10×20-60ms fetches) ≈ 250-750ms total.

**Difference:** actual per-call Pinecone latency on this account/tier is **far higher than the original estimate** (individual `fetch()` calls measured at roughly 250-550ms each, not 20-60ms) — meaning the *absolute* latency numbers in the original report were too optimistic by roughly 5-10x, though the *relative* mechanism (N+1 calls vs 1 batched call) is exactly as described. Call-count reduction is a clean **82%** (11→2); latency reduction from batching alone is **21%** (median), smaller than call-count alone would suggest, because query() carries its own fixed cost that batching doesn't touch, and this account's per-call overhead doesn't scale perfectly linearly with hit count in the batched call.

**Root cause:** `DenseRetriever.search()` (`dense.py:34-38`) and `SparseRetriever.search()` (`sparse.py:25-29`) each call `chunk_store.get(chunk_id)` in a loop; `ChunkStore.get_many_with_embeddings()`-style batching already exists elsewhere in the same class and isn't reused here.

**Potential improvement:** add a `get_many(chunk_ids)` (metadata-only, no embeddings needed at retrieval time) to `ChunkStore` and use it in both `DenseRetriever`/`SparseRetriever` instead of the per-id loop.

**Estimated ROI:** medium-high. Confirmed real latency win (21% in this test) plus an 82% reduction in Pinecone API call volume (meaningful for cost/rate-limit headroom independent of latency), at k=10/10 defaults — the win grows with `dense_k`/`sparse_k` since call count is linear in k while a batched fetch stays at 1 call regardless.

---

## Finding F3 — Dead `index_combined()` path

### ✅ CONFIRMED (and found to also be broken, independent of being unused)

**Measured value (real 20-chunk synthetic document):**

| Path | Pinecone calls | Latency |
|---|---|---|
| Current (`chunk_store.put_many()` + `vector_store.upsert_many()`) | 1 `upsert` + 20 `update` = **21 calls** | **2918.5ms** |
| Combined (`chunk_store.put_many_with_embeddings()`, the primitive `index_combined()` would call) | 1 `upsert` = **1 call** | **883.6ms** |

**Expected value (from the original report):** expected the combined path to be meaningfully faster by collapsing two round-trips per chunk into one; not quantified there.

**Difference:** measured **70% latency reduction** and a **21→1 (95%)** Pinecone call-count reduction for a 20-chunk document — larger than the original report implied ("collapse from two round-trips to one" undersold it; the current path is actually *N+1* round trips — 1 upsert + N individual updates — not 2, so the real win is bigger than "two round trips become one").

**Additional discovery, not in the original report:** `IndexManager.supports_combined_write()` (`index_manager.py:65-69`) — the gate function that would decide whether `index_combined()` is safe to call — **raises `AttributeError`** on every real call: it checks `self.chunk_store._index is self.vector_store._index`, but neither `PineconeChunkStore` nor `PineconeVectorStore` has an `_index` attribute (they store the connection as `_client`). Confirmed live: calling it against real objects threw immediately. This means `index_combined()` isn't just unused — even if a caller were added today using the documented pattern (`if index_manager.supports_combined_write(): index_manager.index_combined(...)`), it would crash before ever reaching the fast path. Not fixed here (zero production callers, so not a live bug — this audit is the first time the function has ever been exercised in any form), but it means wiring this in requires fixing `supports_combined_write()` first, not just adding a call site.

**Root cause:** `IngestionPipeline.ingest()` (`pipeline.py:235`) unconditionally calls `index_manager.index()`, never checks for or calls `index_combined()`.

**Potential improvement:** fix `supports_combined_write()`'s attribute check, then call it from `IngestionPipeline.ingest()` before choosing between `index()` and `index_combined()`.

**Estimated ROI:** high for ingestion throughput specifically — confirmed 70% latency reduction on the vector-write stage, which per the real ingestion load test below is the single largest chunk of per-document ingestion time after embedding.

---

## Finding F4 — Compliance repository query-time routing

### ✅ CONFIRMED — most severe finding in this report

**Measured value:**

| Path | Real measurement |
|---|---|
| Current: `PineconeChunkStore.get_by_legal_metadata()`, cold cache, **real 58-vector corpus** | **13,996.6ms** (≈14 seconds) |
| Current: same call, warm cache (second call, same process, within 300s TTL) | **0.0ms** |
| Proposed: `PostgresComplianceRepository`-equivalent indexed query, **real 20,000-row `chunks` table** (Supabase `inteliai-rag`, via `EXPLAIN ANALYZE`) | **0.336ms** execution time, `Index Scan using chunks_organization_id_legal_regulation_legal_authority_leg_idx`, 7 rows matched |
| Same query, indexes disabled (`enable_indexscan=off`), forcing a sequential scan | **7.236ms** execution time, `Seq Scan`, 19,993 rows filtered out |

**Expected value (from the original report):** "cache hit: ~0ms; cache miss: seconds-to-minutes at real corpus size" — a range, not a number, explicitly hedged as an estimate.

**Difference:** the *cold-cache* cost is **dramatically worse than expected at this corpus size** — 14 seconds at only 58 vectors, not "at real corpus size" as originally hedged; this account's per-call Pinecone latency (confirmed in F2/F3 above, ~300-900ms/call) means even a trivially small scan is already this expensive. The *indexed alternative* is confirmed sub-millisecond at 20,000 rows (**345x the vector count** in this comparison) — the composite index genuinely does bound the query cost by clause-cardinality, not corpus size, exactly as designed. Cross-service comparison: cold-cache Pinecone scan (14,000ms) vs indexed Postgres lookup (0.336ms) is a **~41,600x** difference in this specific measurement — not a fair apples-to-apples "same backend" comparison, but it is the *actual real-world choice* being made by `query_router.py`'s current routing, and that choice currently pays the 14-second side of it on every cache miss.

**Root cause:** `query_router.route_query()` (`compliance/query_router.py:87,95`) calls `chunk_store.get_by_legal_metadata()` directly instead of `ComplianceRepository.find_matching()`, even when a Postgres-backed `ComplianceRepository` is configured and available.

**Potential improvement:** thread the already-injected `ComplianceRepository` into `query_router.route_query()` and use it for `structured`/`metadata`/`mixed` intent instead of `chunk_store.get_by_legal_metadata()`, falling back to the current behavior only when no Postgres repository is configured (matching every other repository's existing Postgres-vs-scanning selection pattern).

**Estimated ROI: highest of the four findings.** This is a compliance-query-classification app; `structured`/`metadata`/`mixed` intent is the primary use case for a meaningful fraction of real queries, and the measured cost of the current default path is catastrophic on any cache miss, confirmed at a corpus size 345x smaller than the one already sitting in the real Postgres schema with the fix ready to use.

---

## Real Ingestion Load Test (1 / 2 / 4 / 10 documents)

**Scope:** scanning-fallback path (no live `RAG_SUPABASE_DB_URL`), single in-process worker — not the `WorkerPool`/4-concurrent-worker path. Real NVIDIA embeddings, real Pinecone writes, 10 distinct synthetic compliance-style markdown documents (~2.5-3.1KB each, ~6 chunks/doc, 58 total chunks), timed via log-timestamp capture (zero code changes — an external logging handler reading the pipeline's own existing `ingest:` log lines).

| Document | Total | Parse | Chunk | Embed | Upsert+BM25+compliance |
|---|---|---|---|---|---|
| doc_01 | 3129.5ms | 0.8ms | *(unchanged, skipped)* | *(unchanged, skipped)* | *(unchanged, skipped)* |
| doc_02 | 4489.1ms | 1.0ms | 507.8ms | 657.6ms | 3322.8ms |
| doc_03 | 4368.6ms | 0.4ms | 0.1ms | 587.7ms | 3780.4ms |
| doc_04 | 5025.2ms | 0.4ms | 0.1ms | 564.1ms | 4460.6ms |
| doc_05 | 4586.3ms | 0.4ms | 0.1ms | 585.9ms | 3999.9ms |
| doc_06 | 23933.6ms | 0.4ms | 0.1ms | 565.0ms | **23368.1ms** |
| doc_07 | 35389.9ms | 0.4ms | 0.1ms | 976.4ms | **34413.1ms** |
| doc_08 | 56119.3ms | 1.6ms | 0.8ms | 658.0ms | **55459.0ms** |
| doc_09 | 9862.3ms | 0.8ms | 0.9ms | 652.6ms | 9208.1ms |
| doc_10 | 9081.0ms | 0.4ms | 0.1ms | 638.0ms | 8442.5ms |

**Derived N-document scenarios (single-worker, cumulative):**

| N | Total wall time to last doc `ready` |
|---|---|
| 1 | 3.13s |
| 2 | 7.62s |
| 4 | 17.01s |
| 10 | **155.98s** (≈2.6 minutes) |

**This is a materially different picture than the original estimate, and reveals a fifth real bottleneck not identified in the original audit:**

- **Embedding is not the dominant cost** in this real run — it stayed flat and small (565-976ms per document, matching F1's real single-call baseline almost exactly, good cross-validation). The original report's claim that embedding dominates ingestion time is **refuted for the scanning-fallback path** by this measurement (though F1 is still real and still matters — it just isn't the bottleneck *here*, because this test never had more than 1 worker's worth of embedding concurrency to serialize in the first place).
- **"Upsert+BM25+compliance" dominates overwhelmingly**, and it **grows with corpus size then behaves erratically** (3.3s → 3.8s → 4.5s → 4.0s → 23.4s → 34.4s → 55.5s → 9.2s → 8.4s). Root cause, confirmed by code inspection cross-referenced with the bug fix above: this stage bucket includes the near-duplicate dedup step's `all_with_embeddings()` call, which — **after this session's bug fix** — now *always* does a real, uncached, full-corpus Pinecone scan (that's the correct behavior; the bug was that it wasn't doing this reliably before). It also includes `rebuild_bm25_index()`'s full `chunk_store.all()` scan (the scanning-fallback BM25 index has no incremental API, by design). Both scale with corpus size, and both pay this account's real ~300-900ms-per-Pinecone-call tax multiplied by however many pages/ids the scan touches. The growth trend through doc_08 (3.3s→55.5s) matches an O(corpus) scan cost growing with each added document; the drop at doc_09/doc_10 (55.5s→9.2s→8.4s) is real, measured, and **not fully explained** by this audit — plausible causes include Pinecone-side eventual-consistency/indexing-lag variance or this specific free-tier account's variable backend load, but this wasn't isolated further. **This is disclosed as an open question, not resolved.**
- **Compliance detection itself contributed ~0** — none of the 10 synthetic documents had `legal_metadata` set (general documents, not `document_type="regulation"`), so `_detect_and_mark_superseded()` short-circuited immediately for every chunk. The "upsert+BM25+compliance" bucket's cost is not from compliance detection in this run.

**Conclusion:** the original report's Phase 5/6 estimate — "embedding dominates, scaling is roughly linear, F1 is the main risk" — is **refuted for the scanning-fallback deployment mode** by real measurement. The real dominant cost in that mode is the **O(corpus) full-scan pattern in near-dup dedup and BM25 rebuild**, which is exactly the problem the Postgres-backed incremental repositories (already built, in a prior milestone) exist to eliminate — this data is strong, real evidence *for* requiring Postgres in any production deployment of this app, not just a nice-to-have. This load test could not validate the Postgres-backed path directly (no `RAG_SUPABASE_DB_URL`), so whether the incremental path actually avoids this growth remains **NOT VALIDATED** — architecturally very likely true (it's exactly what that repository layer was built to do, and F4 independently confirmed the same indexed-Postgres-path pattern is fast at 20,000 rows), but not measured end-to-end in this session.

---

## Retrieval Load Test (1 / 5 / 10 concurrent queries)

Real `retriever.retrieve()` calls (dense + sparse + RRF + passthrough rerank) against the real 58-vector corpus, real NVIDIA query embeddings, real Pinecone reads.

| N concurrent | Wall time | Throughput | Failures | avg | p50 | p95 | p99 | min | max |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 6146.5ms | 0.163 req/s | 0/1 | 6146.2ms | 6146.2ms | 6146.2ms | 6146.2ms | 6146.2ms | 6146.2ms |
| 5 | 7683.2ms | 0.651 req/s | 0/5 | 6036.2ms | 6621.2ms | 7506.0ms | 7647.0ms | 3064.3ms | 7682.3ms |
| 10 | 11348.1ms | 0.881 req/s | 0/10 | 7000.2ms | 7114.5ms | 10889.5ms | 11255.4ms | 2978.0ms | 11346.8ms |

**Zero failures at any concurrency level** — the system degrades gracefully (higher latency, not errors) under this load, which is a genuinely good sign the original report couldn't confirm without a real test.

**Throughput scales sub-linearly, not flat** (0.163 → 0.651 → 0.881 req/s from N=1 to N=10 — a 5.4x throughput increase for a 10x concurrency increase), which is a more nuanced picture than either "F1 pins it flat" (the original report's framing) or "scales linearly" would predict. Explanation: Pinecone reads (F2's N+1 fetch loop, the dominant per-call cost measured above) are **not** subject to F1's lock — only the one query-embedding call per `retrieve()` is. So concurrent retrievals *do* get real parallelism on their dominant cost (Pinecone fetches), while still queueing on the smaller embedding-call cost. Net effect: real speedup from concurrency, but far below ideal, and p95/p99 latency grow substantially under load (p95 nearly doubles from N=5 to N=10: 7506ms → 10889ms) — consistent with F2 (N+1 fetch) being the true dominant bottleneck at this account's Pinecone latency, with F1 as a secondary, additive tax on top.

---

## Summary Table

| Finding | Verdict | Headline number |
|---|---|---|
| F1 — Global NVIDIA lock | ✅ Confirmed | Throughput pinned at ~1.1-1.2 req/s regardless of concurrency (1/2/4/8); 88% throughput loss vs theoretical parallel ceiling at N=8 |
| F2 — N+1 Pinecone fetch | ✅ Confirmed | 11→2 Pinecone calls (82% fewer), 3552ms→2799ms median latency (21% faster) |
| F3 — Dead `index_combined()` path | ✅ Confirmed (+ found broken independently) | 21→1 Pinecone calls (95% fewer), 2918ms→884ms (70% faster); its own gate function crashes on first call |
| F4 — Compliance query routing | ✅ Confirmed, most severe | 14.0s cold-scan (58 vectors) vs 0.336ms indexed Postgres lookup (20,000 rows) |
| Ingestion load test | Original estimate ❌ Refuted for scanning-fallback mode | Embedding stayed flat (~0.6-1.0s/doc); O(corpus) dedup+BM25 scan dominated instead (up to 55s/doc), growing then unexplainedly dropping |
| Retrieval load test | ⚠️ Partially confirmed | Zero failures; throughput scales sub-linearly (5.4x for 10x concurrency) — F2 is the larger real contributor, F1 additive on top, neither alone explains it fully |
| Bug: `all_with_embeddings()` cache | N/A — found live, fixed | Crashed real ingestion on the 2nd document in the scanning-fallback path; fixed, regression-tested |

## What changed from the original report's conclusions

1. **F1 is real but was not the dominant cost in the actual load tests run this session** — it's confirmed as a severe, measurable throughput ceiling in isolation (validated directly), but F2 (N+1 fetch) and the O(corpus) scan pattern turned out to cost more, in real seconds, in the scenarios actually measured here.
2. **A new, more severe bottleneck was found**: the O(corpus) scan pattern in the scanning-fallback dedup/BM25 path, which the original report's Phase 6 correctly flagged as a *future* scaling risk ("10,000 PDFs") but this session's real 10-document test shows is **already** the dominant ingestion cost, in that deployment mode, today.
3. **F4 is confirmed as more severe than hedged** — "seconds-to-minutes at real corpus size" undersold it; 14 seconds at 58 vectors is worse than the low end of that hedge would suggest for a corpus this small.
4. **A real, previously-unknown crash bug was found and fixed** — not predicted by the original static-analysis-only report, only surfaced by actually running the code under real load.
5. Every dollar-figure-adjacent absolute latency number in the original report was **directionally right but numerically too optimistic** — this specific Pinecone account/tier's real per-call latency (~300-900ms) is meaningfully higher than the ~20-60ms assumed there. This is disclosed as a real, measured characteristic of the accounts used for this validation, not necessarily representative of every production Pinecone deployment tier — but it is what was actually measured, and no number in this report has been adjusted to compensate for that.

## Recommended next step

With every finding now evidence-backed, the priority order for actually implementing fixes (not done in this session, per its scope) should be:

1. **F4** (compliance query routing) — highest measured ROI, smallest code change (wire an already-built repository into an already-injected code path).
2. **The O(corpus) scan pattern discovered in the ingestion load test** — architecturally, this is "use the Postgres-backed repositories in production," which already exist; the real gap is operational (get a working `RAG_SUPABASE_DB_URL` into the deployment), not a new code change.
3. **F3** (dead combined-write path) — second-highest confirmed ROI, requires fixing `supports_combined_write()` first.
4. **F2** (N+1 fetch) — confirmed real but smaller win than F3/F4 in absolute terms.
5. **F1** (NVIDIA lock) — confirmed severe in isolation; sizing the correct concurrency limit (not just "remove the lock") needs one more targeted test (find the real NVIDIA rate limit) before implementing.

---

# Addendum — Postgres-backed path validation (real `RAG_SUPABASE_DB_URL`)

This session got a real `RAG_SUPABASE_DB_URL` for the live `inteliai-rag` Supabase project (the "Scope note" above no longer applies for the repository/WorkerPool layer). No NVIDIA or Pinecone key was available this session, so F1-F3 and the NVIDIA/Pinecone-side numbers above are unchanged, real measurements from the prior session, not re-run. Everything below is new, real, against the live Postgres database — `PostgresDocumentRepository`, `PostgresChunkRepository`, `PostgresBM25Repository`, `PostgresComplianceRepository`, `PostgresJobRepository`, and `WorkerPool`, exercised directly (not through the full NVIDIA/Pinecone-dependent `IngestionPipeline`, which still needs those keys).

**Credential handling:** the DB password was supplied ad hoc in this session, not committed. `.env.development` (tracked in git) was left untouched; the URL was passed inline as an environment variable to each one-shot Python process and never persisted to disk or shell history. Note the app itself has no dotenv loading anywhere (`Settings` is plain `pydantic-settings`, env-only) — `.env.development` is a human-readable template only, never actually read by the app.

**Region note:** the `.env.development` template's example pooler host (`aws-0-us-east-1.pooler.supabase.com`) is correct for this project (`us-east-1`), but the direct-connection host (`db.<ref>.supabase.co`) only resolves to an IPv6 address from this environment, which has no outbound IPv6 route — the pooler host is not just "the recommended option," it's the only one that actually connects here.

## Three previously-undetected crash bugs, found and fixed

None of these were caught before because the integration test suite that exercises this exact code (`tests/storage/test_postgres_repositories.py`, `tests/storage/test_job_repository.py`) is `skipif`-gated on `RAG_SUPABASE_DB_URL` and had **never once run** — not in this project's history, not in CI, not manually — until this session. All three are one-line-per-call-site fixes, applied:

1. **`conn.executemany()` doesn't exist on psycopg3's `Connection`.** `PostgresChunkRepository.record_many()` and `PostgresBM25Repository.record_many()` both called it (4 call sites total) — psycopg3 only has `executemany()` on a `Cursor`, not a `Connection` (confirmed: `hasattr(psycopg.Connection, "executemany")` is `False`). This meant **every real Postgres-backed chunk write and every real Postgres-backed BM25 write crashed with `AttributeError`, unconditionally, on every call** — the entire point of this milestone (incremental BM25, indexed dedup) was unreachable code. Fixed by opening a cursor (`with conn.cursor() as cur: cur.executemany(...)`).
2. **`simhash()` returns unsigned 64-bit; `chunks.simhash` is a signed `bigint`.** Any simhash with the top bit set (~50% of all real text, at random) overflows Postgres's signed 64-bit range and fails with `NumericValueOutOfRange`. Nothing in the codebase ever reads `chunks.simhash` back into Python (near-dup matching goes through the `chunk_simhash_bands` table, computed from the original in-memory value at write time), so a lossless two's-complement wraparound before storage is a safe, no-behavior-change fix (`_to_signed_bigint()`, `chunk_repository.py`).
3. **`legal_is_current` is `NOT NULL DEFAULT true`; `_legal_fields()` returned `None` for it on every non-legal chunk.** Since most real documents aren't `document_type="regulation"` (a non-legal chunk gets `legal_metadata=None` entirely, by the model's own design), this meant **every ordinary (non-compliance) document crashed on ingest** via `NotNullViolation` — this is not an edge case, it's the common case. Fixed by defaulting to `True` (matching both `LegalMetadata.is_current`'s own default and the column's own DB default) instead of `None`.

Net effect before this session: the Postgres-backed write path was **completely non-functional** for any real document, compliance or not — not "falls back to scanning," strictly worse: it throws. This is a materially different (worse) finding than "the Scope note" in the original report anticipated ("get a working `RAG_SUPABASE_DB_URL` into the deployment" was framed as the main gap; the schema/driver-mismatch bugs above mean a working URL alone would not have been enough).

## Integration test suite: run for the first time, 2 test-fixture bugs also found and fixed

Running `test_postgres_repositories.py`/`test_job_repository.py` for the first time surfaced (and fixed) two test-only bugs, unrelated to production code:
- `organization_id` fixture teardown deleted `from organizations where organization_id = %s` — but `organizations`' key column is `id`, not `organization_id` — so teardown threw `UndefinedColumn` on every test, every run, leaking a fresh `test-org` row (plus, before the bugs above were fixed, orphaned chunks/postings) into the live DB on every single test invocation. Fixed.
- 5 of the tests inserted chunks referencing a `document_id` (`"doc-1"`/`"doc-2"`) that was never written to the `documents` table, so they only "worked" by accident once `record_many()` itself was broken (bug #1) — once fixed, they hit `documents`' real FK constraint. Fixed by inserting the document row first, matching what `IngestionPipeline`'s real unit-of-work always does.
- `test_job_repository.py`'s `repo` fixture created an `organizations` row with **no teardown at all** — every run left that org and its jobs in the live DB permanently. Fixed (added cleanup).

This session's misuse of the test DB (crashed runs before the fixes above landed) also left **28 orphaned `test-org` organizations** and **3 stuck `processing` jobs** in the live `inteliai-rag` project from repeated runs; all were identified and purged (see "Real measurements," cleanup is verified below).

**Result after fixes: 27 of 28 tests pass for the first time ever.** The one remaining failure is real, not a fixture bug:

## New finding — near-duplicate LSH banding has a real recall gap

`test_chunk_repository_near_duplicate_candidates_via_lsh_bands` asserts that a single-word substitution ("...lazy dog **in** the park..." → "...lazy dog **at** the park...") is found as a near-duplicate candidate via the 8-bands×8-bits LSH scheme. It isn't:

```
simhash(original) = 15519638141880428831, bands = [31, 233, 98, 217, 169, 212, 96, 215]
simhash(near_dup)  = 14375515891255408991, bands = [95, 249, 66, 209, 137,  23,128, 199]
shared bands: 0        Hamming distance: 13/64 bits
```

`hashing.py`'s own docstring claims 8×8 was chosen because it "catches" exactly this class of near-duplicate ("measured against this module's own `simhash()` on realistic single-word-edit near-duplicates... 8x8 catches them"), citing `test_hashing.py`. That claim doesn't hold for this specific (also real, also realistic) example: 13/64 bits of difference is enough to miss all 8 bands simultaneously. **Not fixed here** — retuning LSH band/bit counts is a recall-vs-false-positive-rate tradeoff that needs a real near-dup corpus to evaluate properly, not a one-line change; flagged per the module's own docstring ("revisit against real corpus near-dup rates if recall proves insufficient at scale") — this session is exactly that revisit, and recall is confirmed insufficient for at least this realistic case.

## F4 status: confirmed STILL falls back, and the fallback code path is currently unreachable

Re-checked `query_router.py` directly: `route_query()` still calls `chunk_store.get_by_legal_metadata()` (lines 87, 95) unconditionally — never uses the injected `ComplianceRepository`, exactly as F4 described. Additionally, grepping `api/` for callers of `route_query()`/`query_router` found **none** — `route_query()` has no caller anywhere in the live application today. So F4's fallback isn't just "still there," the entire code path it lives in is currently dead code, not on any real request path. (The fast, indexed `PostgresComplianceRepository.find_matching()` — see measurements below — is fully working and would need to be wired into wherever compliance-intent queries actually get handled today, which this session did not locate.)

## Real measurements (live Postgres, `inteliai-rag`, throwaway `organization_id`, cleaned up after)

3,000 synthetic chunks/postings seeded through the real repository write path (not bulk SQL), 1/50 with legal metadata (`GDPR`/`EU`, ~60 chunks sharing one clause identity):

| Operation | Real measurement | Notes |
|---|---|---|
| Chunk+BM25 write throughput (repository `record_many`, batches of 500) | 116.2ms/chunk this run; 40.9ms/chunk in an earlier 20,000-chunk run | Batch-size/network-variance sensitive; both are the real `executemany` path, not bulk `COPY` |
| `filter_new_hashes()` (exact-dup dedup, indexed) | 712.4ms | |
| `find_near_duplicate_candidates()` (LSH band lookup) | 697.0ms | Found 92 same-band candidates (see recall gap above for a case it misses) |
| `PostgresComplianceRepository.find_matching()` (indexed, real repo call) | 705.9ms | 60 rows matched, correct |
| Same filter, indexes forced off (`enable_indexscan/bitmapscan=off`) | 224.3ms | **Faster than the "indexed" call above** — see below |
| `PostgresBM25Repository.record_many()`, single new chunk | 1213.2ms | |
| `PostgresBM25Repository.search()` | 1021.1ms | |
| `PostgresDocumentRepository.get_hash_for_path()` | 831.9ms | |

**Every one of these single-round-trip calls clusters at ~700-1200ms regardless of query complexity or plan** — including the supposedly-slower forced-seq-scan comparison coming in *faster* than the indexed version. This is strong evidence that **network round-trip latency from this environment to the Supabase session pooler dominates every number above**, not Postgres query-execution cost (which the original report's Supabase-MCP-based `EXPLAIN ANALYZE` correctly measured at sub-millisecond, in-database). These are real, honestly-measured numbers for *this session's specific environment/network path* — they are not representative of latency from a co-located production deployment (e.g., a Render service in the same AWS region as the Supabase project), and should not be read as "Postgres queries take 700ms."

**WorkerPool concurrency scaling — real, and clean.** 40 real jobs through `PostgresJobRepository` + `WorkerPool`, dummy 50ms-sleep processor (isolating queue/claim overhead from any NVIDIA/Pinecone cost):

| Concurrency | Completed (of 40, 30s budget) | Wall time | Throughput |
|---|---|---|---|
| 1 worker | 21 | 30.0s (deadline hit) | 0.70 jobs/s |
| 4 workers | 40 | 15.2s | 2.63 jobs/s |

A **3.75x throughput increase for 4x concurrency** — near-linear, unlike F1's global-lock finding. Confirms the `WorkerPool`/`FOR UPDATE SKIP LOCKED` claim mechanism does what its docstring promises: real concurrent workers, no double-claims (verified via `ingestion_jobs` status counts matching exactly: every enqueued job ends up `queued` or `ready`, none lost or duplicated, across both concurrency levels in the same run).

## Cleanup

All synthetic data (orgs, documents, chunks, postings, jobs) created during this session's testing and validation was deleted from the live `inteliai-rag` project, including residue from crashed early attempts before the bugs above were found. Verified: `0` rows remaining under any `test-org`/`validation-throwaway` organization, `0` leftover `ingestion_jobs` in any status, `0` leftover `documents`, post-cleanup.
