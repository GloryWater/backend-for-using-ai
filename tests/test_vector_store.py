"""
Tests for VectorStore service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import struct
import hashlib

from src.services.vector_store import (
    VectorStore,
    VectorStoreConfig,
    VectorStoreError,
    QdrantConnectionError,
    _content_id,
    _extract_role,
    _SYNC_BATCH_SIZE,
    _MAX_RETRIES,
)


class TestContentId:
    """Tests for _content_id function."""

    def test_content_id_deterministic(self):
        """Tests that same text produces same ID."""
        text = "test advertisement"
        id1 = _content_id(text)
        id2 = _content_id(text)
        
        assert id1 == id2

    def test_content_id_different_texts(self):
        """Tests that different texts produce different IDs."""
        id1 = _content_id("text 1")
        id2 = _content_id("text 2")
        
        assert id1 != id2

    def test_content_id_is_uint64(self):
        """Tests that ID is within uint64 range."""
        id_val = _content_id("test")
        
        assert 0 <= id_val <= 0x7FFFFFFFFFFFFFFF

    def test_content_id_unicode(self):
        """Tests ID generation with unicode text."""
        id1 = _content_id("Привет мир")
        id2 = _content_id("Привет мир")
        
        assert id1 == id2


class TestExtractRole:
    """Tests for _extract_role function."""

    def test_extract_role_user(self):
        """Tests extracting user role content."""
        item = {
            "messages": [
                {"role": "user", "content": "User message"},
                {"role": "model", "content": "Model response"},
            ]
        }
        
        result = _extract_role(item, "user")
        
        assert result == "User message"

    def test_extract_role_model(self):
        """Tests extracting model role content."""
        item = {
            "messages": [
                {"role": "user", "content": "User message"},
                {"role": "model", "content": "Model response"},
            ]
        }
        
        result = _extract_role(item, "model")
        
        assert result == "Model response"

    def test_extract_role_not_found(self):
        """Tests when role is not found."""
        item = {
            "messages": [
                {"role": "system", "content": "System message"},
            ]
        }
        
        result = _extract_role(item, "user")
        
        assert result is None

    def test_extract_role_empty_messages(self):
        """Tests with empty messages list."""
        item = {"messages": []}
        
        result = _extract_role(item, "user")
        
        assert result is None

    def test_extract_role_missing_messages_key(self):
        """Tests when messages key is missing."""
        item = {}
        
        result = _extract_role(item, "user")
        
        assert result is None


class TestVectorStoreConfig:
    """Tests for VectorStoreConfig."""

    def test_config_default_values(self):
        """Tests default configuration values."""
        config = VectorStoreConfig(
            qdrant_url="http://localhost:6333",
            collection_name="test",
            model_name="test-model",
        )
        
        assert config.similarity_threshold == 0.5
        assert config.top_k == 10
        assert config.embedding_cache_size == 1000


class TestVectorStoreUtils:
    """Tests for VectorStore utility functions."""

    def test_sync_batch_size_defined(self):
        """Tests that batch size is properly defined."""
        assert isinstance(_SYNC_BATCH_SIZE, int)
        assert _SYNC_BATCH_SIZE > 0

    def test_max_retries_defined(self):
        """Tests that max retries is properly defined."""
        assert isinstance(_MAX_RETRIES, int)
        assert _MAX_RETRIES > 0
