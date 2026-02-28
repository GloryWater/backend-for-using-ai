"""
Tests for rate limiting middleware.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.middleware.rate_limit import (
    RateLimitConfig,
    RateLimiter,
    create_rate_limiter,
)


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_rate_limiter_allows_within_limit(self):
        """Rate limiter allows requests within limit."""
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
        """Rate limiter blocks exceeding limit."""
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
        """Rate limiter isolates clients from each other."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(
                requests=2,
                window_seconds=60,
                block_duration_seconds=300,
            )
        )

        # Client 1 exhausts limit
        for _ in range(2):
            limiter.is_allowed("client_a", "/test")

        # Client 1 is blocked
        is_allowed_a, _ = limiter.is_allowed("client_a", "/test")
        assert is_allowed_a is False

        # Client 2 can still make requests
        is_allowed_b, _ = limiter.is_allowed("client_b", "/test")
        assert is_allowed_b is True

    def test_rate_limiter_different_paths(self):
        """Rate limiter supports different configurations for paths."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(
                requests=10,
                window_seconds=60,
                block_duration_seconds=300,
            )
        )

        # Configure strict limit for /auth
        limiter.configure(
            "/auth",
            RateLimitConfig(
                requests=2,
                window_seconds=60,
                block_duration_seconds=300,
            ),
        )

        # /auth has strict limit
        for _ in range(2):
            limiter.is_allowed("client_3", "/auth")

        is_allowed, _ = limiter.is_allowed("client_3", "/auth")
        assert is_allowed is False

        # Reset client for /test (this is a different client)
        # /test still has soft limit
        is_allowed, _ = limiter.is_allowed("client_3_test", "/test")
        assert is_allowed is True


class TestCreateRateLimiter:
    """Tests for create_rate_limiter."""

    def test_create_rate_limiter_defaults(self):
        """create_rate_limiter creates limiter with default settings."""
        limiter = create_rate_limiter()

        # Check configuration for /auth
        config = limiter._get_config("/auth")
        assert config.requests == 10
        assert config.window_seconds == 60
        assert config.block_duration_seconds == 900

        # Check configuration for /edit
        config = limiter._get_config("/edit")
        assert config.requests == 30
        assert config.window_seconds == 60

        # Check default configuration
        config = limiter._get_config("/unknown")
        assert config.requests == 100
        assert config.window_seconds == 60


@pytest.mark.asyncio
async def test_rate_limit_middleware_integration():
    """Integration test for rate limiting middleware."""
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
        # First 3 requests pass
        for i in range(3):
            response = await client.get("/test")
            assert response.status_code == 200
            assert "x-ratelimit-remaining" in response.headers

        # 4th request is blocked
        response = await client.get("/test")
        assert response.status_code == 429
        assert "retry_after" in response.json()


@pytest.mark.asyncio
async def test_health_endpoints_excluded_from_rate_limit():
    """Health endpoints are excluded from rate limiting."""
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
        # Make more requests than limit
        for _ in range(10):
            response = await client.get("/health")
            assert response.status_code == 200

        response = await client.get("/health/detailed")
        assert response.status_code == 200
