from __future__ import annotations

from datetime import datetime
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class AuthRequest(BaseModel):
    key: str
    hwid: str  # HWID присылает клиент (Lua)


class AIRequest(BaseModel):
    key: str
    hwid: str
    text: str


class AuthResponse(BaseModel):
    status: str
    script_bytes: str | None = None  # Base64 encoded lua bytecode
    message: str | None = None


class UpdateResponse(BaseModel):
    version: str
    url: str


class PostbackData(BaseModel):
    status: str
    invoice_id: str
    amount_crypto: float  # В логе это число (5.0), FastAPI сам приведет типы
    currency: str
    order_id: str
    token: str

    # Можно добавить invoice_info, если данные оттуда нужны.
    # Если нет — Pydantic просто проигнорирует лишние поля входящего JSON.
    invoice_info: Optional[dict] = None


class ProductItem(BaseModel):
    product_name: str
    quantity: int
    price: int
    currency: str


# --- Модели Payload (содержимое событий) ---


class BasePayload(BaseModel):
    user_id: int
    telegram_user_id: int
    model_config = ConfigDict(
        extra="ignore"
    )  # Игнорировать новые поля от API в будущем


class SubscriptionPayload(BasePayload):
    subscription_name: str
    subscription_id: int
    period_id: int
    period: str
    price: int
    amount: int
    currency: str
    channel_id: int
    channel_name: str
    expires_at: Optional[datetime] = None
    type: Literal["regular", "gift", "trial"]
    # Поля, специфичные для разных статусов подписки
    email: Optional[str] = None
    web_app_link: Optional[str] = None
    cancel_reason: Optional[str] = None


class DonationPayload(BasePayload):
    donation_request_id: int
    donation_name: str
    period: Literal["once", "monthly"]
    amount: int
    currency: str
    anonymously: bool
    web_app_link: str
    # Поле message есть только в new_donation
    message: Optional[str] = None


class PhysicalOrderPayload(BasePayload):
    order_id: int
    status: str
    products: List[ProductItem]
    total: int
    currency: str
    shipping_address: str
    tracking_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DigitalProductPayload(BasePayload):
    product_id: int
    amount: int
    currency: str


# --- Модели Событий (Связка name + payload) ---


class BaseEvent(BaseModel):
    created_at: datetime
    sent_at: datetime


# 1. События подписок
class NewSubscriptionEvent(BaseEvent):
    name: Literal["new_subscription"]
    payload: SubscriptionPayload


class RenewedSubscriptionEvent(BaseEvent):
    name: Literal["renewed_subscription"]
    payload: SubscriptionPayload


class CancelledSubscriptionEvent(BaseEvent):
    name: Literal["cancelled_subscription"]
    payload: SubscriptionPayload


# 2. События физических товаров
class PhysicalOrderCreatedEvent(BaseEvent):
    name: Literal["physical_order_created"]
    payload: PhysicalOrderPayload


class PhysicalOrderShippedEvent(BaseEvent):
    name: Literal["physical_order_shipped"]
    payload: PhysicalOrderPayload


class PhysicalOrderCanceledEvent(BaseEvent):
    name: Literal["physical_order_canceled"]
    payload: PhysicalOrderPayload


# 3. События донатов
class NewDonationEvent(BaseEvent):
    name: Literal["new_donation"]
    payload: DonationPayload


class RecurrentDonationEvent(BaseEvent):
    name: Literal["recurrent_donation"]
    payload: DonationPayload


class CancelledDonationEvent(BaseEvent):
    name: Literal["cancelled_donation"]
    payload: DonationPayload


# 4. Цифровые товары
class NewDigitalProductEvent(BaseEvent):
    name: Literal["new_digital_product"]
    payload: DigitalProductPayload


# --- ГЛАВНАЯ МОДЕЛЬ ---
# Используем Discriminated Union для автоматического выбора модели по полю 'name'
TributeWebhookEvent = Annotated[
    Union[
        NewSubscriptionEvent,
        RenewedSubscriptionEvent,
        CancelledSubscriptionEvent,
        PhysicalOrderCreatedEvent,
        PhysicalOrderShippedEvent,
        PhysicalOrderCanceledEvent,
        NewDonationEvent,
        RecurrentDonationEvent,
        CancelledDonationEvent,
        NewDigitalProductEvent,
    ],
    Field(discriminator="name"),
]

webhook_adapter = TypeAdapter(TributeWebhookEvent)
