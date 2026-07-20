import pdfplumber
from pypdf import PdfReader

from rag_hybrid_search.ingestion.loaders.base import Loader
from rag_hybrid_search.models import Document


def _table_to_text(table: list[list[str | None]]) -> str:
    """Render an extracted table as pipe-delimited rows so columns stay
    distinguishable instead of being smashed into one run-on line."""
    rows = [" | ".join(cell or "" for cell in row) for row in table]
    return "\n".join(rows)


def _detect_gutter_x(page) -> float | None:
    """Return the x of a vertical gutter separating two text columns, or
    None when the page isn't cleanly two-column.

    Two-column legal/Federal-Register PDFs (HIPAA and most CFR parts) are
    otherwise read across BOTH columns line-by-line, interleaving unrelated
    passages into garbled text -- e.g. HIPAA's "60 calendar days" clause got
    spliced with an adjacent column's list, making it unretrievable. Detect
    a vertical band in the middle of the page that almost no word crosses,
    with substantial text on both sides, and treat that as the column split.

    Conservative by design: any ambiguity returns None so genuinely
    single-column pages fall through to the existing extraction unchanged.
    """
    try:
        words = page.extract_words(x_tolerance=1)
    except Exception:
        return None
    if len(words) < 20:
        return None

    width = page.width or 0
    if width <= 0:
        return None
    intervals = [(float(w["x0"]), float(w["x1"])) for w in words]
    n = len(intervals)

    best_x = None
    best_cross = None
    lo, hi = width * 0.35, width * 0.65
    steps = 25
    for i in range(steps + 1):
        x = lo + (hi - lo) * i / steps
        crossing = sum(1 for a, b in intervals if a < x < b)
        left = sum(1 for _, b in intervals if b <= x)
        right = sum(1 for a, _ in intervals if a >= x)
        # need a real column of text on each side, not a stray margin note
        if left < n * 0.25 or right < n * 0.25:
            continue
        if best_cross is None or crossing < best_cross:
            best_cross, best_x = crossing, x

    if best_x is None:
        return None
    # a true gutter has almost nothing spanning it
    if best_cross <= max(2, int(n * 0.02)):
        return best_x
    return None


def _extract_page_text(page) -> str:
    """Extract a page's prose in human reading order, column-aware.

    Single-column (gutter not detected): the existing full-page extraction.
    Two-column: extract the left column top-to-bottom, then the right,
    so each column's sentences stay intact instead of being interleaved.
    """
    gutter = _detect_gutter_x(page)
    if gutter is None:
        return page.extract_text(x_tolerance=1) or ""
    left = page.crop((0, 0, gutter, page.height)).extract_text(x_tolerance=1) or ""
    right = page.crop((gutter, 0, page.width, page.height)).extract_text(x_tolerance=1) or ""
    return "\n".join(part for part in (left.strip(), right.strip()) if part)


def _extract_with_pdfplumber(path: str) -> str | None:
    """Try pdfplumber (table-aware). Returns None if it can't parse the file at all.

    page.flush_cache() after each page: pdfplumber's Page objects cache
    decoded layout/image data (chars, lines, rects, images) and don't release
    it while iterating pdf.pages, so without this a real multi-page PDF holds
    every page's decoded data live simultaneously -- confirmed via Render RSS
    instrumentation to cost ~250MB on a real document, the dominant memory
    cost in the whole ingest path (embedding response parsing, by contrast,
    cost ~8MB for the same document). flush_cache() is pdfplumber's own
    documented fix for this exact memory-growth pattern.
    """
    with pdfplumber.open(path) as pdf:
        if not pdf.pages:
            return None
        pages_text = []
        for page in pdf.pages:
            text = _extract_page_text(page)
            tables = page.extract_tables(table_settings={"text_x_tolerance": 1})
            table_blocks = [_table_to_text(table) for table in tables if table]
            pages_text.append("\n\n".join([text, *table_blocks]).strip())
            page.flush_cache()
        return "\n".join(pages_text)


def _extract_with_pypdf(path: str) -> str:
    """Plain text fallback, no table awareness."""
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


class PdfLoader(Loader):
    """Extracts text and tables from PDFs.

    Tries pdfplumber first because pypdf's ``extract_text`` reads
    left-to-right with no column awareness: a financial table's columns get
    smashed into one run-on line, making numbers unattributable to their
    row/column headers. pdfplumber's ``extract_tables`` detects table grid
    lines/whitespace and returns actual rows/cells, rendered here as
    pipe-delimited text appended after the page's prose so both survive into
    chunking.

    Falls back to pypdf (no table awareness) if pdfplumber can't parse the
    file at all (via pdfminer.six, it's stricter about malformed/minimal PDF
    structure than pypdf and can silently yield zero pages) -- so a
    non-table document that used to extract fine doesn't regress to empty
    content. This is a text-layer improvement either way, not OCR: pages
    that are scanned images with no text layer still yield no content.
    """

    format = "pdf"

    def load(self, path: str) -> Document:
        content = _extract_with_pdfplumber(path)
        if content is None:
            content = _extract_with_pypdf(path)
        return self._build_document(path, content)
