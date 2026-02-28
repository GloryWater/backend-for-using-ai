"""
Tests for bot keyboards.
"""

import pytest
from aiogram.types import InlineKeyboardMarkup
from src.bot.keyboards import (
    get_main_menu,
    get_my_key_menu,
    get_payment_methods_menu,
    get_crypto_payment_menu,
    get_tribute_payment_menu,
    get_back_menu,
)


class TestGetMainMenu:
    """Tests for get_main_menu."""

    def test_get_main_menu_structure(self):
        """Tests main menu structure."""
        keyboard = get_main_menu()

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 4

        # Row 1: My Key, Buy Key
        assert len(keyboard.inline_keyboard[0]) == 2
        assert keyboard.inline_keyboard[0][0].text == "🔑 Мой ключ"
        assert keyboard.inline_keyboard[0][0].callback_data == "my_key"
        assert keyboard.inline_keyboard[0][1].text == "💳 Купить ключ"
        assert keyboard.inline_keyboard[0][1].callback_data == "buy_key"

        # Row 2: Trial
        assert len(keyboard.inline_keyboard[1]) == 1
        assert keyboard.inline_keyboard[1][0].text == "🔥 Пробная версия"
        assert keyboard.inline_keyboard[1][0].callback_data == "get_trial"

        # Row 3: Download loader
        assert len(keyboard.inline_keyboard[2]) == 1
        assert keyboard.inline_keyboard[2][0].text == "📥 Скачать загрузчик"
        assert keyboard.inline_keyboard[2][0].callback_data == "getfile"

        # Row 4: Support
        assert len(keyboard.inline_keyboard[3]) == 1
        assert keyboard.inline_keyboard[3][0].text == "🚩 Сообщить об ошибке"
        assert keyboard.inline_keyboard[3][0].callback_data == "support"


class TestGetMyKeyMenu:
    """Tests for get_my_key_menu."""

    def test_get_my_key_menu_structure(self):
        """Tests my key menu structure."""
        keyboard = get_my_key_menu()

        assert len(keyboard.inline_keyboard) == 2

        # Row 1: Reset HWID
        assert len(keyboard.inline_keyboard[0]) == 1
        assert keyboard.inline_keyboard[0][0].text == "🔄 Сбросить устройство (HWID)"
        assert keyboard.inline_keyboard[0][0].callback_data == "reset_hwid"

        # Row 2: Back
        assert len(keyboard.inline_keyboard[1]) == 1
        assert keyboard.inline_keyboard[1][0].text == "🔙 Назад"
        assert keyboard.inline_keyboard[1][0].callback_data == "main_menu"


class TestGetPaymentMethodsMenu:
    """Tests for get_payment_methods_menu."""

    def test_get_payment_methods_menu_structure(self):
        """Tests payment methods menu structure."""
        keyboard = get_payment_methods_menu()

        assert len(keyboard.inline_keyboard) == 4

        # Row 1: Telegram Stars
        assert len(keyboard.inline_keyboard[0]) == 1
        assert keyboard.inline_keyboard[0][0].text == "⭐️ Telegram Stars"
        assert keyboard.inline_keyboard[0][0].callback_data == "pay_stars"

        # Row 2: Crypto
        assert len(keyboard.inline_keyboard[1]) == 1
        assert keyboard.inline_keyboard[1][0].text == "💎 Криптовалюта (Cryptomus)"
        assert keyboard.inline_keyboard[1][0].callback_data == "pay_crypto"

        # Row 3: Tribute
        assert len(keyboard.inline_keyboard[2]) == 1
        assert keyboard.inline_keyboard[2][0].text == "💳 Карта (Tribute)"
        assert keyboard.inline_keyboard[2][0].callback_data == "pay_tribute"

        # Row 4: Back
        assert len(keyboard.inline_keyboard[3]) == 1
        assert keyboard.inline_keyboard[3][0].text == "🔙 Назад"
        assert keyboard.inline_keyboard[3][0].callback_data == "main_menu"


class TestGetCryptoPaymentMenu:
    """Tests for get_crypto_payment_menu."""

    def test_get_crypto_payment_menu_structure(self):
        """Tests crypto payment menu structure."""
        keyboard = get_crypto_payment_menu(
            pay_url="https://test.pay",
            payment_uuid="test-uuid-123",
            price_usd=3.5,
        )

        assert len(keyboard.inline_keyboard) == 3

        # Row 1: Pay button with price
        assert len(keyboard.inline_keyboard[0]) == 1
        assert keyboard.inline_keyboard[0][0].text == "💎 Оплатить $3.5"
        assert keyboard.inline_keyboard[0][0].url == "https://test.pay"

        # Row 2: Check payment
        assert len(keyboard.inline_keyboard[1]) == 1
        assert keyboard.inline_keyboard[1][0].text == "🔄 Проверить оплату"
        assert keyboard.inline_keyboard[1][0].callback_data == "check_crypto:test-uuid-123"

        # Row 3: Cancel
        assert len(keyboard.inline_keyboard[2]) == 1
        assert keyboard.inline_keyboard[2][0].text == "🔙 Отмена"
        assert keyboard.inline_keyboard[2][0].callback_data == "buy_key"

    def test_get_crypto_payment_menu_different_prices(self):
        """Tests crypto payment menu with different prices."""
        keyboard = get_crypto_payment_menu(
            pay_url="https://pay.example.com",
            payment_uuid="uuid-456",
            price_usd=10.0,
        )

        assert keyboard.inline_keyboard[0][0].text == "💎 Оплатить $10.0"


class TestGetTributePaymentMenu:
    """Tests for get_tribute_payment_menu."""

    def test_get_tribute_payment_menu_structure(self):
        """Tests tribute payment menu structure."""
        keyboard = get_tribute_payment_menu(
            tribute_url="https://tribute.pay",
            price_rub=300,
        )

        assert len(keyboard.inline_keyboard) == 2

        # Row 1: Pay button
        assert len(keyboard.inline_keyboard[0]) == 1
        assert keyboard.inline_keyboard[0][0].text == "💳 Оплатить 300 RUB"
        assert keyboard.inline_keyboard[0][0].url == "https://tribute.pay"

        # Row 2: Cancel
        assert len(keyboard.inline_keyboard[1]) == 1
        assert keyboard.inline_keyboard[1][0].text == "🔙 Отмена"
        assert keyboard.inline_keyboard[1][0].callback_data == "buy_key"


class TestGetBackMenu:
    """Tests for get_back_menu."""

    def test_get_back_menu_structure(self):
        """Tests back menu structure."""
        keyboard = get_back_menu()

        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 1
        assert keyboard.inline_keyboard[0][0].text == "🔙 Назад"
        assert keyboard.inline_keyboard[0][0].callback_data == "main_menu"
