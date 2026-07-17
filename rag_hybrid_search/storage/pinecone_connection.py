"""Shared Pinecone index connection, used by both PineconeVectorStore and
PineconeChunkStore so they operate against one connection per index, not one
each -- vector and chunk-metadata storage are two ABCs/two classes here, but
one real Pinecone index underneath (see the migration spec for why they
aren't merged into a single class despite sharing storage).
"""

import logging
from pinecone import Pinecone

logger = logging.getLogger(__name__)


class PineconeConnection:
    def __init__(self, api_key: str, index_name: str, environment: str | None = None):
        try:
            self._client = Pinecone(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone client: {e}")
            self._client = None
        self._index_name = index_name
        self._index_instance = None
        self._init_error = None if self._client else str(e) if 'e' in locals() else "Unknown error"

    @property
    def index(self):
        """Lazy-initialized Pinecone index. Deferred validation allows app startup with
        dummy credentials in development; real API calls only happen on first data access."""
        if self._client is None:
            raise RuntimeError(f"Pinecone client not initialized: {self._init_error}")
        if self._index_instance is None:
            self._index_instance = self._client.Index(self._index_name)
        return self._index_instance

    @index.setter
    def index(self, value):
        """Allow tests to inject a fake index."""
        self._index_instance = value
