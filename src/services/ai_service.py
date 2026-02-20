# Copyright (c) 2026 Yauheni Sytsevich. All Rights Reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited.
# Proprietary and confidential.

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Final

from openai import AsyncOpenAI, APIError, APITimeoutError

from src.services.vector_store import VectorStore
from src.utils.text import clean_llm_output

logger = logging.getLogger(__name__)

# Constants
_MAX_CACHE_SIZE: Final[int] = 1000
_DEFAULT_TEMPERATURE: Final[float] = 0.3
_DEFAULT_MAX_TOKENS: Final[int] = 200
_MAX_RETRIES: Final[int] = 2
_RETRY_DELAY_SECONDS: Final[float] = 1.0


@dataclass(frozen=True)
class AIServiceConfig:
    """Конфигурация AIService."""

    model_name: str
    temperature: float = _DEFAULT_TEMPERATURE
    max_tokens: int = _DEFAULT_MAX_TOKENS
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600  # 1 час


class AIServiceError(Exception):
    """Базовое исключение для ошибок AIService."""


class LLMUnavailableError(AIServiceError):
    """LLM сервис недоступен."""


class AIService:
    """
    Сервис редактирования объявлений с помощью LLM + RAG.

    Features:
        - Кэширование результатов LLM (LRU)
        - Retry logic для API вызовов
        - Детальное логирование
        - Валидация входных данных
        - Таймауты на запросы
    """

    def __init__(
        self,
        llm: AsyncOpenAI,
        vector_store: VectorStore,
        rules: str,
        config: AIServiceConfig | None = None,
    ):
        self._llm = llm
        self._vector_store = vector_store
        self._rules = rules
        self._config = config or AIServiceConfig(model_name="gpt-4o-mini")
        self._cache: dict[str, tuple[str, float]] = {}  # {hash: (result, timestamp)}
        self._request_count = 0
        self._cache_hits = 0

    @property
    def stats(self) -> dict:
        """Возвращает статистику работы сервиса."""
        cache_size = len(self._cache)
        hit_rate = (
            self._cache_hits / self._request_count * 100
            if self._request_count > 0
            else 0
        )
        return {
            "request_count": self._request_count,
            "cache_size": cache_size,
            "cache_hits": self._cache_hits,
            "cache_hit_rate": f"{hit_rate:.2f}%",
        }

    async def edit_text(self, text: str) -> str:
        """
        Редактирует текст объявления.

        Args:
            text: Исходный текст

        Returns:
            Отредактированный текст или оригинал при ошибке

        Raises:
            AIServiceError: При критической ошибке
        """
        self._request_count += 1
        text = text.strip()

        # Валидация входных данных
        if not self._validate_input(text):
            return "ОТКАЗ: Пустой запрос или некорректный текст"

        # Проверка кэша
        if self._config.enable_caching:
            cache_key = self._get_cache_key(text)
            if cached_result := self._get_from_cache(cache_key):
                self._cache_hits += 1
                logger.debug("Cache hit for text: %.30s...", text)
                return cached_result

        try:
            examples = await self._build_examples_block(text)
            prompt = self._build_prompt(text, examples)

            response = await self._call_llm_with_retry(prompt)

            if not response:
                logger.warning("LLM returned empty response")
                return text

            result = clean_llm_output(response)
            logger.info("[AI output]: %.100s…", result)

            # Сохранение в кэш
            if self._config.enable_caching and cache_key:
                self._save_to_cache(cache_key, result)

            return result

        except LLMUnavailableError as e:
            logger.error("LLM unavailable, returning original text: %s", e)
            return text  # fail-safe: возвращаем оригинал
        except AIServiceError as e:
            logger.exception("AIService error: %s", e)
            return text
        except Exception as e:
            logger.exception("Unexpected error in edit_text: %s", e)
            return text

    # ── private ──────────────────────────────────────────────

    def _validate_input(self, text: str) -> bool:
        """Проверяет валидность входного текста."""
        if not text:
            return False

        # Проверка на "мусор" (только спецсимволы)
        if all(not c.isalnum() and not c.isspace() for c in text):
            return False

        # Проверка максимальной длины (защита от DoS)
        if len(text) > 10000:
            logger.warning("Input text too long: %d chars", len(text))
            return False

        return True

    def _get_cache_key(self, text: str) -> str:
        """Генерирует ключ кэша для текста."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _get_from_cache(self, cache_key: str) -> str | None:
        """Получает результат из кэша с проверкой TTL."""
        if cache_key not in self._cache:
            return None

        result, timestamp = self._cache[cache_key]
        now = time.time()

        if now - timestamp > self._config.cache_ttl_seconds:
            # Истёк TTL
            del self._cache[cache_key]
            return None

        # LRU: обновляем timestamp при доступе
        self._cache[cache_key] = (result, now)
        return result

    def _save_to_cache(self, cache_key: str, result: str) -> None:
        """Сохраняет результат в кэш с очисткой старых записей."""
        # Очистка старых записей при переполнении
        if len(self._cache) >= _MAX_CACHE_SIZE:
            self._cleanup_cache()

        self._cache[cache_key] = (result, time.time())

    def _cleanup_cache(self) -> None:
        """Очищает старые записи кэша (LRU)."""
        now = time.time()
        expired = [
            key
            for key, (_, timestamp) in self._cache.items()
            if now - timestamp > self._config.cache_ttl_seconds
        ]

        for key in expired:
            del self._cache[key]

        # Если всё ещё переполнен, удаляем самые старые
        if len(self._cache) >= _MAX_CACHE_SIZE:
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            to_remove = _MAX_CACHE_SIZE // 4  # Удаляем 25%

            for key, _ in sorted_items[:to_remove]:
                del self._cache[key]

        logger.debug(
            "Cache cleanup: removed %d expired entries, current size: %d",
            len(expired),
            len(self._cache),
        )

    async def _call_llm_with_retry(self, prompt: str) -> str:
        """Вызывает LLM с retry logic."""
        last_exception: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await self._llm.chat.completions.create(
                    model=self._config.model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "Ты ИИ-редактор объявлений. Возвращай только отредактированный текст без пояснений.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self._config.temperature,
                    max_tokens=self._config.max_tokens,
                    timeout=30,
                    extra_body={"enable_thinking": False},
                    stream=False,
                )

                if not response.choices:
                    raise AIServiceError("Empty response from LLM")

                return response.choices[0].message.content or ""

            except APITimeoutError as e:
                last_exception = e
                logger.warning(
                    "LLM timeout (attempt %d/%d): %s", attempt, _MAX_RETRIES, e
                )

            except APIError as e:
                last_exception = e
                status_code = e.status_code if hasattr(e, "status_code") else None
                if status_code and status_code >= 500:
                    # Серверная ошибка — можно retry
                    logger.warning(
                        "LLM server error %d (attempt %d/%d): %s",
                        status_code,
                        attempt,
                        _MAX_RETRIES,
                        e,
                    )
                else:
                    # Клиентская ошибка — не retry
                    logger.error("LLM client error %d: %s", status_code or 0, e)
                    raise AIServiceError(f"LLM error: {e}") from e

            except Exception as e:
                last_exception = e
                logger.warning(
                    "Unexpected LLM error (attempt %d/%d): %s", attempt, _MAX_RETRIES, e
                )

            # Задержка перед retry (exponential backoff)
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_DELAY_SECONDS * attempt)

        raise LLMUnavailableError(
            f"LLM unavailable after {_MAX_RETRIES} retries"
        ) from last_exception

    async def _build_examples_block(self, query: str) -> str:
        """Строит блок примеров для промпта."""
        similar = await self._vector_store.find_similar(query)

        if not similar:
            logger.debug("No similar examples found for: %.50s...", query)
            return ""

        logger.debug("Found %d similar examples", len(similar))

        lines = []
        for item in similar:
            msgs = item.get("messages", [])
            user = next((m["content"] for m in msgs if m["role"] == "user"), "")
            model = next((m["content"] for m in msgs if m["role"] == "model"), "")

            if user and model:
                lines.append(
                    f"<input>{user}</input>\n<correct_output>{model}</correct_output>"
                )

        if not lines:
            return ""

        return (
            "\n<examples>\n"
            "Ниже приведены примеры того, как надо редактировать похожие объявления:\n"
            + "\n".join(lines)
            + "\n</examples>\n"
        )

    def _build_prompt(self, text: str, examples_block: str) -> str:
        """Строит финальный промпт для LLM."""
        rules_section = f"{self._rules}\n" if self._rules else ""

        return (
            f"{rules_section}"
            f"{examples_block}"
            f"<instruction>\n"
            f"Отредактируй следующий текст пользователя согласно правилам выше.\n"
            f"Входящий текст: {text}\n"
            f"Верни ТОЛЬКО отредактированный текст или причину отказа. "
            f"Никаких кавычек, markdown блоков или лишних слов.\n"
            f"</instruction>"
        )
