import hashlib
import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.db import get_db
from src.services.ai_service import AIService
from src.services.notification_service import NotificationService

# ── Сервисы из app.state ────────────────────────────────────


def _get_ai_service(request: Request) -> AIService:
    return request.app.state.ai_service


def _get_notifier(request: Request) -> NotificationService:
    return request.app.state.notification_service


# ── HMAC-верификация Tribute ─────────────────────────────────


async def _verify_tribute_signature(
    request: Request,
    trbt_signature: Annotated[str | None, Header()] = None,
) -> bytes:
    if not trbt_signature:
        raise HTTPException(status_code=401, detail="Missing signature header")

    body = await request.body()

    expected = hmac.new(
        settings.TRIBUTE_API_KEY.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, trbt_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    return body


# ── Type aliases для чистых сигнатур роутов ──────────────────

DbSession = Annotated[AsyncSession, Depends(get_db)]
AI = Annotated[AIService, Depends(_get_ai_service)]
Notifier = Annotated[NotificationService, Depends(_get_notifier)]
TributeBody = Annotated[bytes, Depends(_verify_tribute_signature)]
