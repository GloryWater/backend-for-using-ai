import logging

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from src.database.crud import add_license, set_payment_success_and_get_user
from src.dependencies import DbSession, Notifier, TributeBody
from src.schemas import PostbackData, TributeWebhookEvent, webhook_adapter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payments"])


@router.post("/callback")
async def handle_cryptocloud_postback(
    data: PostbackData,
    db: DbSession,
    notifier: Notifier,
):
    if data.status != "success":
        return {"message": "Not success status"}

    payer_id = await set_payment_success_and_get_user(db, f"INV-{data.invoice_id}")
    if not payer_id:
        return {"message": "Payment processed, but user not found"}

    key = await add_license(db, owner_id=payer_id, days=30)
    await notifier.send_license_issued(payer_id, key)
    return {"message": "Postback processed successfully"}


@router.post("/webhook/tribute")
async def handle_tribute_webhook(
    body_bytes: TributeBody,
    db: DbSession,
    notifier: Notifier,
):
    try:
        event: TributeWebhookEvent = webhook_adapter.validate_json(body_bytes)
    except ValidationError as e:
        logger.warning("Tribute payload validation error: %s", e)
        raise HTTPException(status_code=400, detail="Invalid payload structure")

    user_id = _extract_payer_id(event)
    if not user_id:
        return {"status": "ignored"}

    key = await add_license(db, owner_id=user_id, days=30)
    await notifier.send_license_issued(user_id, key)
    return {"status": user_id}


def _extract_payer_id(event: TributeWebhookEvent) -> int | None:
    """Извлекает telegram_user_id из события, если оно релевантно."""
    payload = event.payload

    if event.name in ("new_donation", "new_subscription"):
        return payload.telegram_user_id

    if event.name == "physical_order_created":
        if getattr(payload, "status", None) not in ("paid", "created"):
            return None
        return payload.telegram_user_id

    return None
