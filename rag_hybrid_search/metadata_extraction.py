"""AI-assisted metadata extraction for the upload flow.

Provider-agnostic: takes any ``GenerationProvider`` (Gemini, NVIDIA, ...) and
prompts it to infer document metadata as JSON. Never raises -- a malformed
response, an empty document, or a provider error all degrade to an
all-null result so extraction failures never block an upload; the user
still gets the manual metadata form (see api/routes.py extract_metadata).
"""

import json
import logging

from pydantic import BaseModel

from rag_hybrid_search.providers.base import GenerationProvider

logger = logging.getLogger(__name__)

_FIELDS = (
    "document_type",
    "authority",
    "regulation",
    "jurisdiction",
    "risk_category",
    "version",
    "effective_date",
)

# Cap the text sent to the LLM -- metadata (title, issuing body, dates) lives
# in the first few pages of virtually every regulatory document, and a hard
# cap keeps extraction latency/cost independent of document length.
_MAX_CHARS = 12_000

_PROMPT_TEMPLATE = """You are extracting document metadata for a compliance document management system.

Read the document text below and infer these fields:
- document_type: one of "regulation", "policy", "contract", "standard", "guideline", or "general"
- authority: the issuing organization or authority (e.g. "Reserve Bank of India")
- regulation: the regulation or policy name (e.g. "Master Circular on KYC")
- jurisdiction: the country or region the document applies to (e.g. "India")
- risk_category: one of "low", "medium", "high", "critical", based on the document's compliance risk
- version: the document's version or edition label, if stated
- effective_date: the date the document takes/took effect, as YYYY-MM-DD

Rules:
- If a field cannot be confidently determined from the text, set it to null. Never guess or fabricate a value.
- Respond with JSON only, no other text, matching exactly this shape:
{{"document_type": null, "authority": null, "regulation": null, "jurisdiction": null, "risk_category": null, "version": null, "effective_date": null}}

Document text:
---
{text}
---"""


class ExtractedMetadata(BaseModel):
    document_type: str | None = None
    authority: str | None = None
    regulation: str | None = None
    jurisdiction: str | None = None
    risk_category: str | None = None
    version: str | None = None
    effective_date: str | None = None

    @property
    def fields_found(self) -> int:
        return sum(1 for f in _FIELDS if getattr(self, f) is not None)


def build_extraction_prompt(text: str) -> str:
    return _PROMPT_TEMPLATE.format(text=text[:_MAX_CHARS])


def extract_metadata(provider: GenerationProvider, text: str) -> ExtractedMetadata:
    """Ask ``provider`` to infer metadata from ``text``. Always returns a result --
    extraction failures (bad JSON, provider error, empty document) yield an
    all-null ``ExtractedMetadata`` rather than raising."""
    if not text.strip():
        return ExtractedMetadata()
    try:
        raw = provider.generate(build_extraction_prompt(text))
        payload = json.loads(_strip_code_fence(raw))
        return ExtractedMetadata(**{k: payload.get(k) for k in _FIELDS if isinstance(payload, dict)})
    except Exception:  # noqa: BLE001 - never let extraction failures block an upload
        logger.exception("metadata extraction failed")
        return ExtractedMetadata()


def _strip_code_fence(raw: str) -> str:
    """LLMs commonly wrap JSON in ```json ... ``` despite being told not to -- strip it."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.removesuffix("```").strip()
        if text.endswith("```"):
            text = text[: -len("```")].strip()
    return text
