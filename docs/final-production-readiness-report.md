# InteliAI — Final Production Readiness Report

This report certifies InteliAI's production readiness based on real, unmocked execution against live infrastructure: a live NVIDIA API key, a live Pinecone index (`rag-hybrid-search-dense`), and the live `inteliai-rag` Supabase/Postgres project. It consolidates and supersedes `docs/production-readiness-report.md` and `docs/validation-report.md` (including its addendum) — those remain as historical record; this document is the final word.

No refactoring, redesign, or new abstractions were introduced while producing this report. Two prior sessions did fix 4 crash bugs blocking the Postgres-backed path (documented below, under "Bugs Fixed") — those are carried forward as context, not repeated here.

---

## 1. Final Architecture Diagram

```
                              ┌─────────────┐
                              │   Client    │
                              └──────┬──────┘
                                     │
                              ┌──────▼──────┐
                              │  FastAPI    │  (api/main.py, api/routes.py)
                              │  + auth     │  (api/auth.py — open by default,
                              │  + rate-lim │   no roles, see Security Assessment)
                              └──────┬──────┘
                     ┌───────────────┼────────────────┐
                     ▼                                ▼
            POST /upload/async                   POST /answer
                     │                                │
                     ▼                                ▼
         ┌───────────────────────┐          ┌──────────────────┐
         │  PostgresJobRepository │          │  query_router.py  │
         │  (ingestion_jobs,      │          │  classify_query() │
         │   FOR UPDATE SKIP      │          │  → route_query()   │
         │   LOCKED)               │          └─────────┬─────────┘
         └───────────┬────────────┘                     │
                     │                         structured/metadata/mixed?
              ┌──────▼──────┐                           │
              │ WorkerPool   │                  ┌────────▼─────────┐
              │ (N threads,  │                  │ chunk_store       │
              │  claim/heart-│                  │ .get_by_legal_    │
              │  beat/retry/ │                  │  metadata()        │
              │  reap)       │                  │ (Pinecone scan —   │
              └──────┬───────┘                  │  NOT the indexed   │
                     │                          │  ComplianceRepo —  │
                     ▼                          │  see F4, still     │
          IngestionPipeline.ingest()            │  live)             │
                     │                          └────────┬───────────┘
      ┌──────────────┼──────────────┐                    │
      ▼              ▼              ▼                     ▼
   Chunking    Exact-dup dedup  Near-dup dedup      HybridRetriever
 (Recursive-   (PostgresChunk   (SimHash LSH bands, │ (dense + sparse
  Chunker)      Repository.      PostgresChunk       │  + RRF + rerank)
               filter_new_       Repository.                 │
               hashes(), O(1)    find_near_dup_               ▼
               indexed lookup)   candidates())          RagPipeline
      │              │              │                   .answer()
      └──────┬───────┴──────┬───────┘                        │
             ▼              ▼                          Generation
      NVIDIA Embeddings  (global lock,               (NVIDIA, structured
      (rate-limited,      F1 — throughput             JSON output —
       real: 1024-dim)    ceiling, confirmed)         confirmed fragile,
             │                                        see Bugs Found)
             ▼
      Pinecone (vectors + metadata)
             │
      ┌──────┴───────┐
      ▼              ▼
  Incremental    ComplianceRepository
  BM25           (PostgresComplianceRepository
  (Postgres      .find_matching() — indexed,
  postings,      fast, correct — but NOT on
  O(new          the /answer request path,
  chunks))       see F4)
             │
             ▼
      AuditLog (Postgres/local — every
      ingest + query recorded)
             │
             ▼
        Searchable
```

## 2. Complete Request Flow (query path, as actually executed)

```
Client
  → POST /answer  (api/routes.py:answer)
  → get_identity() (api/auth.py — open unless RAG_API_KEYS set; no roles)
  → RagPipeline.answer()
      → query_router.classify_query()  (real, called)
      → query_router.route_query()     (real, called — confirmed live, not dead)
          → intent in {structured, metadata, mixed}?
              → chunk_store.get_by_legal_metadata()  (Pinecone scan path — F4, unchanged)
          → intent == semantic/hybrid?
              → HybridRetriever.retrieve()
                  → DenseRetriever  (NVIDIA query-embed + Pinecone query + per-hit fetch loop, F2)
                  → SparseRetriever (PostgresBM25Repository.search() when Postgres configured)
                  → RRF fusion
                  → rerank (passthrough/cross_encoder/nvidia, per RAG_RERANK_BACKEND)
      → GenerationProvider.generate()  (NVIDIA — structured JSON output; confirmed fragile, see Bugs Found)
  → _record_audit()  (AuditLog — confirmed written, real event observed)
  → response to client
```

## 3. Complete Ingestion Flow (as actually executed and confirmed this session)

```
Client → POST /upload/async
  → file bytes written to container.uploads_dir (disk, before job persisted)
  → PostgresJobRepository.enqueue()  (idempotency-keyed)
  → 202 Accepted, job_id returned
  ⋯ (async, off the request thread) ⋯
  → WorkerPool worker thread claims job (FOR UPDATE SKIP LOCKED — confirmed real, 4 workers, no double-claim)
  → process_ingestion_payload()
      → IngestionPipeline.ingest()
          → Loader (markdown/html/text/pdf)
          → RecursiveChunker
          → PostgresDocumentRepository.get_hash_for_path()  (unchanged-document short-circuit)
          → PostgresChunkRepository.filter_new_hashes()      (exact-dup, O(1) indexed — confirmed real)
          → PostgresChunkRepository.find_near_duplicate_candidates()  (LSH bands — confirmed real, confirmed recall gap on some inputs)
          → chunk_store.all_with_embeddings()  (full-corpus Pinecone scan for near-dup cosine check — real cost, scales with corpus size, unrelated to whether Postgres is configured)
          → NvidiaProvider.embed()             (real, confirmed 1024-dim vectors)
          → chunk_store.put_many() + vector_store.upsert_many()  (N+1 Pinecone calls — F3; index_combined() exists but is dead/broken, not used)
          → PostgresBM25Repository.record_many()  (confirmed real, incremental — bug-fixed this session's prior pass)
          → chunks table's legal_* columns written directly by PostgresChunkRepository (confirmed real)
          → AuditLog entry recorded
  → job status: queued → processing → ready (confirmed observed end-to-end)
Client polls GET /jobs/{job_id} → ready
Client → POST /answer → finds the new chunk via BM25 and/or dense retrieval (confirmed: PostgresComplianceRepository.find_matching() and PostgresBM25Repository.search() both located the real ingested chunk directly; /answer produced a grounded response citing it)
```

## 4. Components

| Component | Role | Status |
|---|---|---|
| FastAPI app (`api/main.py`, `api/routes.py`) | HTTP surface, lifespan-managed singletons | Real, working |
| `WorkerPool` (`api/jobs.py`) | Multi-threaded claim-based job processor | **Confirmed real**: 4 threads started, real job claimed/processed/completed this session |
| `PostgresJobRepository` | Persistent job queue, `FOR UPDATE SKIP LOCKED` | **Confirmed real** and race-free (verified in a prior session's 40-job/4-worker test: exact accounting, no double-claim) |
| `PostgresDocumentRepository` / `PostgresChunkRepository` | Indexed dedup (exact + near-dup LSH) | **Confirmed real**; 3 crash bugs found+fixed in a prior session (`executemany`, simhash bigint overflow, `legal_is_current` NOT NULL) |
| `PostgresBM25Repository` | Incremental BM25 postings, no full rebuild | **Confirmed real** end-to-end this session (search located the freshly-ingested chunk) |
| `PostgresComplianceRepository` | Indexed legal-metadata lookup | **Confirmed real** and correct this session — but not on the live `/answer` path (see F4) |
| `PineconeVectorStore` / `PineconeChunkStore` | Vector + chunk storage | **Confirmed real**: fetched the newly-ingested vector directly from Pinecone |
| `AuditLog` | Compliance audit trail | **Confirmed real**: a real `/answer` call was recorded with full detail |
| `query_router.py` | Compliance-intent query classification/routing | **Confirmed real and live** (called from `rag_pipeline.py:428`) — correction from a prior session's report, which incorrectly called this dead code |
| `IndexManager.index_combined()` / `supports_combined_write()` | Combined-write fast path | **Confirmed dead and broken** — zero callers; the gate function itself crashes if ever called (`AttributeError`, pre-existing, unfixed by design of this audit's scope) |
| Scanning repositories (`storage/repositories/scanning/*`) | No-Postgres fallback | **Live, intentional, not dead** — selected by `api/dependencies.py` whenever `RAG_SUPABASE_DB_URL` is unset; this is a supported deployment mode, not legacy cruft (see Phase 2) |

## 5. Technologies Used

FastAPI, Pydantic/pydantic-settings, psycopg3 + psycopg_pool (Postgres), Supabase (managed Postgres), Pinecone (managed vector DB), NVIDIA NIM API (embeddings + generation), rank_bm25-style BM25 reimplemented in Postgres SQL, SimHash/LSH (pure Python), sentence-transformers (optional cross-encoder rerank), React (frontend, not audited here).

## 6. Benchmarks / Real Measurements (Phase 5)

All numbers below are real measurements from live infrastructure (this session and the immediately preceding one — no numbers here are estimated).

| Area | Real measurement | Bottleneck |
|---|---|---|
| NVIDIA embedding, single call | 835ms baseline; throughput pinned ~1.1-1.2 req/s at any concurrency (1/2/4/8) | **External API + a global lock** (`_nvidia_throttle`) — confirmed the lock, not NVIDIA's real rate limit (no 429s seen) |
| NVIDIA generation (this session, real `/answer` call) | **59.4 seconds** for one question (70B default model) | **External API** — single largest end-to-end latency contributor observed this session |
| Pinecone per-call latency | ~300-900ms/call (query, fetch, upsert, update all in this range) | **External API / network**, not Pinecone-side compute |
| Postgres round-trip (this session's network path) | ~700-1200ms per single-round-trip repository call (dedup lookup, compliance lookup, BM25 search, document lookup) — even a forced sequential scan came back *faster* than the "indexed" query | **Network** (session→Supabase pooler RTT), confirmed by the fact indexed vs. seq-scan made no measurable difference at this corpus size; real in-database query cost (measured via `EXPLAIN ANALYZE`) is sub-millisecond |
| `WorkerPool` concurrency scaling | 1 worker: 0.70 jobs/s; 4 workers: 2.63 jobs/s (3.75x for 4x) | **Not algorithmic or lock-bound** — near-linear, confirms `FOR UPDATE SKIP LOCKED` claiming scales cleanly; the residual gap vs. perfectly-linear 4x is per-job Postgres round-trip latency (network), not contention |
| Ingestion, per-document (real, scanning-fallback mode, from a prior session) | 3.1s-56s per document, growing with corpus size then unexplainedly dropping | **Algorithmic**: O(corpus) full-scan in near-dup dedup (`all_with_embeddings()`) and BM25 rebuild — this scan cost is present **regardless of whether Postgres is configured**, since it lives in `chunk_store.all_with_embeddings()`, a Pinecone-side operation, not a repository call |
| Compliance query, cold Pinecone scan vs. indexed Postgres | 14.0s (58 vectors) vs. 0.336ms (20,000 rows, real `EXPLAIN ANALYZE`) | **Algorithmic + external API**: the routing choice (not using the indexed repository) is the root cause; Pinecone per-call cost multiplies it |
| Retrieval, concurrent queries (1/5/10) | 0.163 → 0.651 → 0.881 req/s (5.4x for 10x concurrency) | **External API (Pinecone N+1 fetch, F2)** dominant; NVIDIA lock (F1) additive |

## 7. Bugs Found (this session + carried forward)

1. **Structured generation output parse failure, real, live, this session.** A real `/answer` call against the real NVIDIA generation model returned output that failed structured-JSON parsing (`"failed to parse structured generation output: Expecting value: line 1 column 1 (char 0)"`). The pipeline degraded gracefully — an answer was still produced via an "inline drift" fallback, citing a document inline in prose — but `citations`/`structured_citations` were empty despite a citation appearing in the answer text, and the audit log recorded this call as `status: "failure"`. **Not fixed this session** (a generation-provider/prompt-robustness issue, not a wiring or config bug — needs its own investigation into why the model's structured-output call failed for this specific prompt).
2. **`route_query()` misclassified as dead code in the prior session's addendum.** It is not — it's called from `rag_pipeline.py:428`, on the live `/answer` path. Corrected in this report (see F4, section 4).
3. `conn.executemany()`, simhash `bigint` overflow, `legal_is_current` NOT NULL violation — **carried forward from a prior session**, already fixed (see `docs/validation-report.md` addendum for full detail). Not re-litigated here.
4. **Near-duplicate LSH recall gap** — carried forward from a prior session, confirmed real and unfixed: a realistic single-word-edit near-duplicate pair shares zero LSH bands at the current 8×8 parameterization.
5. **`IndexManager.supports_combined_write()` crashes on every real call** (`AttributeError` — checks a `_index` attribute neither real store class has) — carried forward, confirmed still present, still unfixed (zero real callers, so not a live-traffic bug, but blocks ever wiring in the combined-write fast path without fixing this first).
6. **Audit log has no enforced access control**, despite its own docstring claiming "Admin-only (compliance surface)" — confirmed this session: `api/auth.py` has zero role/permission logic anywhere. Any caller who can reach the API (which is *any* caller, when `RAG_API_KEYS` is unset — the default) can read the full compliance audit trail, including regulation metadata and query text.

## 8. Bugs Fixed

Fixed in the immediately preceding session (not repeated here in full — see `docs/validation-report.md`'s addendum for complete detail and diffs):
1. `conn.executemany()` doesn't exist on psycopg3's `Connection` — 4 call sites, both `PostgresChunkRepository` and `PostgresBM25Repository`, crashed on every real write.
2. `simhash()`'s unsigned 64-bit value overflowed the signed `bigint` `chunks.simhash` column for ~50% of real inputs.
3. `legal_is_current` (`NOT NULL DEFAULT true`) was defaulted to `None` for every non-legal chunk — crashed ingestion of every ordinary (non-compliance) document.
4. Two test-fixture bugs in the (previously never-run) Postgres integration test suite, unrelated to production code.

**Nothing was fixed in this session** — Phase 1-6 were validation and audit only, per the explicit "no unnecessary refactoring" instruction; bug #1 (structured-generation parsing) and #6 (audit access control) above are newly found, not fixed.

## 9. Remaining Technical Debt

- **F4 (compliance query routing) is still live and unfixed**: `route_query()` calls `chunk_store.get_by_legal_metadata()` (a Pinecone full-scan) instead of the already-built, already-injected, already-fast `ComplianceRepository`. This is the single highest-ROI fix identified across both sessions and remains undone.
- **`index_combined()`/`supports_combined_write()`**: dead, broken, unused. Either fix-and-wire or delete; leaving it as-is means the F3 finding's fix is unreachable without first fixing this gate.
- **O(corpus) Pinecone scan in near-dup dedup** (`chunk_store.all_with_embeddings()`): present in ingestion regardless of Postgres configuration, since it's a Pinecone-side operation. Real, measured, dominant ingestion cost at scale.
- **Global NVIDIA lock (F1)**: confirmed severe, unsized fix (needs a real rate-limit-discovery test before choosing a concurrency bound).
- **N+1 Pinecone fetch (F2)**: confirmed, `get_many()`-style batching exists elsewhere in the codebase and isn't reused here.
- **Structured-generation parsing fragility** (new, this session): the generation provider's structured-output contract is not robust against at least one real prompt/response pairing observed live.

## 10. Remaining Risks

- **Audit trail has no real access control** — a genuine compliance/security risk for an app whose stated purpose is compliance query classification (see Bugs Found #6).
- **Near-dup LSH recall gap** — real duplicate content can silently double-ingest without triggering the near-dup path (exact-hash dedup still catches byte-identical content; near-dup is the gap).
- **Single fixed tenant** (`default_organization_id` hardcoded) — no real multi-tenancy; every real customer would share one organization row today.
- **No IPv4 direct-connection path confirmed** — this session's environment could only reach Postgres via the session pooler (IPv6-only direct-connection host, no outbound IPv6 route here). Any production deployment must confirm its own network path can reach whichever Postgres endpoint it's configured against.

## 11. Known Limitations

- No NVIDIA rerank backend validation against a live call exists in either session (flagged, unverified, per the provider's own module docstring).
- The O(corpus) Pinecone scan issue in near-dup dedup is not eliminated by having Postgres configured — this was a real misunderstanding surfaced and corrected across the two sessions' reports; Postgres eliminates the *exact-dup* and *BM25-rebuild* full scans, but the near-dup step's `all_with_embeddings()` call is a chunk_store (Pinecone) method regardless.
- This report's "real measurements" reflect *this session's specific network path* (a workstation to Supabase's US-East-1 pooler, and to Pinecone/NVIDIA's public endpoints) — not necessarily representative of a co-located production deployment (e.g., a Render service in the same AWS region).

## 12. Scalability Assessment

- **WorkerPool/Postgres path scales cleanly and near-linearly** with worker count — the strongest positive finding in this report, confirmed by direct measurement (3.75x throughput for 4x workers, no double-claims, clean accounting).
- **Ingestion at real load is dominated by external API latency and an O(corpus) scan**, not CPU/memory. This will get *worse*, not better, as corpus size grows, until F4 is fixed and the near-dup scan cost is addressed.
- **Compliance query routing (F4) is the most severe scalability risk found in either session**: its cost is bounded by Pinecone scan time, not the (already-fast, already-built) indexed alternative, and this is on the live query path today.
- **NVIDIA global lock (F1)** caps embedding/generation throughput regardless of how many workers or requests run concurrently — a hard ceiling until resized.

## 13. Security Assessment

- **No enforced authorization model.** `RAG_API_KEYS` unset (the default) means every endpoint, including the audit log, is open to any caller who can reach the API. When keys *are* configured, there is still no role distinction — any valid key gets full access (confirmed: zero role logic in `api/auth.py`).
- **Debug endpoint correctly gated**: `/debug/retrieval` returns 404 unless `RAG_DEBUG_TOKEN` is explicitly set, and requires a matching header — this one is done right.
- **Credentials handled correctly in this validation process** (not a code finding, a process note): the Postgres password, NVIDIA key, and Pinecone key used in this session's validation were never written to a tracked file, only passed inline to one-shot processes.
- **No secrets scanning / rotation policy observed** in the repository (out of scope to audit further here — CLAUDE.md-level guidance, not code).

## 14. Production Readiness Score: **5/10**

**Rationale**: the underlying architecture is sound and, where it's actually wired correctly, performs well and scales cleanly (WorkerPool, Postgres repositories, dedup, BM25 — all confirmed real and working end-to-end this session). But the score is held down by: (a) a real, unresolved, high-severity routing bug on the live query path (F4) with a fast fix already built and sitting unused, (b) zero enforced access control on a compliance-sensitive audit trail, (c) a real generation-output-parsing failure observed live in this session's own validation run, and (d) an unsized external-API concurrency bottleneck (F1) that caps throughput today. None of these are exotic edge cases — F4 and the audit gap are both on real, common request paths.

## 15. Release Recommendation

## ⚠ Ready for Beta

**Evidence for this call:**
- **Not "Not Ready"**: the core ingestion→storage→retrieval→answer loop is confirmed working end-to-end against real infrastructure in this session, with correct data landing in Postgres and Pinecone and being correctly retrieved back out via both BM25 and the compliance repository.
- **Not "Ready for Production"**: F4 (a known, understood, already-has-a-fix routing bug that makes the primary compliance-query use case pay a 14-second-plus Pinecone-scan tax instead of a sub-millisecond indexed lookup) is unresolved and live; the audit log's access-control gap is a real compliance risk for a compliance-focused product; and this session's own validation run surfaced a live generation-parsing failure, meaning the answer-quality path is not yet reliably robust.
- **"Beta" fits**: real users could exercise the real system today and get real, mostly-correct answers (as demonstrated), but should not be given SLAs around compliance-query latency, audit-log confidentiality, or 100% structured-citation reliability until F4, the auth gap, and the generation-parsing issue are addressed.
