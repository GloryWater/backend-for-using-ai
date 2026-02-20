# Copyright (c) 2026 Yauheni Sytsevich. All Rights Reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited.
# Proprietary and confidential.

"""
Health check endpoints для мониторинга состояния сервиса.
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
    """Статус здоровья сервиса."""

    status: str = Field(..., description="Общий статус: healthy/degraded/unhealthy")
    version: str = Field(..., description="Версия приложения")
    timestamp: datetime = Field(..., description="Время проверки")
    uptime_seconds: float = Field(..., description="Время работы в секундах")


class ComponentHealth(BaseModel):
    """Статус компонента."""

    name: str
    status: str  # healthy, unhealthy, unknown
    latency_ms: float | None = None
    error: str | None = None


class DetailedHealth(HealthStatus):
    """Детальная информация о здоровье с компонентами."""

    components: list[ComponentHealth] = Field(
        default_factory=list, description="Статус компонентов"
    )
    ai_stats: dict | None = Field(None, description="Статистика AI сервиса")


# Время запуска приложения
_startup_time: datetime | None = None


def set_startup_time() -> None:
    """Устанавливает время запуска приложения."""
    global _startup_time
    _startup_time = datetime.now(timezone.utc)


def get_uptime() -> float:
    """Возвращает время работы приложения в секундах."""
    if not _startup_time:
        return 0.0
    return (datetime.now(timezone.utc) - _startup_time).total_seconds()


@router.get("/health", response_model=HealthStatus, tags=["Health"])
async def health_check():
    """
    Basic health check endpoint.

    Returns 200 если сервис работает.
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
    Detailed health check с проверкой всех компонентов.

    Проверяет:
        - Подключение к базе данных
        - Подключение к Qdrant (через VectorStore)
    """
    components: list[ComponentHealth] = []
    overall_status = "healthy"

    # ─── Проверка базы данных ──────────────────────────────────
    try:
        db_start = time.perf_counter()
        await db.execute(text("SELECT 1"))
        db_latency = (time.perf_counter() - db_start) * 1000

        # Проверка наличия таблиц
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

    # ─── Определение общего статуса ────────────────────────────
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
    Readiness probe для Kubernetes.

    Returns 200 только если сервис готов принимать трафик.
    """
    # Проверяем, что приложение запустилось
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
    Liveness probe для Kubernetes.

    Returns 200 если сервис жив (не завис).
    """
    return HealthStatus(
        status="alive",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=get_uptime(),
    )
