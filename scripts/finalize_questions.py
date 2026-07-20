#!/usr/bin/env python3
"""Swap filename placeholders in eval/questions_compliance.yaml for the real
document_id hashes produced by ingestion (eval/corpus_document_ids.json).
Questions citing documents that failed to ingest are dropped, with a report.

Run: uv run python -m scripts.finalize_questions
"""
import json
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
_QUESTIONS = _REPO_ROOT / "eval" / "questions_compliance.yaml"
_DOC_IDS = _REPO_ROOT / "eval" / "corpus_document_ids.json"
_OUT = _REPO_ROOT / "eval" / "questions_compliance_final.yaml"


def main() -> None:
    mapping = {fn: info["document_id"] for fn, info in json.loads(_DOC_IDS.read_text()).items()}
    data = yaml.safe_load(_QUESTIONS.read_text())

    kept, dropped = [], []
    for q in data["questions"]:
        filenames = q["expected"]["citation_doc_ids"]
        missing = [f for f in filenames if f not in mapping]
        if missing:
            dropped.append((q["id"], missing))
            continue
        q["expected"]["citation_doc_ids"] = [mapping[f] for f in filenames]
        kept.append(q)

    data["questions"] = kept
    _OUT.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000))
    print(f"kept {len(kept)}, dropped {len(dropped)}")
    for qid, missing in dropped:
        print(f"  dropped {qid}: missing {missing}")
    if len(kept) < 75:
        print("WARNING: below the 75-question floor", file=sys.stderr)


if __name__ == "__main__":
    main()
