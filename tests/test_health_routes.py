"""
Tests for health routes with improved coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.routes.health import (
    health_check,
    detailed_health_check,
    readiness_check,
    liveness_check,
    set_startup_time,
    get_uptime,
    HealthStatus,
    DetailedHealth,
    ComponentHealth,
)


class TestHealthStatusModels:
    """Tests for health status Pydantic models."""

    def test_health_status_creation(self):
        """Tests HealthStatus model creation."""
        status = HealthStatus(
            status="healthy",
            version="0.1.0",
            timestamp=datetime.now(timezone.utc),
            uptime_seconds=100.5,
        )
        
        assert status.status == "healthy"
        assert status.version == "0.1.0"
        assert status.uptime_seconds == 100.5

    def test_detailed_health_creation(self):
        """Tests DetailedHealth model creation."""
        status = DetailedHealth(
            status="healthy",
            version="0.1.0",
            timestamp=datetime.now(timezone.utc),
            uptime_seconds=100.5,
            components=[
                ComponentHealth(
                    name="database",
                    status="healthy",
                    latency_ms=10.5,
                )
            ],
            ai_stats={"requests": 100},
        )
        
        assert status.status == "healthy"
        assert len(status.components) == 1
        assert status.ai_stats == {"requests": 100}

    def test_component_health_creation(self):
        """Tests ComponentHealth model creation."""
        component = ComponentHealth(
            name="qdrant",
            status="unhealthy",
            latency_ms=None,
            error="Connection refused",
        )
        
        assert component.name == "qdrant"
        assert component.status == "unhealthy"
        assert component.error == "Connection refused"


class TestStartupTime:
    """Tests for startup time utilities."""

    def test_get_uptime_no_startup_time(self):
        """Tests uptime when startup time not set."""
        # Save current state
        import src.routes.health as health_module
        original_startup = health_module._startup_time
        
        try:
            # Set to None
            health_module._startup_time = None
            
            uptime = get_uptime()
            assert uptime == 0.0
        finally:
            # Restore
            health_module._startup_time = original_startup

    def test_set_and_get_startup_time(self):
        """Tests setting and getting startup time."""
        import src.routes.health as health_module
        original_startup = health_module._startup_time
        
        try:
            set_startup_time()
            
            uptime = get_uptime()
            assert uptime >= 0.0
            assert health_module._startup_time is not None
        finally:
            health_module._startup_time = original_startup


class TestHealthEndpoints:
    """Tests for health endpoint functions."""

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self):
        """Tests basic health check endpoint."""
        result = await health_check()
        
        assert result.status == "healthy"
        assert result.version == "0.1.0"
        assert result.uptime_seconds >= 0.0
        assert isinstance(result.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_liveness_check_endpoint(self):
        """Tests liveness check endpoint."""
        result = await liveness_check()
        
        assert result.status == "alive"
        assert result.version == "0.1.0"

    @pytest.mark.asyncio
    async def test_readiness_check_success(self):
        """Tests readiness check when app is started."""
        import src.routes.health as health_module
        original_startup = health_module._startup_time
        
        try:
            set_startup_time()
            
            result = await readiness_check()
            
            assert result.status == "ready"
            assert result.version == "0.1.0"
        finally:
            health_module._startup_time = original_startup

    @pytest.mark.asyncio
    async def test_readiness_check_not_started(self):
        """Tests readiness check when app not started."""
        import src.routes.health as health_module
        original_startup = health_module._startup_time
        
        try:
            health_module._startup_time = None
            
            with pytest.raises(Exception) as exc_info:
                await readiness_check()
            
            assert exc_info.value.status_code == 503
            assert "not started" in exc_info.value.detail.lower()
        finally:
            health_module._startup_time = original_startup

    @pytest.mark.asyncio
    async def test_detailed_health_check_db_healthy(self):
        """Tests detailed health check with healthy database."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5  # 5 tables
        
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        import src.routes.health as health_module
        original_startup = health_module._startup_time
        
        try:
            set_startup_time()
            
            result = await detailed_health_check(mock_db)
            
            assert result.status == "healthy"
            assert len(result.components) >= 1
            assert any(c.name == "database" for c in result.components)
            
            db_component = next(c for c in result.components if c.name == "database")
            assert db_component.status == "healthy"
            assert db_component.latency_ms is not None
        finally:
            health_module._startup_time = original_startup

    @pytest.mark.asyncio
    async def test_detailed_health_check_db_unhealthy(self):
        """Tests detailed health check with unhealthy database."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
        
        import src.routes.health as health_module
        original_startup = health_module._startup_time
        
        try:
            set_startup_time()
            
            result = await detailed_health_check(mock_db)
            
            assert result.status == "unhealthy" or result.status == "degraded"
            
            db_component = next(c for c in result.components if c.name == "database")
            assert db_component.status == "unhealthy"
            assert db_component.error is not None
        finally:
            health_module._startup_time = original_startup

    @pytest.mark.asyncio
    async def test_detailed_health_check_degraded(self):
        """Tests detailed health check with degraded status."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))
        
        import src.routes.health as health_module
        original_startup = health_module._startup_time
        
        try:
            set_startup_time()
            
            result = await detailed_health_check(mock_db)
            
            # With only DB check failing, status should be unhealthy or degraded
            assert result.status in ["unhealthy", "degraded"]
        finally:
            health_module._startup_time = original_startup
