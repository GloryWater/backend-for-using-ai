"""
Тесты для API endpoints.

Используют моки для внешних сервисов и тестовую базу данных.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.db import Base, get_db
from src.database.models import License, User
from src.main import app


@pytest.fixture
async def db_engine():
    """Создаёт тестовый движок БД в памяти."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Создаёт тестовую сессию БД."""
    async_session = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
def test_client(db_session):
    """Создаёт тестовый клиент с переопределённой зависимостью БД."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")

    yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session):
    """Создаёт тестового пользователя."""
    user = User(telegram_id=123456, username="test_user")
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def active_license(db_session, test_user):
    """Создаёт активную лицензию для тестового пользователя."""
    from datetime import datetime, timedelta, timezone

    license_obj = License(
        key="test_key_abc123",
        hwid=None,
        is_active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        owner_id=test_user.telegram_id,
    )
    db_session.add(license_obj)
    await db_session.commit()
    return license_obj


@pytest.fixture
async def expired_license(db_session, test_user):
    """Создаёт просроченную лицензию для тестового пользователя."""
    from datetime import datetime, timedelta, timezone

    license_obj = License(
        key="expired_key_xyz789",
        hwid=None,
        is_active=True,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        owner_id=test_user.telegram_id,
    )
    db_session.add(license_obj)
    await db_session.commit()
    return license_obj


# ─── Health Check Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_check(test_client):
    """Тест basic health check endpoint."""
    response = await test_client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data
    assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_health_detailed(test_client):
    """Тест detailed health check endpoint."""
    response = await test_client.get("/health/detailed")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "components" in data
    assert any(c["name"] == "database" for c in data["components"])


@pytest.mark.asyncio
async def test_health_ready(test_client):
    """Тест readiness probe."""
    response = await test_client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_health_live(test_client):
    """Тест liveness probe."""
    response = await test_client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


# ─── Loader Version Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_loader_version(test_client):
    """Тест endpoint версии загрузчика."""
    response = await test_client.get("/loader/version")
    assert response.status_code == 200

    data = response.json()
    assert "version" in data
    assert "url" in data


# ─── Auth Endpoint Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auth_success(test_client, active_license):
    """Тест успешной аутентификации."""
    response = await test_client.post(
        "/auth",
        json={"key": "test_key_abc123", "hwid": "test_hwid_12345"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert "script_bytes" in data


@pytest.mark.asyncio
async def test_auth_license_not_found(test_client):
    """Тест аутентификации с несуществующим ключом."""
    response = await test_client.post(
        "/auth",
        json={"key": "nonexistent_key", "hwid": "test_hwid"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "error"
    assert "не найден" in data["message"].lower()


@pytest.mark.asyncio
async def test_auth_expired_license(test_client, expired_license):
    """Тест аутентификации с просроченной лицензией."""
    response = await test_client.post(
        "/auth",
        json={"key": "expired_key_xyz789", "hwid": "test_hwid"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "error"
    assert "истек" in data["message"].lower()


@pytest.mark.asyncio
async def test_auth_hwid_lock(test_client, active_license, db_session):
    """Тест HWID lock — первая активация."""
    # Первая активация — должна пройти
    response = await test_client.post(
        "/auth",
        json={"key": "test_key_abc123", "hwid": "hwid_first"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Обновляем лицензию из БД
    await db_session.refresh(active_license)
    assert active_license.hwid == "hwid_first"

    # Вторая активация с другим HWID — должна отказать
    response = await test_client.post(
        "/auth",
        json={"key": "test_key_abc123", "hwid": "hwid_second"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "hwid" in response.json()["message"].lower()


# ─── AI Edit Endpoint Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_edit_success(test_client, active_license, monkeypatch):
    """Тест успешного редактирования текста."""

    # Мокаем AI сервис
    async def mock_edit_text(text):
        return f"Edited: {text}"

    from src.services.ai_service import AIService

    monkeypatch.setattr(AIService, "edit_text", mock_edit_text)

    response = await test_client.post(
        "/edit",
        json={
            "key": "test_key_abc123",
            "hwid": "test_hwid",
            "text": "test advertisement text",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert "result" in data


@pytest.mark.asyncio
async def test_edit_invalid_license(test_client):
    """Тест редактирования с невалидной лицензией."""
    response = await test_client.post(
        "/edit",
        json={
            "key": "invalid_key",
            "hwid": "test_hwid",
            "text": "test text",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_edit_empty_text(test_client, active_license, monkeypatch):
    """Тест редактирования пустого текста."""

    async def mock_edit_text(text):
        return "ОТКАЗ: Пустой запрос или некорректный текст"

    from src.services.ai_service import AIService

    monkeypatch.setattr(AIService, "edit_text", mock_edit_text)

    response = await test_client.post(
        "/edit",
        json={
            "key": "test_key_abc123",
            "hwid": "test_hwid",
            "text": "",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
