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
    Handles CryptoCloud webhook.

    Idempotency:
        - Check if this invoice_id was already processed
        - Use atomic database update
    """
    invoice_id = f"{_CRYPTOCLOUD_ORDER_PREFIX}{data.invoice_id}"

    # Log incoming request
    logger.info(
        "CryptoCloud postback received: invoice_id=%s, status=%s, amount=%.2f %s",
        invoice_id,
        data.status,
        data.amount_crypto,
        data.currency,
    )

    async with AsyncSessionLocal() as session:
        try:
            # Idempotency check - look for existing payment
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
                    "CryptoCloud postback with non-success status: "
                    "invoice_id=%s, status=%s",
                    invoice_id,
                    data.status,
                )
                return {"message": "Not success status"}

            # Update payment as successful
            payer_id = await set_payment_success_and_get_user(session, invoice_id)

            if not payer_id:
                logger.error(
                    "Payment processed but user not found: invoice_id=%s",
                    invoice_id,
                )
                return {"message": "Payment recorded, but user notification failed"}

            # Issue license
            key = await add_license(session, owner_id=payer_id, days=30)

            # Notify user
            await notifier.send_license_issued(payer_id, key)

            logger.info(
                "CryptoCloud postback processed successfully: "
                "invoice_id=%s, user_id=%d, key=%s***",
                invoice_id,
                payer_id,
                key[-4:],
            )

            return {"message": "Postback processed successfully"}

        except SQLAlchemyError as e:
            logger.exception("Database error during CryptoCloud postback: %s", e)
            # Return error to allow CryptoCloud retry
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
    Handles Tribute webhook.

    Idempotency:
        - Use created_at + user_id as idempotency key
        - Check if license was already issued to this user
    """
    try:
        event: TributeWebhookEvent = webhook_adapter.validate_json(body_bytes)
    except ValidationError as e:
        logger.warning("Tribute payload validation error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload structure",
        ) from e

    # Log event
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

    # Idempotency check - check if license was issued recently
    async with AsyncSessionLocal() as session:
        try:
            # Check if user has an active license issued recently
            license_key = await _check_and_grant_license(
                session, user_id, event.created_at
            )

            if license_key:
                # License already issued or just issued
                return {"status": "processed", "user_id": user_id}

            # Issue new license
            key = await add_license(session, owner_id=user_id, days=30)

            # Notify
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
    Checks if a license was issued to this user recently.

    Returns:
        License key if already issued, None if needs to be issued
    """
    from src.database.crud import get_user_license

    # Check existing license
    existing = await get_user_license(session, user_id)

    if existing:
        now = datetime.now(timezone.utc)
        # If license is active and issued recently (within idempotency window)
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
    """Extracts telegram_user_id from event if applicable."""
    payload = event.payload

    # Events that definitely contain telegram_user_id
    if event.name in ("new_donation", "new_subscription"):
        return payload.telegram_user_id

    # Physical goods - only if status is "paid" or "created"
    if event.name == "physical_order_created":
        if getattr(payload, "status", None) not in ("paid", "created"):
            return None
        return payload.telegram_user_id

    # Ignore other events
    return None
