"""
Конфигурация pytest и общие фикстуры.

Запуск тестов:
    # Быстрые unit тесты (по умолчанию)
    pytest tests/ -v

    # Load тесты (требуют запущенного сервера)
    pytest tests/load/ -v --load

    # Load тесты в полном режиме (длительные)
    pytest tests/load/ -v --load --full-mode

    # Все тесты кроме load
    pytest tests/ -v -m "not load"

    # Конкретный тип тестов
    pytest tests/load/ -v --load -m stress
"""

import os

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


def pytest_collection_modifyitems(config, items):
    """Пропускает load тесты если не указан флаг --load."""
    # Проверяем, указан ли флаг --load
    if config.option.load:
        return

    # Проверяем, не запрошен ли конкретный маркер через -m
    markexpr = str(getattr(config.option, "markexpr", "") or "")
    load_markers = ["load", "stress", "soak", "spike", "chaos"]
    if any(marker in markexpr for marker in load_markers):
        # Маркер указан явно, разрешаем запуск
        return

    # Пропускаем load тесты если флаг --load не указан
    skip_load = pytest.mark.skip(reason="Need --load flag to run load tests")
    for item in items:
        if any(marker.name in load_markers for marker in item.iter_markers()):
            item.add_marker(skip_load)


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
