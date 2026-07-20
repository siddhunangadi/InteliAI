#!/usr/bin/env python3
"""Ingest the compliance PDF corpus (data/compliance_corpus/) into the
eval Pinecone index via the real ingestion pipeline + ClauseChunker, and
write a filename -> document_id map for golden-question authoring.

Concurrent (asyncio + a bounded semaphore around the sync pipeline.ingest,
run in a thread pool -- the pipeline's own code, NVIDIA/Pinecone clients
included, is all synchronous, so this is still threads underneath, but
asyncio gives cleaner concurrency control and lets per-task retry/backoff
happen without blocking siblings).

Resumable: a checkpoint file (eval/ingest_checkpoint.json) is written after
every completed document, not just at the end. A killed or crashed run
picks up where it left off on the next invocation instead of restarting
the whole corpus -- at 10,000-document scale, losing all progress to one
mid-run failure isn't acceptable.

Run: uv run python -m scripts.ingest_compliance_corpus [--workers N]
     Add --restart to ignore any existing checkpoint and start clean.
"""
import argparse
import asyncio
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from api.dependencies import build_container  # noqa: E402
from rag_hybrid_search.compliance.clause_chunker import ClauseChunker  # noqa: E402
from rag_hybrid_search.ingestion.loaders.pdf import PdfLoader  # noqa: E402

_CORPUS_DIR = Path(_REPO_ROOT).parent.parent.parent / "data" / "compliance_corpus"
_MANIFEST_PATH = _CORPUS_DIR / "manifest.json"
_OUT_PATH = Path(_REPO_ROOT) / "eval" / "corpus_document_ids.json"
_CHECKPOINT_PATH = Path(_REPO_ROOT) / "eval" / "ingest_checkpoint.json"


def _load_checkpoint() -> dict:
    if _CHECKPOINT_PATH.exists():
        return json.loads(_CHECKPOINT_PATH.read_text())
    return {}


def _save_checkpoint(checkpoint: dict) -> None:
    _CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file + rename so a crash mid-write never corrupts the
    # checkpoint a resumed run would otherwise trust.
    tmp = _CHECKPOINT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(checkpoint, indent=2))
    tmp.replace(_CHECKPOINT_PATH)


def _ingest_one_sync(doc, container, loader, known_hashes, index, total):
    pdf_path = _CORPUS_DIR / doc["filename"]
    if not pdf_path.exists():
        print(f"[{index}/{total}] SKIP missing file {doc['filename']}", flush=True)
        return None

    chunker = ClauseChunker(
        document_title=doc["regulation_authority"],
        regulation=doc["regulation_authority"],
        document_type="regulation",
    )
    pipeline = container.build_ingestion_pipeline(loader, chunker=chunker)

    try:
        # existing_pairs=[] per-call (not a batch-wide shared list): cross-
        # document dedup across concurrent workers isn't worth locking the
        # whole network-bound ingest() call for -- see module docstring.
        status = pipeline.ingest(
            str(pdf_path), existing_pairs=[],
            rebuild_bm25=False, known_hashes=known_hashes,
        )
        document_id = loader.load(str(pdf_path)).document_id
        print(f"[{index}/{total}] {status.value} {doc['filename']} -> {document_id[:12]}...", flush=True)
        return {
            "document_id": document_id,
            "regulation_authority": doc["regulation_authority"],
            "status": status.value,
        }
    except Exception as e:
        print(f"[{index}/{total}] FAIL {doc['filename']}: {type(e).__name__}: {e}", flush=True)
        return None


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--restart", action="store_true", help="Ignore any existing checkpoint, start clean.")
    args = parser.parse_args()

    manifest = json.loads(_MANIFEST_PATH.read_text())
    documents = manifest["documents"]
    total = len(documents)

    checkpoint = {} if args.restart else _load_checkpoint()
    remaining = [(i, doc) for i, doc in enumerate(documents, 1) if doc["filename"] not in checkpoint]
    if len(remaining) < total:
        print(f"Resuming: {total - len(remaining)}/{total} already done per checkpoint, {len(remaining)} left.", flush=True)

    container = build_container()
    loader = PdfLoader()
    known_hashes: dict[str, str] = {}

    semaphore = asyncio.Semaphore(args.workers)
    loop = asyncio.get_running_loop()
    checkpoint_lock = asyncio.Lock()
    # asyncio's default executor caps at min(32, cpu_count+4) -- explicit
    # sizing so --workers actually controls real concurrency instead of
    # silently capping below whatever's requested.
    executor = ThreadPoolExecutor(max_workers=args.workers)

    async def worker(index: int, doc: dict) -> None:
        async with semaphore:
            result = await loop.run_in_executor(
                executor, _ingest_one_sync, doc, container, loader, known_hashes, index, total,
            )
        if result is not None:
            async with checkpoint_lock:
                checkpoint[doc["filename"]] = result
                _save_checkpoint(checkpoint)

    await asyncio.gather(*(worker(i, doc) for i, doc in remaining))
    executor.shutdown(wait=True)

    print("\nRebuilding BM25 index over the full corpus...", flush=True)
    container.index_manager.rebuild_bm25_index()

    _OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUT_PATH.write_text(json.dumps(checkpoint, indent=2))
    print(f"Wrote {_OUT_PATH} ({len(checkpoint)} documents)")


if __name__ == "__main__":
    asyncio.run(main())
