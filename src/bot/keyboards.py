from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔑 Мой ключ", callback_data="my_key"),
                InlineKeyboardButton(text="💳 Купить ключ", callback_data="buy_key"),
            ],
            [InlineKeyboardButton(text="🔥 Пробная версия", callback_data="get_trial")],
            [
                InlineKeyboardButton(
                    text="📥 Скачать загрузчик", callback_data="getfile"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚩 Сообщить об ошибке", callback_data="support"
                )
            ],
        ]
    )


def get_my_key_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Сбросить устройство (HWID)",
                    callback_data="reset_hwid",
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
        ]
    )


def get_payment_methods_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐️ Telegram Stars", callback_data="pay_stars")],
            [
                InlineKeyboardButton(
                    text="💎 Криптовалюта (Cryptomus)",
                    callback_data="pay_crypto",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💳 Карта (Tribute)",
                    callback_data="pay_tribute",
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
        ]
    )


def get_crypto_payment_menu(
    pay_url: str, payment_uuid: str, price_usd: float
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"💎 Оплатить ${price_usd}", url=pay_url)],
            [
                InlineKeyboardButton(
                    text="🔄 Проверить оплату",
                    callback_data=f"check_crypto:{payment_uuid}",
                )
            ],
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="buy_key")],
        ]
    )


def get_tribute_payment_menu(tribute_url: str, price_rub: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💳 Оплатить {price_rub} RUB", url=tribute_url
                )
            ],
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="buy_key")],
        ]
    )


def get_back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
        ]
    )
