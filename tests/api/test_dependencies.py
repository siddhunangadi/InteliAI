from unittest.mock import MagicMock, patch

from api.dependencies import _select_chunker, _select_generation_provider, build_container
from rag_hybrid_search.config import Settings
from rag_hybrid_search.ingestion.chunkers.fixed import FixedChunker
from rag_hybrid_search.ingestion.chunkers.recursive import RecursiveChunker
from rag_hybrid_search.ingestion.chunkers.semantic import SemanticChunker
from rag_hybrid_search.providers.gemini import GeminiProvider
from rag_pipeline.generation_provider import MockProvider


def test_build_container_wires_pinecone_backend(tmp_path):
    settings = Settings(
        data_dir=str(tmp_path),
        pinecone_api_key="k", pinecone_index_name="idx",
    )
    with patch("api.dependencies.PineconeConnection") as mock_client_cls, \
         patch("api.dependencies.PineconeVectorStore") as mock_vs_cls, \
         patch("api.dependencies.PineconeChunkStore") as mock_cs_cls:
        mock_client_cls.return_value = MagicMock()
        mock_vs_cls.return_value = MagicMock()
        mock_cs_cls.return_value = MagicMock()
        container = build_container(settings)
        mock_client_cls.assert_called_once_with(
            api_key="k", index_name="idx", environment=None,
        )
        mock_vs_cls.assert_called_once_with(mock_client_cls.return_value)
        mock_cs_cls.assert_called_once_with(
            mock_client_cls.return_value, embedding_dimension=8,
        )
        assert container.index_manager.vector_store is mock_vs_cls.return_value
        assert container.chunk_store is mock_cs_cls.return_value


def test_select_chunker_dispatches_on_strategy():
    embedding_provider = MagicMock()
    assert isinstance(_select_chunker(Settings(chunking_strategy="fixed"), embedding_provider), FixedChunker)
    assert isinstance(_select_chunker(Settings(chunking_strategy="recursive"), embedding_provider), RecursiveChunker)
    assert isinstance(_select_chunker(Settings(chunking_strategy="semantic"), embedding_provider), SemanticChunker)


def test_select_generation_provider_picks_gemini():
    settings = Settings(provider="gemini", gemini_api_key="k")
    provider, name = _select_generation_provider(settings, nvidia_provider=None)
    assert isinstance(provider, GeminiProvider)
    assert name == "gemini"


def test_select_generation_provider_falls_back_to_mock_without_key():
    settings = Settings(provider="gemini", gemini_api_key=None)
    provider, name = _select_generation_provider(settings, nvidia_provider=None)
    assert isinstance(provider, MockProvider)
    assert name == "mock"
