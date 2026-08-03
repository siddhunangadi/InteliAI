import pytest

from rag_hybrid_search.metadata_extraction import ExtractedMetadata, extract_metadata


class _StubProvider:
    def __init__(self, response: str):
        self._response = response

    def generate(self, prompt: str, **kwargs) -> str:
        return self._response


_FULL_JSON = (
    '{"document_type": "regulation", "authority": "Reserve Bank of India", '
    '"regulation": "Master Circular on KYC", "jurisdiction": "India", '
    '"risk_category": "high", "version": "2025", "effective_date": "2025-04-01"}'
)


def test_extracts_all_fields_from_well_formed_json():
    result = extract_metadata(_StubProvider(_FULL_JSON), "some document text")
    assert result == ExtractedMetadata(
        document_type="regulation",
        authority="Reserve Bank of India",
        regulation="Master Circular on KYC",
        jurisdiction="India",
        risk_category="high",
        version="2025",
        effective_date="2025-04-01",
    )
    assert result.fields_found == 7


def test_strips_markdown_code_fence():
    fenced = f"```json\n{_FULL_JSON}\n```"
    result = extract_metadata(_StubProvider(fenced), "some document text")
    assert result.authority == "Reserve Bank of India"


def test_missing_fields_become_null_not_fabricated():
    partial = '{"document_type": "policy"}'
    result = extract_metadata(_StubProvider(partial), "some document text")
    assert result.document_type == "policy"
    assert result.authority is None
    assert result.effective_date is None
    assert result.fields_found == 1


def test_malformed_json_degrades_to_all_null_instead_of_raising():
    result = extract_metadata(_StubProvider("not json at all"), "some document text")
    assert result == ExtractedMetadata()


def test_provider_error_degrades_to_all_null_instead_of_raising():
    class _RaisingProvider:
        def generate(self, prompt: str, **kwargs) -> str:
            raise RuntimeError("provider unavailable")

    result = extract_metadata(_RaisingProvider(), "some document text")
    assert result == ExtractedMetadata()


def test_empty_document_skips_the_provider_call_entirely():
    class _FailIfCalled:
        def generate(self, prompt: str, **kwargs) -> str:
            raise AssertionError("provider should not be called for empty text")

    result = extract_metadata(_FailIfCalled(), "   ")
    assert result == ExtractedMetadata()
