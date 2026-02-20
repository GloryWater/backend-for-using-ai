# Copyright (c) 2026 Yauheni Sytsevich. All Rights Reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited.
# Proprietary and confidential.

import asyncio
import hashlib
import json
import logging
import os
import struct
from dataclasses import dataclass
from typing import Final

import aiohttp
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    Filter,
    HasIdCondition,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

# Constants
_SYNC_BATCH_SIZE: Final[int] = 64
_MAX_RETRIES: Final[int] = 3
_RETRY_DELAY_SECONDS: Final[int] = 1
_QDRANT_TIMEOUT_SECONDS: Final[int] = 30


@dataclass(frozen=True)
class VectorStoreConfig:
    """Конфигурация VectorStore."""

    qdrant_url: str
    collection_name: str
    model_name: str
    similarity_threshold: float = 0.5
    top_k: int = 10
    embedding_cache_size: int = 1000


def _content_id(text: str) -> int:
    """Детерминированный uint64 ID из текста (SHA-256 → первые 8 байт).

    Один и тот же текст всегда даёт один и тот же ID,
    поэтому повторная загрузка не создаёт дубликатов.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return struct.unpack(">Q", digest[:8])[0] & 0x7FFFFFFFFFFFFFFF


def _extract_role(item: dict, role: str) -> str | None:
    """Извлекает content первого сообщения с заданной ролью."""
    return next(
        (m["content"] for m in item.get("messages", []) if m.get("role") == role),
        None,
    )


class VectorStoreError(Exception):
    """Базовое исключение для ошибок VectorStore."""


class QdrantConnectionError(VectorStoreError):
    """Ошибка подключения к Qdrant."""


class VectorStore:
    """
    Обёртка над Qdrant с инкрементальной синхронизацией из JSONL.

    Features:
        - Retry logic для всех операций с Qdrant
        - Timeout на все запросы
        - Детальное логирование
        - Проверка подключения при инициализации
    """

    def __init__(
        self,
        config: VectorStoreConfig,
        model: SentenceTransformer | None = None,
    ):
        self._config = config
        self._model = model or SentenceTransformer(config.model_name)
        self._client: AsyncQdrantClient | None = None
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Проверяет, инициализирован ли VectorStore."""
        return self._initialized

    async def initialize(self, data_file: str) -> None:
        """
        Создаёт коллекцию (если нет) и дозагружает новые примеры.

        Args:
            data_file: Путь к JSONL файлу с примерами

        Raises:
            QdrantConnectionError: Если не удалось подключиться к Qdrant
        """
        try:
            self._client = AsyncQdrantClient(
                url=self._config.qdrant_url,
                timeout=_QDRANT_TIMEOUT_SECONDS,
            )

            # Проверка подключения
            await self._check_connection()

            await self._ensure_collection_exists()
            await self._sync_from_file(data_file)

            self._initialized = True
            logger.info(
                "VectorStore initialized: collection=%s, threshold=%.2f, top_k=%d",
                self._config.collection_name,
                self._config.similarity_threshold,
                self._config.top_k,
            )

        except aiohttp.ClientError as e:
            logger.error("Failed to connect to Qdrant: %s", e)
            raise QdrantConnectionError(f"Cannot connect to Qdrant: {e}") from e
        except Exception:
            logger.exception("Unexpected error during VectorStore initialization")
            raise

    async def find_similar(self, query: str) -> list[dict]:
        """
        Возвращает payload'ы ближайших примеров.

        Args:
            query: Текст запроса

        Returns:
            Список payload найденных примеров

        Raises:
            VectorStoreError: Если произошла ошибка поиска
        """
        if not self._initialized or not self._client:
            logger.warning("VectorStore not initialized, returning empty results")
            return []

        try:
            query_vector = await run_in_threadpool(self._model.encode, query)

            result = await self._execute_with_retry(
                self._client.query_points,
                collection_name=self._config.collection_name,
                query=query_vector.tolist(),
                limit=self._config.top_k,
                score_threshold=self._config.similarity_threshold,
            )

            if result.points:
                logger.debug(
                    "Found %d similar examples for query: %.50s...",
                    len(result.points),
                    query,
                )

            return [point.payload for point in result.points if point.payload]

        except Exception as e:
            logger.exception("Error during similarity search: %s", e)
            return []

    async def close(self) -> None:
        """Закрывает соединение с Qdrant."""
        if self._client:
            await self._client.close()
            self._initialized = False
            logger.info("VectorStore closed")

    # ── private ──────────────────────────────────────────────

    async def _check_connection(self) -> None:
        """Проверяет подключение к Qdrant."""
        if not self._client:
            raise QdrantConnectionError("Client not initialized")

        try:
            await self._client.get_collections()
        except Exception as e:
            raise QdrantConnectionError(f"Qdrant connection failed: {e}") from e

    async def _execute_with_retry(self, func, *args, **kwargs):
        """Выполняет функцию с retry logic."""
        last_exception = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return await func(*args, **kwargs)
            except (aiohttp.ClientError, TimeoutError) as e:
                last_exception = e
                if attempt < _MAX_RETRIES:
                    logger.warning(
                        "Retry %d/%d after error: %s",
                        attempt,
                        _MAX_RETRIES,
                        e,
                    )
                    await asyncio.sleep(_RETRY_DELAY_SECONDS * attempt)
                else:
                    logger.error(
                        "All %d retries failed for %s",
                        _MAX_RETRIES,
                        func.__name__,
                    )

        raise VectorStoreError(
            f"Operation failed after {_MAX_RETRIES} retries"
        ) from last_exception

    async def _ensure_collection_exists(self) -> None:
        """Создаёт коллекцию если она не существует."""
        if not self._client:
            raise QdrantConnectionError("Client not initialized")

        if await self._client.collection_exists(self._config.collection_name):
            logger.debug("Collection '%s' already exists", self._config.collection_name)
            return

        logger.info("Creating Qdrant collection '%s'...", self._config.collection_name)

        try:
            sample = await run_in_threadpool(self._model.encode, "test")

            await self._client.create_collection(
                collection_name=self._config.collection_name,
                vectors_config=VectorParams(size=len(sample), distance=Distance.COSINE),
            )

            logger.info(
                "Collection '%s' created successfully", self._config.collection_name
            )

        except Exception:
            logger.exception("Failed to create collection")
            raise

    async def _sync_from_file(self, path: str) -> None:
        """
        Потоково читает JSONL построчно, добавляет только отсутствующие точки.

        Файл НЕ загружается в память целиком — Python file iterator
        читает по одной строке за раз.
        """
        if not os.path.exists(path):
            logger.warning("Data file '%s' not found.", path)
            return

        batch: list[tuple[int, str, dict]] = []  # (id, text, payload)
        total_added = 0
        total_skipped = 0
        total_parsed = 0

        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    item = json.loads(line)
                    text = _extract_role(item, "user")
                    if not text:
                        continue

                    total_parsed += 1
                    batch.append((_content_id(text), text, item))

                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(
                        "Skipping invalid JSONL line %d: %s",
                        line_num,
                        e,
                    )
                    continue

                if len(batch) >= _SYNC_BATCH_SIZE:
                    added, skipped = await self._upsert_missing(batch)
                    total_added += added
                    total_skipped += skipped
                    batch.clear()

        # Остаток
        if batch:
            added, skipped = await self._upsert_missing(batch)
            total_added += added
            total_skipped += skipped

        logger.info(
            "Qdrant sync complete: parsed=%d, added=%d, skipped=%d",
            total_parsed,
            total_added,
            total_skipped,
        )

    async def _upsert_missing(
        self, batch: list[tuple[int, str, dict]]
    ) -> tuple[int, int]:
        """Проверяет какие ID уже есть в Qdrant, вставляет только новые."""
        if not self._client:
            raise QdrantConnectionError("Client not initialized")

        ids = [pid for pid, _, _ in batch]

        try:
            existing_points, _ = await self._client.scroll(
                collection_name=self._config.collection_name,
                scroll_filter=Filter(
                    must=[HasIdCondition(has_id=[int(i) for i in ids])]
                ),
                limit=len(ids),
                with_payload=False,
                with_vectors=False,
            )
            existing_ids = {p.id for p in existing_points}
        except Exception:
            logger.exception("Error checking existing points")
            # Если не удалось проверить, пытаемся вставить всё (Qdrant обработает дубликаты)
            existing_ids = set()

        # Оставляем только новые
        new = [
            (pid, text, payload)
            for pid, text, payload in batch
            if pid not in existing_ids
        ]

        skipped = len(batch) - len(new)
        if not new:
            return 0, skipped

        # Векторизуем только новые
        texts = [text for _, text, _ in new]
        embeddings = await run_in_threadpool(
            self._model.encode, texts, batch_size=32, show_progress_bar=False
        )

        points = [
            PointStruct(id=pid, vector=vec.tolist(), payload=payload)
            for (pid, _, payload), vec in zip(new, embeddings)
        ]

        await self._client.upsert(
            collection_name=self._config.collection_name, points=points
        )
        return len(points), skipped
