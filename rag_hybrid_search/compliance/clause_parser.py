import re

from rag_hybrid_search.compliance.regulation_models import (
    ClauseParseResult,
    ClauseSpan,
    LegalMetadata,
)

_ARTICLE_RE = re.compile(r"^(?:Article|ARTICLE|Art\.)\s+(\d+[A-Za-z]?)\s*$", re.MULTILINE)
_SECTION_RE = re.compile(r"^(?:Section|SECTION|Sec\.)\s+([\d.]+)\s*$", re.MULTILINE)
_CHAPTER_RE = re.compile(r"^(?:Chapter|CHAPTER)\s+([IVXLCDM]+|\d+)\s*$", re.MULTILINE)
_ANNEX_RE = re.compile(r"^(?:Annex|ANNEX|Appendix|APPENDIX)\s+([A-Za-z0-9]+)\s*$", re.MULTILINE)
_CLAUSE_RE = re.compile(r"^\(?(\d+(?:\.\d+)*(?:\([a-z]\))?)\)?[\s.:]", re.MULTILINE)
_LETTER_CLAUSE_RE = re.compile(r"^\(([a-z])\)[\s.:]", re.MULTILINE)

_HEADING_PATTERNS = [
    ("article", _ARTICLE_RE),
    ("section", _SECTION_RE),
    ("chapter", _CHAPTER_RE),
    ("annex", _ANNEX_RE),
]


def _tag_sub_clauses(
    block: str,
    document_id: str,
    document_title: str,
    current_article: str | None,
    current_section: str | None,
) -> list[ClauseSpan]:
    """Split a top-level block into one span per *numbered* clause, keeping
    each numbered clause's lettered sub-items (a)/(b)/(c) inline with it.

    Splitting out every lettered sub-clause into its own span
    over-fragments the text: a clause like GDPR Art 83(5) -- "Infringements
    ... shall be subject to administrative fines up to 20 000 000 EUR ...:
    (a) the basic principles ...; (b) ..." -- would put the penalty amount
    in one chunk and each violation it applies to in separate sibling
    chunks, so a query matching "(a) basic principles" retrieves the item
    without the fine. Grouping keeps the number and its list together in one
    retrievable unit. A numbered clause with no lettered sub-items is
    unaffected; a block with no numbered markers at all stays whole.
    """
    numbered = [(sc.start(), sc.group(1)) for sc in _CLAUSE_RE.finditer(block)]
    if not numbered:
        return [
            ClauseSpan(
                text=block,
                metadata=LegalMetadata(
                    document_id=document_id,
                    document_title=document_title,
                    article=current_article,
                    section=current_section,
                ),
            )
        ]

    spans: list[ClauseSpan] = []
    boundaries = [start for start, _ in numbered] + [len(block)]
    # Text before the first numbered clause (block heading / preamble) is
    # prepended to the first clause so nothing is dropped.
    lead = block[: boundaries[0]].strip()
    for j, (start, number) in enumerate(numbered):
        sub_text = block[start : boundaries[j + 1]].strip()
        if j == 0 and lead:
            sub_text = f"{lead}\n{sub_text}"
        full_clause = f"{current_article}.{number}" if current_article else number
        spans.append(
            ClauseSpan(
                text=sub_text,
                metadata=LegalMetadata(
                    document_id=document_id,
                    document_title=document_title,
                    article=current_article,
                    section=current_section,
                    clause=full_clause,
                ),
            )
        )
    return spans


def parse_clauses(text: str, document_id: str, document_title: str) -> ClauseParseResult:
    """Split text into clause spans using regex heading detection.

    Splits at top-level Article/Section/Chapter/Annex headings, then
    tags nested numbered sub-clauses (e.g. "1.", "5.2(a)") within each
    top-level span. Falls back to a single whole-document clause with
    confidence 0.0 if no heading is recognized anywhere.
    """
    if not text.strip():
        return ClauseParseResult(clauses=[], confidence=0.0)

    matches: list[tuple[int, str, str]] = []
    for label, pattern in _HEADING_PATTERNS:
        for m in pattern.finditer(text):
            matches.append((m.start(), label, m.group(1)))
    matches.sort(key=lambda m: m[0])

    if not matches:
        span = ClauseSpan(
            text=text.strip(),
            metadata=LegalMetadata(document_id=document_id, document_title=document_title),
        )
        return ClauseParseResult(clauses=[span], confidence=0.0, fallback_used=True)

    boundaries = [m[0] for m in matches] + [len(text)]
    clauses: list[ClauseSpan] = []
    current_article: str | None = None
    current_section: str | None = None

    for i, (start, label, value) in enumerate(matches):
        end = boundaries[i + 1]
        block = text[start:end].strip()
        if label == "article":
            current_article = value
            current_section = None
        elif label == "section":
            current_section = value
            current_article = None

        clauses.extend(
            _tag_sub_clauses(block, document_id, document_title, current_article, current_section)
        )

    coverage = sum(len(c.text) for c in clauses) / max(len(text), 1)
    confidence = min(1.0, 0.5 + 0.5 * min(coverage, 1.0)) if clauses else 0.0

    return ClauseParseResult(clauses=clauses, confidence=confidence)
