# Copyright (c) 2026 Yauheni Sytsevich. All Rights Reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited.
# Proprietary and confidential.

import logging
import os
import uuid
from typing import List

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContextManager:
    def __init__(self):
        # Получаем настройки из переменных окружения
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        self.qdrant_api_key = os.getenv(
            "QDRANT_API_KEY", None
        )  # Добавлена поддержка ключа
        self.collection_name = "dialog_context"

        # Инициализация клиента Qdrant
        self.qdrant = AsyncQdrantClient(
            host=self.qdrant_host,
            port=self.qdrant_port,
            api_key=self.qdrant_api_key,
            # Важно: для работы внутри докер-сети иногда нужно увеличить таймаут
            timeout=10,
        )

        # Инициализация эмбеддингов (размерность 384 для модели по умолчанию)
        self.embeddings = FastEmbedEmbeddings()
        self.vector_size = 384

    async def init_collection(self):
        """Создает коллекцию, если она не существует."""
        try:
            # Проверяем существование коллекции
            if await self.qdrant.collection_exists(
                collection_name=self.collection_name
            ):
                logger.info(f"Коллекция '{self.collection_name}' уже существует.")
                return

            # Создаем коллекцию, если её нет
            await self.qdrant.collections.create(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size, distance=models.Distance.COSINE
                ),
            )
            logger.info(f"Коллекция '{self.collection_name}' успешно создана.")

        except Exception as e:
            logger.error(f"Ошибка при инициализации коллекции: {e}")

    async def add_to_context(self, user_id: int, text: str, role: str):
        """Добавляет сообщение в контекст (векторизирует и сохраняет)."""
        try:
            # Векторизация текста
            vector = await self.embeddings.aembed_query(text)

            payload = {
                "user_id": user_id,
                "text": text,
                "role": role,
                "timestamp": uuid.uuid1().time,  # Можно заменить на реальный datetime
            }

            # ИСПРАВЛЕНО: используем points.upsert вместо upsert
            await self.qdrant.points.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=uuid.uuid4().hex, vector=vector, payload=payload
                    )
                ],
            )
            logger.info(f"Сообщение добавлено в контекст для пользователя {user_id}")

        except Exception as e:
            logger.error(f"Ошибка добавления в контекст: {e}")

    async def get_relevant_context(
        self, user_id: int, query: str, limit: int = 5
    ) -> str:
        """Поиск релевантного контекста по вектору запроса."""
        try:
            query_vector = await self.embeddings.aembed_query(query)

            # Фильтр для поиска только по конкретному user_id
            search_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id", match=models.MatchValue(value=user_id)
                    )
                ]
            )

            # ИСПРАВЛЕНО: используем points.search вместо search
            search_result = await self.qdrant.points.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=search_filter,
                with_payload=True,
            )

            # Формируем строку контекста из найденных результатов
            context_messages = []
            for hit in search_result:
                if hit.payload:
                    role = hit.payload.get("role", "unknown")
                    text = hit.payload.get("text", "")
                    context_messages.append(f"{role}: {text}")

            # Разворачиваем, чтобы старые были сверху (если Qdrant вернул по релевантности, хронология может сбиться, но для RAG это часто ок)
            return "\n".join(context_messages)

        except Exception as e:
            logger.error(f"Ошибка поиска в Qdrant: {e}")
            return ""

    async def clear_context(self, user_id: int):
        """Удаляет контекст конкретного пользователя."""
        try:
            delete_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id", match=models.MatchValue(value=user_id)
                    )
                ]
            )

            # ИСПРАВЛЕНО: используем points.delete вместо delete
            await self.qdrant.points.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=delete_filter),
            )
            logger.info(f"Контекст очищен для пользователя {user_id}")

        except Exception as e:
            logger.error(f"Ошибка очистки контекста: {e}")
