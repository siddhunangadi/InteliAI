from datetime import date

from rag_hybrid_search.compliance.clause_parser import parse_clauses
from rag_hybrid_search.compliance.regulation_models import DocumentType, LegalMetadata
from rag_hybrid_search.ingestion.chunkers.base import Chunker
from rag_hybrid_search.models import Chunk, Document
from rag_hybrid_search.uuid7 import uuid7


class ClauseChunker(Chunker):
    """Chunks a document along Article/Section/Clause boundaries instead
    of fixed-size windows, attaching LegalMetadata to each resulting Chunk.

    Falls back to a single whole-document chunk (still tagged with
    LegalMetadata, all fields null except document_id/document_title)
    when clause_parser finds no recognizable structure — the document is
    never dropped or left unchunked.

    The document-level fields (regulation/jurisdiction/version_label/
    document_type/effective_date) are optional and default to None so
    existing call sites that only pass document_title are unaffected.
    When provided, they are stamped onto every clause's LegalMetadata
    alongside the clause-level article/section/clause fields already
    populated by clause_parser.parse_clauses().
    """

    version = "clause-v1"

    # ponytail: parse_clauses() has no upper bound on a span's length -- an
    # unrecognized document (or one giant annex/article) produces a single
    # clause spanning the whole document, which blows past Pinecone's 40KB
    # per-vector metadata limit (chunk text is almost all of that payload).
    # Sub-split any oversized span on paragraph boundaries so every stored
    # chunk stays well under that limit, rather than storing one giant chunk.
    _MAX_CHUNK_CHARS = 6000

    def __init__(
        self,
        document_title: str,
        regulation: str | None = None,
        jurisdiction: str | None = None,
        version_label: str | None = None,
        document_type: DocumentType | None = None,
        effective_date: date | None = None,
    ):
        self._document_title = document_title
        self._regulation = regulation
        self._jurisdiction = jurisdiction
        self._version_label = version_label
        self._document_type = document_type
        self._effective_date = effective_date

    def chunk(self, document: Document) -> list[Chunk]:
        if not document.content.strip():
            return []

        parse_result = parse_clauses(
            document.content,
            document_id=document.document_id,
            document_title=self._document_title,
        )

        chunks: list[Chunk] = []
        index = 0
        for clause_span in parse_result.clauses:
            legal_metadata = LegalMetadata(
                document_id=clause_span.metadata.document_id,
                document_title=clause_span.metadata.document_title,
                regulation=self._regulation,
                version=self._version_label,
                jurisdiction=self._jurisdiction,
                article=clause_span.metadata.article,
                section=clause_span.metadata.section,
                clause=clause_span.metadata.clause,
                effective_date=self._effective_date,
                document_type=self._document_type,
                page=clause_span.metadata.page,
            )
            for piece in self._split_oversized(clause_span.text):
                chunks.append(
                    Chunk(
                        chunk_id=uuid7(),
                        document_id=document.document_id,
                        chunk_index=index,
                        text=piece,
                        strategy_version=self.version,
                        heading=legal_metadata.article or legal_metadata.section,
                        page=legal_metadata.page,
                        char_count=len(piece),
                        legal_metadata=legal_metadata,
                    )
                )
                index += 1
        return chunks

    @classmethod
    def _split_oversized(cls, text: str) -> list[str]:
        """Split ``text`` into pieces <= ``_MAX_CHUNK_CHARS``, on paragraph
        boundaries where possible, hard-slicing any single paragraph that's
        still too long on its own."""
        if len(text) <= cls._MAX_CHUNK_CHARS:
            return [text]

        pieces: list[str] = []
        current = ""
        for paragraph in text.split("\n\n"):
            candidate = f"{current}\n\n{paragraph}" if current else paragraph
            if len(candidate) <= cls._MAX_CHUNK_CHARS:
                current = candidate
                continue
            if current:
                pieces.append(current)
                current = ""
            if len(paragraph) <= cls._MAX_CHUNK_CHARS:
                current = paragraph
            else:
                for start in range(0, len(paragraph), cls._MAX_CHUNK_CHARS):
                    pieces.append(paragraph[start : start + cls._MAX_CHUNK_CHARS])
        if current:
            pieces.append(current)
        return pieces
