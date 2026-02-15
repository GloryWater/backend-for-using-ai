import hashlib
import json
import logging
import os
import struct

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

_SYNC_BATCH_SIZE = 64


def _content_id(text: str) -> int:
    """Детерминированный uint64 ID из текста (SHA-256 → первые 8 байт).

    Один и тот же текст всегда даёт один и тот же ID,
    поэтому повторная загрузка не создаёт дубликатов.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    # Берём первые 8 байт, гарантируем положительное число
    return struct.unpack(">Q", digest[:8])[0] & 0x7FFFFFFFFFFFFFFF


def _extract_role(item: dict, role: str) -> str | None:
    """Извлекает content первого сообщения с заданной ролью."""
    return next(
        (m["content"] for m in item.get("messages", []) if m.get("role") == role),
        None,
    )


class VectorStore:
    """Обёртка над Qdrant с инкрементальной синхронизацией из JSONL."""

    def __init__(
        self,
        qdrant_url: str,
        collection_name: str,
        model: SentenceTransformer,
        similarity_threshold: float = 0.5,
        top_k: int = 10,
    ):
        self._client = AsyncQdrantClient(url=qdrant_url)
        self._collection = collection_name
        self._model = model
        self._threshold = similarity_threshold
        self._top_k = top_k

    async def initialize(self, data_file: str) -> None:
        """Создаёт коллекцию (если нет) и дозагружает новые примеры."""
        await self._ensure_collection_exists()
        await self._sync_from_file(data_file)

    async def find_similar(self, query: str) -> list[dict]:
        """Возвращает payload'ы ближайших примеров."""
        query_vector = await run_in_threadpool(self._model.encode, query)
        result = await self._client.query_points(
            collection_name=self._collection,
            query=query_vector.tolist(),
            limit=self._top_k,
            score_threshold=self._threshold,
        )
        return [point.payload for point in result.points]

    async def close(self) -> None:
        await self._client.close()

    # ── private ──────────────────────────────────────────────

    async def _ensure_collection_exists(self) -> None:
        if await self._client.collection_exists(self._collection):
            return
        logger.info("Creating Qdrant collection '%s'...", self._collection)
        sample = self._model.encode("test")
        await self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=len(sample), distance=Distance.COSINE),
        )

    async def _sync_from_file(self, path: str) -> None:
        """Потоково читает JSONL построчно, добавляет только отсутствующие точки.

        Файл НЕ загружается в память целиком — Python file iterator
        читает по одной строке за раз.
        """
        if not os.path.exists(path):
            logger.warning("Data file '%s' not found.", path)
            return

        batch: list[tuple[int, str, dict]] = []  # (id, text, payload)
        total_added = 0
        total_skipped = 0

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                # --- парсим одну строку ---
                try:
                    item = json.loads(line)
                    text = _extract_role(item, "user")
                    if not text:
                        continue
                except (json.JSONDecodeError, KeyError):
                    continue

                batch.append((_content_id(text), text, item))

                # --- когда батч набрался — обрабатываем и очищаем ---
                if len(batch) >= _SYNC_BATCH_SIZE:
                    added, skipped = await self._upsert_missing(batch)
                    total_added += added
                    total_skipped += skipped
                    batch.clear()

        # --- остаток ---
        if batch:
            added, skipped = await self._upsert_missing(batch)
            total_added += added
            total_skipped += skipped

        logger.info(
            "Qdrant sync complete: %d added, %d already existed.",
            total_added,
            total_skipped,
        )

    async def _upsert_missing(
        self, batch: list[tuple[int, str, dict]]
    ) -> tuple[int, int]:
        """Проверяет какие ID уже есть в Qdrant, вставляет только новые.

        Returns:
            (added_count, skipped_count)
        """
        ids = [pid for pid, _, _ in batch]

        # Запрашиваем существующие точки (без payload/vector — экономим трафик)
        existing = await self._client.query_points(
            collection_name=self._collection,
            ids=ids,
            with_payload=False,
            with_vectors=False,
        )
        existing_ids = {p.id for p in existing}

        # Фильтруем — оставляем только новые
        new = [
            (pid, text, payload)
            for pid, text, payload in batch
            if pid not in existing_ids
        ]

        skipped = len(batch) - len(new)
        if not new:
            return 0, skipped

        # Векторизуем только новые тексты
        texts = [text for _, text, _ in new]
        embeddings = await run_in_threadpool(
            self._model.encode, texts, batch_size=32, show_progress_bar=False
        )

        points = [
            PointStruct(id=pid, vector=vec.tolist(), payload=payload)
            for (pid, _, payload), vec in zip(new, embeddings)
        ]

        await self._client.upsert(collection_name=self._collection, points=points)
        return len(points), skipped
