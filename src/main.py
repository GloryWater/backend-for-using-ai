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
from src.routes import ai, auth, payments
from src.services.ai_service import AIService
from src.services.notification_service import NotificationService
from src.services.vector_store import VectorStore

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
    # ── Startup ──────────────────────────────────────────────
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # ML model (CPU, загружается один раз)
    ml_model = SentenceTransformer(settings.ML_MODEL_NAME)

    # Vector store
    vector_store = VectorStore(
        qdrant_url=settings.QDRANT_URL,
        collection_name=settings.QDRANT_COLLECTION,
        model=ml_model,
        similarity_threshold=settings.SIMILARITY_THRESHOLD,
        top_k=settings.TOP_K_EXAMPLES,
    )
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
        model_name=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )
    app.state.notification_service = NotificationService(bot)

    logger.info("Application started. LLM: %s", settings.LLM_MODEL)

    yield

    # ── Shutdown ─────────────────────────────────────────────
    await app.state.notification_service.close()
    await llm_client.close()
    await vector_store.close()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(payments.router)
