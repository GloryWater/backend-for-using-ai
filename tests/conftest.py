"""
Pytest configuration and common fixtures.

Run tests:
    # Fast unit tests (default)
    pytest tests/ -v

    # Load tests (require running server)
    pytest tests/load/ -v --load

    # Load tests in full mode (long)
    pytest tests/load/ -v --load --full-mode

    # All tests except load
    pytest tests/ -v -m "not load"

    # Specific test type
    pytest tests/load/ -v --load -m stress
"""

import os
from pathlib import Path

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


@pytest.fixture(scope="session", autouse=True)
def setup_test_files():
    """Creates test files (script, version) for tests."""
    # Create protected directory if not exists
    protected_dir = Path("protected")
    protected_dir.mkdir(exist_ok=True)

    # Create fake Lua script
    script_file = protected_dir / "scriptV2.lua"
    if not script_file.exists():
        script_file.write_text("-- Test script\nprint('Hello from test script')")

    # Create loader_version.json if not exists
    version_file = Path("loader_version.json")
    if not version_file.exists():
        version_file.write_text('{"version": "0.1", "url": "http://test/loader.lua"}')

    yield


def pytest_collection_modifyitems(config, items):
    """Skips load tests if --load flag is not specified."""
    # Check if --load flag is specified (use getattr for safety)
    if getattr(config.option, "load", False):
        return

    # Check if specific marker is not requested via -m
    markexpr = str(getattr(config.option, "markexpr", "") or "")
    load_markers = ["load", "stress", "soak", "spike", "chaos"]
    if any(marker in markexpr for marker in load_markers):
        # Marker is specified explicitly, allow run
        return

    # Skip load tests if --load flag is not specified
    skip_load = pytest.mark.skip(reason="Need --load flag to run load tests")
    for item in items:
        if any(marker.name in load_markers for marker in item.iter_markers()):
            item.add_marker(skip_load)


@pytest.fixture
async def db_session():
    """
    Creates test DB session in memory (SQLite).

    Uses SQLite for fast tests.
    """
    from src.database.db import Base

    # Create in-memory engine
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
