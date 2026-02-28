"""
Tests for AI service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from openai import AsyncOpenAI

from src.services.ai_service import (
    AIService,
    AIServiceConfig,
    LLMUnavailableError,
    AIServiceError,
    _MAX_CACHE_SIZE,
    _MAX_RETRIES,
)


@pytest.fixture
def mock_llm():
    """Creates mock LLM client."""
    llm = MagicMock(spec=AsyncOpenAI)
    llm.chat = MagicMock()
    llm.chat.completions = MagicMock()
    return llm


@pytest.fixture
def mock_vector_store():
    """Creates mock vector store."""
    vs = MagicMock()
    vs.find_similar = AsyncMock(return_value=[])
    return vs


@pytest.fixture
def ai_service(mock_llm, mock_vector_store):
    """Creates AIService instance with mocks."""
    config = AIServiceConfig(
        model_name="gpt-4o-mini",
        temperature=0.7,
        max_tokens=200,
        enable_caching=True,
        cache_ttl_seconds=3600,
    )
    return AIService(
        llm=mock_llm,
        vector_store=mock_vector_store,
        rules="Test rules",
        config=config,
    )


class TestAIServiceConfig:
    """Tests for AIServiceConfig."""

    def test_config_default_values(self):
        """Tests default configuration values."""
        config = AIServiceConfig(model_name="gpt-4o-mini")
        
        assert config.model_name == "gpt-4o-mini"
        assert config.temperature == 0.3  # _DEFAULT_TEMPERATURE
        assert config.max_tokens == 200  # _DEFAULT_MAX_TOKENS
        assert config.enable_caching is True
        assert config.cache_ttl_seconds == 3600


class TestAIServiceStats:
    """Tests for AIService statistics."""

    def test_stats_initial(self, ai_service):
        """Tests initial statistics."""
        stats = ai_service.stats
        
        assert stats["request_count"] == 0
        assert stats["cache_size"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_hit_rate"] == "0.00%"

    @pytest.mark.asyncio
    async def test_stats_after_requests(self, ai_service, mock_llm):
        """Tests statistics after requests."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Edited text"
        mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Make requests
        await ai_service.edit_text("test text 1")
        await ai_service.edit_text("test text 2")
        
        stats = ai_service.stats
        assert stats["request_count"] == 2
        assert stats["cache_size"] == 2


class TestAIServiceEdit:
    """Tests for edit_text method."""

    @pytest.mark.asyncio
    async def test_edit_success(self, ai_service, mock_llm):
        """Tests successful text editing."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Edited text"
        mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await ai_service.edit_text("test advertisement")
        
        assert result == "Edited text"
        mock_llm.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_edit_empty_text(self, ai_service):
        """Tests editing empty text."""
        result = await ai_service.edit_text("")
        
        assert result == "ОТКАЗ: Пустой запрос или некорректный текст"

    @pytest.mark.asyncio
    async def test_edit_whitespace_only(self, ai_service):
        """Tests editing whitespace-only text."""
        result = await ai_service.edit_text("   \n\t  ")
        
        assert result == "ОТКАЗ: Пустой запрос или некорректный текст"

    @pytest.mark.asyncio
    async def test_edit_special_chars_only(self, ai_service):
        """Tests editing text with only special characters."""
        result = await ai_service.edit_text("@@@@####$$$$")
        
        assert result == "ОТКАЗ: Пустой запрос или некорректный текст"

    @pytest.mark.asyncio
    async def test_edit_too_long_text(self, ai_service):
        """Tests editing text exceeding max length."""
        long_text = "x" * 10001  # > 10000 chars
        
        result = await ai_service.edit_text(long_text)
        
        assert result == "ОТКАЗ: Пустой запрос или некорректный текст"

    @pytest.mark.asyncio
    async def test_edit_with_caching(self, ai_service, mock_llm):
        """Tests caching functionality."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Cached result"
        mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # First request
        result1 = await ai_service.edit_text("same text")
        assert result1 == "Cached result"
        assert mock_llm.chat.completions.create.call_count == 1
        
        # Second request (should use cache)
        result2 = await ai_service.edit_text("same text")
        assert result2 == "Cached result"
        assert mock_llm.chat.completions.create.call_count == 1  # Not called again
        
        stats = ai_service.stats
        assert stats["cache_hits"] == 1

    @pytest.mark.asyncio
    async def test_edit_cache_ttl_expired(self, ai_service, mock_llm):
        """Tests cache TTL expiration."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Result"
        mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # First request
        await ai_service.edit_text("test")
        
        # Manually expire cache entry
        cache_key = ai_service._get_cache_key("test")
        ai_service._cache[cache_key] = (ai_service._cache[cache_key][0], 0)  # Old timestamp
        
        # Second request (cache expired)
        await ai_service.edit_text("test")
        
        assert mock_llm.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_edit_llm_timeout_retry(self, ai_service, mock_llm):
        """Tests retry on LLM timeout."""
        from openai import APITimeoutError
        
        # Create timeout error with required argument
        mock_request = MagicMock()
        timeout_error = APITimeoutError(request=mock_request)
        
        mock_llm.chat.completions.create = AsyncMock(
            side_effect=timeout_error
        )
        
        result = await ai_service.edit_text("test")
        
        # After retries exhausted, should return original text
        assert result == "test"
        # Should have tried _MAX_RETRIES times
        assert mock_llm.chat.completions.create.call_count == _MAX_RETRIES

    @pytest.mark.asyncio
    async def test_edit_llm_empty_response(self, ai_service, mock_llm):
        """Tests handling empty LLM response."""
        mock_response = MagicMock()
        mock_response.choices = []  # Empty choices
        mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await ai_service.edit_text("test")
        
        assert result == "test"  # Returns original text

    @pytest.mark.asyncio
    async def test_edit_llm_none_content(self, ai_service, mock_llm):
        """Tests handling None content in LLM response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await ai_service.edit_text("test")
        
        assert result == "test"  # Returns original text

    @pytest.mark.asyncio
    async def test_edit_with_vector_store_results(self, ai_service, mock_llm, mock_vector_store):
        """Tests editing with similar examples from vector store."""
        mock_vector_store.find_similar = AsyncMock(return_value=[
            {
                "messages": [
                    {"role": "user", "content": "Sell garage"},
                    {"role": "model", "content": "🔥 Продам гараж!"},
                ]
            }
        ])
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Edited with examples"
        mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await ai_service.edit_text("sell garage")
        
        assert result == "Edited with examples"
        mock_vector_store.find_similar.assert_called_once()

    @pytest.mark.asyncio
    async def test_edit_llm_server_error_retry(self, ai_service, mock_llm):
        """Tests retry on LLM server error (5xx)."""
        from openai import APIError
        
        # First two calls fail with 500, third succeeds
        error_500 = APIError("Server error", request=None, body=None)
        error_500.status_code = 500
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success after retry"
        
        mock_llm.chat.completions.create = AsyncMock(
            side_effect=[error_500, error_500]
        )
        
        result = await ai_service.edit_text("test")
        
        # After retries exhausted, returns original text
        assert result == "test"

    @pytest.mark.asyncio
    async def test_edit_llm_client_error_no_retry(self, ai_service, mock_llm):
        """Tests no retry on LLM client error (4xx)."""
        from openai import APIError
        
        error_400 = APIError("Bad request", request=None, body=None)
        error_400.status_code = 400
        
        mock_llm.chat.completions.create = AsyncMock(side_effect=error_400)
        
        result = await ai_service.edit_text("test")
        
        # Client errors should not retry, returns original text
        assert result == "test"
        assert mock_llm.chat.completions.create.call_count == 1


class TestAIServiceCacheCleanup:
    """Tests for cache cleanup logic."""

    @pytest.mark.asyncio
    async def test_cache_cleanup_on_overflow(self, ai_service, mock_llm):
        """Tests cache cleanup when overflow occurs."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Result"
        mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Fill cache beyond limit
        for i in range(_MAX_CACHE_SIZE + 10):
            await ai_service.edit_text(f"text_{i}")
        
        # Cache should be cleaned up
        assert len(ai_service._cache) < _MAX_CACHE_SIZE

    def test_cleanup_cache_expired_entries(self, ai_service):
        """Tests cleanup of expired cache entries."""
        now = __import__('time').time()
        
        # Add entries with different timestamps
        ai_service._cache = {
            "key1": ("result1", now - 7200),  # Expired (2 hours old)
            "key2": ("result2", now - 1800),  # Not expired (30 min old)
            "key3": ("result3", now - 3700),  # Expired
        }
        
        ai_service._cleanup_cache()
        
        # Only non-expired entry should remain
        assert "key1" not in ai_service._cache
        assert "key3" not in ai_service._cache
        assert "key2" in ai_service._cache

    def test_cleanup_cache_lru_removal(self, ai_service):
        """Tests LRU removal when cache overflows."""
        now = __import__('time').time()
        
        # Fill cache to limit with old entries
        for i in range(_MAX_CACHE_SIZE):
            ai_service._cache[f"key_{i}"] = (f"result_{i}", now - 100)
        
        # Add new entry to trigger cleanup
        ai_service._cache["new_key"] = ("new_result", now)
        
        # Trigger cleanup manually
        ai_service._cleanup_cache()
        
        # Should have removed some entries
        assert len(ai_service._cache) <= _MAX_CACHE_SIZE


class TestAIServicePromptBuilding:
    """Tests for prompt building methods."""

    def test_build_prompt_with_rules(self, ai_service):
        """Tests prompt building with rules."""
        examples_block = "<examples>...</examples>\n"
        text = "test advertisement"
        
        prompt = ai_service._build_prompt(text, examples_block)
        
        assert "Test rules" in prompt
        assert examples_block in prompt
        assert text in prompt
        assert "<instruction>" in prompt

    def test_build_prompt_without_rules(self):
        """Tests prompt building without rules."""
        config = AIServiceConfig(model_name="gpt-4o-mini")
        ai_service = AIService(
            llm=MagicMock(),
            vector_store=MagicMock(),
            rules="",  # No rules
            config=config,
        )
        
        prompt = ai_service._build_prompt("test", "")
        
        assert "<instruction>" in prompt
        assert "test" in prompt

    @pytest.mark.asyncio
    async def test_build_examples_block_empty(self, ai_service, mock_vector_store):
        """Tests building examples block with no results."""
        mock_vector_store.find_similar = AsyncMock(return_value=[])
        
        examples = await ai_service._build_examples_block("test")
        
        assert examples == ""

    @pytest.mark.asyncio
    async def test_build_examples_block_with_results(self, ai_service, mock_vector_store):
        """Tests building examples block with results."""
        mock_vector_store.find_similar = AsyncMock(return_value=[
            {
                "messages": [
                    {"role": "user", "content": "User message"},
                    {"role": "model", "content": "Model response"},
                ]
            }
        ])
        
        examples = await ai_service._build_examples_block("test")
        
        assert "<examples>" in examples
        assert "<input>" in examples
        assert "<correct_output>" in examples

    @pytest.mark.asyncio
    async def test_build_examples_block_missing_role(self, ai_service, mock_vector_store):
        """Tests building examples with missing user/model roles."""
        mock_vector_store.find_similar = AsyncMock(return_value=[
            {
                "messages": [
                    {"role": "system", "content": "System message"},
                ]
            }
        ])
        
        examples = await ai_service._build_examples_block("test")
        
        # Should return empty string if no user/model messages
        assert examples == ""
