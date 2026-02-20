"""
Конфигурация pytest и общие фикстуры.
"""

import asyncio
import os
from typing import Generator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Устанавливаем тестовые переменные окружения перед импортом приложения
os.environ["DB_USER"] = "test"
os.environ["DB_PASS"] = "test"
os.environ["DB_NAME"] = "test"
os.environ["DB_HOST"] = "localhost"
os.environ["BOT_TOKEN"] = "fake_bot_token"
os.environ["LLM_API_KEY"] = "fake_llm_key"
os.environ["LLM_BASE_URL"] = "https://fake.url/v1"
os.environ["LLM_MODEL"] = "gpt-fake"
os.environ["TRIBUTE_API_KEY"] = "fake_tribute_key"
os.environ["CRYPTOCLOUD_API_KEY"] = "fake_crypto_key"
os.environ["QDRANT_URL"] = "http://localhost:6333"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Создаёт event loop для сессии тестов."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    """
    Создаёт тестовую сессию БД в памяти (SQLite).

    Использует SQLite для скорости тестов.
    """
    from src.database.db import Base

    # Создаём движок в памяти
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    # Создаём таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Создаём сессию
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    # Удаляем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
