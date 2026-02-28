"""
Tests for API endpoints.

Uses mocks for external services and test database.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import AsyncMock, MagicMock

from src.database.db import Base, get_db
from src.database.models import License, User
from src.main import app


@pytest.fixture
async def db_engine():
    """Creates test database engine in memory."""
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
    """Creates test database session."""
    async_session = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
def test_client(db_session):
    """Creates test client with overridden DB dependency and mocked services."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Мокаем AI сервис для тестов
    mock_ai_service = MagicMock()
    mock_ai_service.edit_text = AsyncMock(return_value="Edited text")
    app.state.ai_service = mock_ai_service

    # Мокаем notification сервис
    mock_notification_service = MagicMock()
    app.state.notification_service = mock_notification_service

    # Мокаем vector store
    mock_vector_store = MagicMock()
    mock_vector_store.search = AsyncMock(return_value=[])
    app.state.vector_store = mock_vector_store

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")

    yield client

    app.dependency_overrides.clear()
    # Очищаем моки
    if hasattr(app.state, "ai_service"):
        delattr(app.state, "ai_service")
    if hasattr(app.state, "notification_service"):
        delattr(app.state, "notification_service")
    if hasattr(app.state, "vector_store"):
        delattr(app.state, "vector_store")


@pytest.fixture
async def test_user(db_session):
    """Creates test user."""
    user = User(telegram_id=123456, username="test_user")
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def active_license(db_session, test_user):
    """Creates active license for test user."""
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
    """Creates expired license for test user."""
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
    """Tests basic health check endpoint."""
    response = await test_client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data
    assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_health_detailed(test_client):
    """Tests detailed health check endpoint."""
    response = await test_client.get("/health/detailed")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "components" in data
    assert any(c["name"] == "database" for c in data["components"])


@pytest.mark.asyncio
async def test_health_ready(test_client):
    """Tests readiness probe."""
    from src.routes.health import _startup_time, set_startup_time

    # Set startup time if not set
    if not _startup_time:
        set_startup_time()

    response = await test_client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_health_live(test_client):
    """Tests liveness probe."""
    response = await test_client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


# ─── Loader Version Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_loader_version(test_client):
    """Tests loader version endpoint."""
    response = await test_client.get("/loader/version")
    assert response.status_code == 200

    data = response.json()
    assert "version" in data
    assert "url" in data


# ─── Auth Endpoint Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auth_success(test_client, active_license):
    """Tests successful authentication."""
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
    """Tests authentication with non-existent key."""
    response = await test_client.post(
        "/auth",
        json={"key": "nonexistent_key", "hwid": "test_hwid"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()


@pytest.mark.asyncio
async def test_auth_expired_license(test_client, expired_license):
    """Tests authentication with expired license."""
    response = await test_client.post(
        "/auth",
        json={"key": "expired_key_xyz789", "hwid": "test_hwid"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "error"
    assert "expired" in data["message"].lower()


@pytest.mark.asyncio
async def test_auth_hwid_lock(test_client, active_license, db_session):
    """Tests HWID lock — first activation."""
    # First activation — should pass
    response = await test_client.post(
        "/auth",
        json={"key": "test_key_abc123", "hwid": "hwid_first"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Refresh license from DB
    await db_session.refresh(active_license)
    assert active_license.hwid == "hwid_first"

    # Second activation with different HWID — should fail
    response = await test_client.post(
        "/auth",
        json={"key": "test_key_abc123", "hwid": "hwid_second"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "hwid" in response.json()["message"].lower()


# ─── AI Edit Endpoint Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_edit_success(test_client, active_license):
    """Tests successful text editing."""
    # AI service is already mocked in test_client fixture

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
    assert "Edited" in data["result"]


@pytest.mark.asyncio
async def test_edit_invalid_license(test_client):
    """Tests editing with invalid license."""
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
async def test_edit_empty_text(test_client, active_license):
    """Tests editing empty text."""
    # Mock empty response
    from src.main import app

    app.state.ai_service.edit_text = AsyncMock(
        return_value="REFUSAL: Empty or invalid text"
    )

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
