"""
Rate limiting middleware для защиты API от злоупотреблений.

Использует simple in-memory хранилище с sliding window логикой.
Для production рекомендуется использовать Redis.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, DefaultDict, List, Tuple

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Конфигурация rate limit."""

    requests: int  # Количество запросов
    window_seconds: int  # Временное окно в секундах
    block_duration_seconds: int = 60  # Длительность блокировки при превышении


@dataclass
class RequestRecord:
    """Запись о запросах клиента."""

    timestamps: List[float] = field(default_factory=list)
    blocked_until: float = 0.0


class RateLimiter:
    """
    In-memory rate limiter с sliding window.

    WARNING: Для production используйте Redis-based rate limiting.
    """

    def __init__(self, default_config: RateLimitConfig | None = None):
        self._default_config = default_config or RateLimitConfig(
            requests=100,
            window_seconds=60,
            block_duration_seconds=300,
        )
        self._records: DefaultDict[str, RequestRecord] = defaultdict(RequestRecord)
        self._configs: dict[str, RateLimitConfig] = {}

    def configure(self, path_prefix: str, config: RateLimitConfig) -> None:
        """Настраивает rate limit для конкретного пути."""
        self._configs[path_prefix] = config

    def _get_config(self, path: str) -> RateLimitConfig:
        """Получает конфигурацию для пути."""
        for prefix, config in self._configs.items():
            if path.startswith(prefix):
                return config
        return self._default_config

    def _cleanup_old_requests(self, record: RequestRecord, window_seconds: int) -> None:
        """Удаляет старые запросы из окна."""
        now = time.time()
        cutoff = now - window_seconds
        record.timestamps = [ts for ts in record.timestamps if ts > cutoff]

    def is_allowed(self, client_id: str, path: str) -> Tuple[bool, dict]:
        """
        Проверяет, разрешён ли запрос.

        Returns:
            Tuple[bool, dict]: (разрешено, заголовки для ответа)
        """
        now = time.time()
        record = self._records[client_id]
        config = self._get_config(path)

        # Проверка блокировки
        if record.blocked_until > now:
            retry_after = int(record.blocked_until - now)
            return False, {
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(config.requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(record.blocked_until)),
            }

        # Сброс блокировки если истекла
        if record.blocked_until > 0 and record.blocked_until <= now:
            record.blocked_until = 0.0
            record.timestamps = []

        # Очистка старых запросов
        self._cleanup_old_requests(record, config.window_seconds)

        # Проверка лимита
        remaining = config.requests - len(record.timestamps)
        headers = {
            "X-RateLimit-Limit": str(config.requests),
            "X-RateLimit-Remaining": str(max(0, remaining - 1)),
            "X-RateLimit-Reset": str(int(now + config.window_seconds)),
        }

        if len(record.timestamps) >= config.requests:
            # Превышение лимита — блокируем
            record.blocked_until = now + config.block_duration_seconds
            headers["Retry-After"] = str(config.block_duration_seconds)
            headers["X-RateLimit-Remaining"] = "0"

            logger.warning(
                "Rate limit exceeded for %s on %s. Blocked until %s",
                client_id,
                path,
                record.blocked_until,
            )

            return False, headers

        # Разрешаем запрос
        record.timestamps.append(now)
        return True, headers


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware для rate limiting.

    Пример использования:
        app.add_middleware(
            RateLimitMiddleware,
            limiter=RateLimiter(
                default_config=RateLimitConfig(
                    requests=100,
                    window_seconds=60,
                    block_duration_seconds=300,
                )
            ),
        )
    """

    def __init__(self, app, limiter: RateLimiter | None = None):
        super().__init__(app)
        self._limiter = limiter or RateLimiter()

    async def _get_client_id(self, request: Request) -> str:
        """
        Получает идентификатор клиента.

        Приоритет:
            1. X-Forwarded-For header (первый IP)
            2. X-Real-IP header
            3. client.host
        """
        # Проверка X-Forwarded-For
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Берём первый IP (клиентский)
            return forwarded_for.split(",")[0].strip()

        # Проверка X-Real-IP
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        # Fallback на client.host
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable):
        client_id = await self._get_client_id(request)
        path = request.url.path

        # Исключаем health checks из rate limiting
        if path.startswith("/health"):
            return await call_next(request)

        is_allowed, headers = self._limiter.is_allowed(client_id, path)

        if not is_allowed:
            logger.warning(
                "Rate limit blocked: client=%s, path=%s",
                client_id,
                path,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": headers.get("Retry-After", "60"),
                },
                headers=headers,
            )

        response = await call_next(request)

        # Добавляем rate limit заголовки в ответ
        for header, value in headers.items():
            response.headers[header] = value

        return response


# ─── Helper functions ──────────────────────────────────────────────────────


def create_rate_limiter(
    default_requests: int = 100,
    default_window_seconds: int = 60,
    default_block_duration: int = 300,
) -> RateLimiter:
    """
    Создаёт настроенный rate limiter.

    Args:
        default_requests: Запросов по умолчанию в окно
        default_window_seconds: Размер окна по умолчанию
        default_block_duration: Длительность блокировки по умолчанию

    Returns:
        Настроенный RateLimiter
    """
    limiter = RateLimiter(
        default_config=RateLimitConfig(
            requests=default_requests,
            window_seconds=default_window_seconds,
            block_duration_seconds=default_block_duration,
        )
    )

    # Строгие лимиты для auth endpoints (защита от brute force)
    limiter.configure(
        "/auth",
        RateLimitConfig(
            requests=10,  # 10 попыток
            window_seconds=60,  # в минуту
            block_duration_seconds=900,  # 15 минут блокировка
        ),
    )

    # Лимиты для AI endpoints (дорогие запросы)
    limiter.configure(
        "/edit",
        RateLimitConfig(
            requests=30,  # 30 запросов
            window_seconds=60,  # в минуту
            block_duration_seconds=300,  # 5 минут блокировка
        ),
    )

    # Более мягкие лимиты для вебхуков (они редкие)
    limiter.configure(
        "/callback",
        RateLimitConfig(
            requests=50,
            window_seconds=60,
            block_duration_seconds=60,
        ),
    )

    limiter.configure(
        "/webhook",
        RateLimitConfig(
            requests=50,
            window_seconds=60,
            block_duration_seconds=60,
        ),
    )

    return limiter
