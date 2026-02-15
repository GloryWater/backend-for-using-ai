import logging

from aiogram import Bot

logger = logging.getLogger(__name__)


class NotificationService:
    """Отправка уведомлений пользователям через Telegram."""

    def __init__(self, bot: Bot):
        self._bot = bot

    async def send_license_issued(self, user_id: int, key: str) -> None:
        """Уведомляет пользователя об успешной оплате и выдаче ключа."""
        try:
            await self._bot.send_message(
                chat_id=user_id,
                text=(
                    f"✅ <b>Оплата прошла успешно!</b>\n\n"
                    f"Ваш ключ: <code>{key}</code>\n"
                    f"Спасибо за покупку!"
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error("Failed to notify user %s: %s", user_id, e)

    async def close(self) -> None:
        await self._bot.session.close()
