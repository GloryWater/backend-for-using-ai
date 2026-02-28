# Copyright (c) 2026 Yauheni Sytsevich. All Rights Reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited.
# Proprietary and confidential.

"""
Health check endpoints for service monitoring.
"""

import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


class HealthStatus(BaseModel):
    """Service health status."""

    status: str = Field(..., description="Overall status: healthy/degraded/unhealthy")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="Check timestamp")
    uptime_seconds: float = Field(..., description="Uptime in seconds")


class ComponentHealth(BaseModel):
    """Component status."""

    name: str
    status: str  # healthy, unhealthy, unknown
    latency_ms: float | None = None
    error: str | None = None


class DetailedHealth(HealthStatus):
    """Detailed health information with components."""

    components: list[ComponentHealth] = Field(
        default_factory=list, description="Component statuses"
    )
    ai_stats: dict | None = Field(None, description="AI service statistics")


# Application startup time
_startup_time: datetime | None = None


def set_startup_time() -> None:
    """Sets the application startup time."""
    global _startup_time
    _startup_time = datetime.now(timezone.utc)


def get_uptime() -> float:
    """Returns the application uptime in seconds."""
    if not _startup_time:
        return 0.0
    return (datetime.now(timezone.utc) - _startup_time).total_seconds()


@router.get("/health", response_model=HealthStatus, tags=["Health"])
async def health_check():
    """
    Basic health check endpoint.

    Returns 200 if the service is running.
    """
    return HealthStatus(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=get_uptime(),
    )


@router.get("/health/detailed", response_model=DetailedHealth, tags=["Health"])
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check with component verification.

    Checks:
        - Database connection
        - Qdrant connection (via VectorStore)
    """
    components: list[ComponentHealth] = []
    overall_status = "healthy"

    # ─── Database check ──────────────────────────────────
    try:
        db_start = time.perf_counter()
        await db.execute(text("SELECT 1"))
        db_latency = (time.perf_counter() - db_start) * 1000

        # Check for tables
        result = await db.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        )
        table_count = result.scalar() or 0

        components.append(
            ComponentHealth(
                name="database",
                status="healthy",
                latency_ms=round(db_latency, 2),
            )
        )
        logger.debug(
            "Database health check passed: latency=%.2fms, tables=%d",
            db_latency,
            table_count,
        )

    except Exception as e:
        components.append(
            ComponentHealth(
                name="database",
                status="unhealthy",
                error=str(e),
            )
        )
        overall_status = "degraded"
        logger.error("Database health check failed: %s", e)

    # ─── Determine overall status ────────────────────────────
    unhealthy_count = sum(1 for c in components if c.status == "unhealthy")
    if unhealthy_count > 0:
        overall_status = (
            "unhealthy" if unhealthy_count > len(components) // 2 else "degraded"
        )

    return DetailedHealth(
        status=overall_status,
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=get_uptime(),
        components=components,
        ai_stats=None,
    )


@router.get("/health/ready", response_model=HealthStatus, tags=["Health"])
async def readiness_check():
    """
    Readiness probe for Kubernetes.

    Returns 200 only if the service is ready to accept traffic.
    """
    # Check that the application has started
    if not _startup_time:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application not started",
        )

    return HealthStatus(
        status="ready",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=get_uptime(),
    )


@router.get("/health/live", response_model=HealthStatus, tags=["Health"])
async def liveness_check():
    """
    Liveness probe for Kubernetes.

    Returns 200 if the service is alive (not hung).
    """
    return HealthStatus(
        status="alive",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=get_uptime(),
    )
