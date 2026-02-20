# Copyright (c) 2026 Yauheni Sytsevich. All Rights Reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited.
# Proprietary and confidential.

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from src.database.crud import add_license, set_payment_success_and_get_user
from src.database.db import AsyncSessionLocal
from src.database.models import CryptocloudPayments
from src.dependencies import DbSession, Notifier, TributeBody
from src.schemas import PostbackData, TributeWebhookEvent, webhook_adapter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payments"])

# Префиксы для order_id
_CRYPTOCLOUD_ORDER_PREFIX = "INV-"
_IDEMPOTENCY_WINDOW_HOURS = 24


@router.post("/callback")
async def handle_cryptocloud_postback(
    data: PostbackData,
    notifier: Notifier,
):
    """
    Обработка вебхука от CryptoCloud.

    Идемпотентность:
        - Проверяем, не обрабатывали ли уже этот invoice_id
        - Используем атомарное обновление в БД
    """
    invoice_id = f"{_CRYPTOCLOUD_ORDER_PREFIX}{data.invoice_id}"

    # Логирование входящего запроса
    logger.info(
        "CryptoCloud postback received: invoice_id=%s, status=%s, amount=%.2f %s",
        invoice_id,
        data.status,
        data.amount_crypto,
        data.currency,
    )

    async with AsyncSessionLocal() as session:
        try:
            # Проверка на идемпотентность — ищем существующий платеж
            stmt = select(CryptocloudPayments).where(
                CryptocloudPayments.check_id == invoice_id
            )
            result = await session.execute(stmt)
            existing_payment = result.scalar_one_or_none()

            if existing_payment and existing_payment.isPaid:
                logger.warning(
                    "Duplicate postback ignored: invoice_id=%s already paid",
                    invoice_id,
                )
                return {"message": "Postback already processed"}

            if data.status != "success":
                logger.warning(
                    "CryptoCloud postback with non-success status: invoice_id=%s, status=%s",
                    invoice_id,
                    data.status,
                )
                return {"message": "Not success status"}

            # Обновляем платеж как успешный
            payer_id = await set_payment_success_and_get_user(session, invoice_id)

            if not payer_id:
                logger.error(
                    "Payment processed but user not found: invoice_id=%s",
                    invoice_id,
                )
                return {"message": "Payment recorded, but user notification failed"}

            # Выдача лицензии
            key = await add_license(session, owner_id=payer_id, days=30)

            # Уведомление пользователя
            await notifier.send_license_issued(payer_id, key)

            logger.info(
                "CryptoCloud postback processed successfully: invoice_id=%s, user_id=%d, key=%s***",
                invoice_id,
                payer_id,
                key[-4:],
            )

            return {"message": "Postback processed successfully"}

        except SQLAlchemyError as e:
            logger.exception("Database error during CryptoCloud postback: %s", e)
            # Возвращаем ошибку, чтобы CryptoCloud повторил попытку
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database error",
            ) from e
        except Exception as e:
            logger.exception("Unexpected error during CryptoCloud postback: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal error",
            ) from e


@router.post("/webhook/tribute")
async def handle_tribute_webhook(
    body_bytes: TributeBody,
    db: DbSession,
    notifier: Notifier,
):
    """
    Обработка вебхука от Tribute.

    Идемпотентность:
        - Используем created_at + user_id как ключ идемпотентности
        - Проверяем, не выдавали ли уже лицензию этому пользователю recently
    """
    try:
        event: TributeWebhookEvent = webhook_adapter.validate_json(body_bytes)
    except ValidationError as e:
        logger.warning("Tribute payload validation error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload structure",
        ) from e

    # Логирование события
    logger.info(
        "Tribute webhook received: event=%s, user_id=%s, amount=%s",
        event.name,
        getattr(event.payload, "telegram_user_id", "unknown"),
        getattr(event.payload, "amount", "unknown"),
    )

    user_id = _extract_payer_id(event)
    if not user_id:
        logger.debug(
            "Tribute event ignored: no payer_id extractable from event=%s",
            event.name,
        )
        return {"status": "ignored"}

    # Проверка на идемпотентность — не выдавали ли лицензию недавно
    async with AsyncSessionLocal() as session:
        try:
            # Проверяем, есть ли у пользователя активная лицензия, выданная недавно
            license_key = await _check_and_grant_license(
                session, user_id, event.created_at
            )

            if license_key:
                # Лицензия уже выдана или только что выдана
                return {"status": "processed", "user_id": user_id}

            # Выдача новой лицензии
            key = await add_license(session, owner_id=user_id, days=30)

            # Уведомление
            await notifier.send_license_issued(user_id, key)

            logger.info(
                "Tribute webhook processed: event=%s, user_id=%d, key=%s***",
                event.name,
                user_id,
                key[-4:],
            )

            return {"status": "processed", "user_id": user_id}

        except SQLAlchemyError as e:
            logger.exception("Database error during Tribute webhook: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database error",
            ) from e
        except Exception as e:
            logger.exception("Unexpected error during Tribute webhook: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal error",
            ) from e


async def _check_and_grant_license(
    session, user_id: int, event_time: datetime
) -> str | None:
    """
    Проверяет, не выдавали ли лицензию этому пользователю недавно.

    Returns:
        Ключ лицензии если уже выдана, None если нужно выдать
    """
    from src.database.crud import get_user_license

    # Проверяем существующую лицензию
    existing = await get_user_license(session, user_id)

    if existing:
        now = datetime.now(timezone.utc)
        # Если лицензия активна и выдана недавно (в пределах окна идемпотентности)
        if existing.is_active and existing.expires_at > now:
            time_since_created = now - existing.created_at
            if time_since_created.total_seconds() < _IDEMPOTENCY_WINDOW_HOURS * 3600:
                logger.warning(
                    "Duplicate license request ignored: user_id=%d, existing_key=%s***",
                    user_id,
                    existing.key[-4:],
                )
                return existing.key

    return None


def _extract_payer_id(event: TributeWebhookEvent) -> int | None:
    """Извлекает telegram_user_id из события, если оно релевантно."""
    payload = event.payload

    # События, которые точно содержат telegram_user_id
    if event.name in ("new_donation", "new_subscription"):
        return payload.telegram_user_id

    # Физические товары — только если статус "paid" или "created"
    if event.name == "physical_order_created":
        if getattr(payload, "status", None) not in ("paid", "created"):
            return None
        return payload.telegram_user_id

    # Остальные события игнорируем
    return None
