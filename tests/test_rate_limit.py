"""
Тесты для rate limiting middleware.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.middleware.rate_limit import (
    RateLimitConfig,
    RateLimiter,
    create_rate_limiter,
)


class TestRateLimiter:
    """Тесты для RateLimiter."""

    def test_rate_limiter_allows_within_limit(self):
        """Rate limiter разрешает запросы в пределах лимита."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(
                requests=5,
                window_seconds=60,
                block_duration_seconds=300,
            )
        )

        # Первые 5 запросов должны пройти
        for i in range(5):
            is_allowed, headers = limiter.is_allowed("client_1", "/test")
            assert is_allowed is True
            assert headers["X-RateLimit-Remaining"] == str(4 - i)

    def test_rate_limiter_blocks_over_limit(self):
        """Rate limiter блокирует превышение лимита."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(
                requests=3,
                window_seconds=60,
                block_duration_seconds=300,
            )
        )

        # Первые 3 запроса проходят
        for _ in range(3):
            is_allowed, _ = limiter.is_allowed("client_2", "/test")
            assert is_allowed is True

        # 4-й запрос блокируется
        is_allowed, headers = limiter.is_allowed("client_2", "/test")
        assert is_allowed is False
        assert "Retry-After" in headers
        assert headers["X-RateLimit-Remaining"] == "0"

    def test_rate_limiter_per_client_isolation(self):
        """Rate limiter изолирует клиентов друг от друга."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(
                requests=2,
                window_seconds=60,
                block_duration_seconds=300,
            )
        )

        # Клиент 1 исчерпывает лимит
        for _ in range(2):
            limiter.is_allowed("client_a", "/test")

        # Клиент 1 блокируется
        is_allowed_a, _ = limiter.is_allowed("client_a", "/test")
        assert is_allowed_a is False

        # Клиент 2 всё ещё может делать запросы
        is_allowed_b, _ = limiter.is_allowed("client_b", "/test")
        assert is_allowed_b is True

    def test_rate_limiter_different_paths(self):
        """Rate limiter поддерживает разные конфигурации для путей."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(
                requests=10,
                window_seconds=60,
                block_duration_seconds=300,
            )
        )

        # Настраиваем строгий лимит для /auth
        limiter.configure(
            "/auth",
            RateLimitConfig(
                requests=2,
                window_seconds=60,
                block_duration_seconds=300,
            ),
        )

        # /auth имеет строгий лимит
        for _ in range(2):
            limiter.is_allowed("client_3", "/auth")

        is_allowed, _ = limiter.is_allowed("client_3", "/auth")
        assert is_allowed is False

        # Сбрасываем клиента для /test (это другой клиент)
        # /test всё ещё имеет мягкий лимит
        is_allowed, _ = limiter.is_allowed("client_3_test", "/test")
        assert is_allowed is True


class TestCreateRateLimiter:
    """Тесты для create_rate_limiter."""

    def test_create_rate_limiter_defaults(self):
        """create_rate_limiter создаёт лимитер с настройками по умолчанию."""
        limiter = create_rate_limiter()

        # Проверка конфигурации для /auth
        config = limiter._get_config("/auth")
        assert config.requests == 10
        assert config.window_seconds == 60
        assert config.block_duration_seconds == 900

        # Проверка конфигурации для /edit
        config = limiter._get_config("/edit")
        assert config.requests == 30
        assert config.window_seconds == 60

        # Проверка конфигурации по умолчанию
        config = limiter._get_config("/unknown")
        assert config.requests == 100
        assert config.window_seconds == 60


@pytest.mark.asyncio
async def test_rate_limit_middleware_integration():
    """Интеграционный тест rate limiting middleware."""
    from fastapi import FastAPI
    from src.middleware.rate_limit import RateLimitMiddleware, create_rate_limiter

    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    app.add_middleware(
        RateLimitMiddleware,
        limiter=create_rate_limiter(
            default_requests=3,
            default_window_seconds=60,
            default_block_duration=60,
        ),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Первые 3 запроса проходят
        for i in range(3):
            response = await client.get("/test")
            assert response.status_code == 200
            assert "x-ratelimit-remaining" in response.headers

        # 4-й запрос блокируется
        response = await client.get("/test")
        assert response.status_code == 429
        assert "retry_after" in response.json()


@pytest.mark.asyncio
async def test_health_endpoints_excluded_from_rate_limit():
    """Health endpoints исключены из rate limiting."""
    from fastapi import FastAPI
    from src.middleware.rate_limit import RateLimitMiddleware, create_rate_limiter

    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/health/detailed")
    async def health_detailed():
        return {"status": "detailed"}

    app.add_middleware(
        RateLimitMiddleware,
        limiter=create_rate_limiter(
            default_requests=2,
            default_window_seconds=60,
            default_block_duration=60,
        ),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Делаем больше запросов чем лимит
        for _ in range(10):
            response = await client.get("/health")
            assert response.status_code == 200

        response = await client.get("/health/detailed")
        assert response.status_code == 200
