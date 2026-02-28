"""
Tests for payment routes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from src.routes.payments import (
    _extract_payer_id,
)
from src.schemas import (
    NewDonationEvent,
    NewSubscriptionEvent,
    PhysicalOrderCreatedEvent,
    PhysicalOrderPayload,
    DonationPayload,
    SubscriptionPayload,
)


class TestExtractPayerId:
    """Tests for _extract_payer_id helper."""

    def test_extract_new_donation(self):
        """Tests extraction from new_donation event."""
        event = NewDonationEvent(
            created_at=datetime.now(timezone.utc),
            sent_at=datetime.now(timezone.utc),
            name="new_donation",
            payload=DonationPayload(
                user_id=1,
                telegram_user_id=123,
                donation_request_id=1,
                donation_name="Test",
                period="once",
                amount=300,
                currency="RUB",
                anonymously=False,
                web_app_link="https://test.com",
            ),
        )
        
        result = _extract_payer_id(event)
        
        assert result == 123

    def test_extract_new_subscription(self):
        """Tests extraction from new_subscription event."""
        event = NewSubscriptionEvent(
            created_at=datetime.now(timezone.utc),
            sent_at=datetime.now(timezone.utc),
            name="new_subscription",
            payload=SubscriptionPayload(
                user_id=1,
                telegram_user_id=456,
                subscription_name="Test",
                subscription_id=1,
                period_id=1,
                period="month",
                price=300,
                amount=300,
                currency="RUB",
                channel_id=1,
                channel_name="Test",
                type="regular",
            ),
        )
        
        result = _extract_payer_id(event)
        
        assert result == 456

    def test_extract_physical_order_paid(self):
        """Tests extraction from paid physical order."""
        payload = PhysicalOrderPayload(
            user_id=1,
            telegram_user_id=789,
            order_id=1,
            status="paid",
            products=[],
            total=300,
            currency="RUB",
            shipping_address="Test",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        event = PhysicalOrderCreatedEvent(
            created_at=datetime.now(timezone.utc),
            sent_at=datetime.now(timezone.utc),
            name="physical_order_created",
            payload=payload,
        )
        
        result = _extract_payer_id(event)
        
        assert result == 789

    def test_extract_physical_order_not_paid(self):
        """Tests extraction from non-paid physical order."""
        payload = PhysicalOrderPayload(
            user_id=1,
            telegram_user_id=789,
            order_id=1,
            status="pending",
            products=[],
            total=300,
            currency="RUB",
            shipping_address="Test",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        event = PhysicalOrderCreatedEvent(
            created_at=datetime.now(timezone.utc),
            sent_at=datetime.now(timezone.utc),
            name="physical_order_created",
            payload=payload,
        )
        
        result = _extract_payer_id(event)
        
        assert result is None

    def test_extract_unknown_event(self):
        """Tests extraction from unknown event type."""
        # Create a mock event with unknown name
        event = MagicMock()
        event.name = "unknown_event"
        event.payload = MagicMock()
        
        result = _extract_payer_id(event)
        
        assert result is None
