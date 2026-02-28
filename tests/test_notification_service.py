"""
Tests for notification service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.notification_service import NotificationService


@pytest.fixture
def mock_bot():
    """Creates mock Telegram bot."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.session = MagicMock()
    bot.session.close = AsyncMock()
    return bot


@pytest.fixture
def notification_service(mock_bot):
    """Creates NotificationService instance."""
    return NotificationService(bot=mock_bot)


class TestNotificationServiceSend:
    """Tests for sending notifications."""

    @pytest.mark.asyncio
    async def test_send_license_issued_success(self, notification_service, mock_bot):
        """Tests successful license issued notification."""
        await notification_service.send_license_issued(123456, "test_key_abc123")
        
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        
        assert call_args.kwargs["chat_id"] == 123456
        assert "test_key_abc123" in call_args.kwargs["text"]
        assert "Оплата прошла успешно" in call_args.kwargs["text"]
        assert call_args.kwargs["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    async def test_send_license_issued_bot_error(self, notification_service, mock_bot):
        """Tests handling bot error."""
        mock_bot.send_message.side_effect = Exception("Bot error")
        
        # Should not raise
        await notification_service.send_license_issued(123456, "test_key")

    @pytest.mark.asyncio
    async def test_send_license_issued_formatting(self, notification_service, mock_bot):
        """Tests message formatting."""
        await notification_service.send_license_issued(789, "key_xyz")
        
        call_args = mock_bot.send_message.call_args
        text = call_args.kwargs["text"]
        
        assert "✅" in text
        assert "<b>" in text  # HTML formatting
        assert "<code>key_xyz</code>" in text


class TestNotificationServiceClose:
    """Tests for closing notification service."""

    @pytest.mark.asyncio
    async def test_close_success(self, notification_service, mock_bot):
        """Tests successful close."""
        await notification_service.close()
        
        mock_bot.session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_error(self, notification_service, mock_bot):
        """Tests close with error."""
        mock_bot.session.close.side_effect = Exception("Close error")
        
        # Should raise
        with pytest.raises(Exception):
            await notification_service.close()


class TestNotificationServiceInit:
    """Tests for initialization."""

    def test_init_stores_bot(self, mock_bot):
        """Tests bot is stored on init."""
        service = NotificationService(bot=mock_bot)
        
        assert service._bot == mock_bot
