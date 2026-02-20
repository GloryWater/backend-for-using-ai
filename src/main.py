# Copyright (c) 2026 Yauheni Sytsevich. All Rights Reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited.
# Proprietary and confidential.

import logging
import os
from contextlib import asynccontextmanager

from aiogram import Bot
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

from src.config import settings
from src.database.db import Base, engine
from src.middleware import create_rate_limiter, RateLimitMiddleware
from src.routes import ai, auth, health, payments
from src.routes.health import set_startup_time
from src.services.ai_service import AIService, AIServiceConfig
from src.services.notification_service import NotificationService
from src.services.vector_store import VectorStore, VectorStoreConfig

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def _load_rules() -> str:
    path = settings.RULES_FILE
    if not os.path.exists(path):
        logger.warning("Rules file '%s' not found. Running without rules.", path)
        return ""
    with open(path, "r", encoding="utf-8") as f:
        rules = f.read().strip()
    logger.info("Rules loaded (%d chars).", len(rules))
    return rules


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Устанавливаем время запуска для мониторинга
    set_startup_time()

    # ── Startup ──────────────────────────────────────────────
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # ML model (CPU, загружается один раз)
    logger.info("Loading ML model: %s", settings.ML_MODEL_NAME)
    ml_model = SentenceTransformer(settings.ML_MODEL_NAME)

    # Vector store
    vector_store_config = VectorStoreConfig(
        qdrant_url=settings.QDRANT_URL,
        collection_name=settings.QDRANT_COLLECTION,
        model_name=settings.ML_MODEL_NAME,
        similarity_threshold=settings.SIMILARITY_THRESHOLD,
        top_k=settings.TOP_K_EXAMPLES,
    )

    vector_store = VectorStore(config=vector_store_config, model=ml_model)
    await vector_store.initialize(settings.EXAMPLES_FILE)

    # LLM client
    llm_client = AsyncOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
    )

    # Telegram bot
    bot = Bot(token=settings.BOT_TOKEN)

    # Собираем сервисы и прокидываем через app.state

    app.state.ai_service = AIService(
        llm=llm_client,
        vector_store=vector_store,
        rules=_load_rules(),
        config=AIServiceConfig(
            model_name=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            enable_caching=True,
            cache_ttl_seconds=3600,
        ),
    )
    app.state.notification_service = NotificationService(bot)
    app.state.vector_store = vector_store

    logger.info(
        "Application started. LLM: %s, Collection: %s",
        settings.LLM_MODEL,
        settings.QDRANT_COLLECTION,
    )

    yield

    # ── Shutdown ─────────────────────────────────────────────
    logger.info("Shutting down application...")
    await app.state.notification_service.close()
    await vector_store.close()
    await llm_client.close()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Добавляем rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    limiter=create_rate_limiter(
        default_requests=100,
        default_window_seconds=60,
        default_block_duration=300,
    ),
)

app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(payments.router)
app.include_router(health.router)
