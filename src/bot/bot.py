# Copyright (c) 2026 Yauheni Sytsevich. All Rights Reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited.
# Proprietary and confidential.

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timezone

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from src.bot.keyboards import (
    get_back_menu,
    get_crypto_payment_menu,
    get_main_menu,
    get_my_key_menu,
    get_payment_methods_menu,
    get_tribute_payment_menu,
)
from src.database.crud import (
    activate_trial_period,
    add_license,
    add_payment,
    get_or_create_user,
    get_user_license,
    reset_hwid,
)
from src.database.db import AsyncSessionLocal
from src.services.cryptocloud import check_invoice_status, create_invoice

logger = logging.getLogger(__name__)

# ── конфигурация ──────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
FILE_URL = "https://glorysyntax.live/static/loader.lua"
TRIBUTE_URL = "https://t.me/tribute/app?startapp=sMtV"
PRICE_STARS = 300
PRICE_RUB = 300
PRICE_USD = 3.5

dp = Dispatcher()


# ── главное меню ──────────────────────────────────────────────


async def show_main_menu(message: Message, *, is_edit: bool = False) -> None:
    """Показать / обновить главное меню."""
    text = "🏠 <b>Главное меню</b>\nВыберите действие:"
    if is_edit:
        await message.edit_text(text, reply_markup=get_main_menu())
    else:
        await message.answer(text, reply_markup=get_main_menu())


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    telegram_id = message.from_user.id
    username = message.from_user.username

    async with AsyncSessionLocal() as session:
        user_existed = await get_or_create_user(session, telegram_id, username)

    if user_existed:
        greeting = f"С возвращением, {message.from_user.full_name}!"
    else:
        greeting = (
            f"Привет, {message.from_user.full_name}!\n"
            "✅ Вы успешно зарегистрированы в системе."
        )

    await message.answer(greeting)
    await show_main_menu(message)


@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery) -> None:
    await show_main_menu(callback.message, is_edit=True)
    await callback.answer()


# ── скачать загрузчик ─────────────────────────────────────────


@dp.callback_query(F.data == "getfile")
async def cb_get_file(callback: CallbackQuery) -> None:
    async with aiohttp.ClientSession() as http:
        try:
            async with http.get(FILE_URL) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    doc = BufferedInputFile(content, filename="loader.lua")
                    await callback.message.answer_document(
                        document=doc,
                        caption="Вот актуальная версия скрипта.",
                    )
                else:
                    await callback.message.answer(
                        f"Не удалось скачать файл. Код ошибки: {resp.status}"
                    )
        except Exception:
            logger.exception("Ошибка при скачивании файла")
            await callback.message.answer("Произошла ошибка при скачивании файла.")
    await callback.answer()


# ── мой ключ ──────────────────────────────────────────────────


@dp.callback_query(F.data == "my_key")
async def cb_my_key(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        lic = await get_user_license(session, callback.from_user.id)

    if not lic:
        await callback.answer("У вас ещё нет лицензии.", show_alert=True)
        return

    is_expired = lic.expires_at < datetime.now(timezone.utc)
    status_emoji = "🔴" if is_expired else "🟢"
    status_text = "ИСТЕКЛА" if is_expired else "АКТИВНА"
    hwid_text = "Привязан" if lic.hwid else "Не привязан"

    text = (
        "🔑 <b>Информация о лицензии</b>\n\n"
        f"<b>Ключ:</b> <code>{lic.key}</code>\n"
        f"<b>Срок:</b> до {lic.expires_at.strftime('%d.%m.%Y %H:%M UTC')}\n"
        f"<b>Статус:</b> {status_emoji} {status_text}\n"
        f"<b>HWID:</b> {hwid_text}"
    )

    await callback.message.edit_text(text, reply_markup=get_my_key_menu())
    await callback.answer()


@dp.callback_query(F.data == "reset_hwid")
async def cb_reset_hwid(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        success = await reset_hwid(session, callback.from_user.id)

    if success:
        await callback.answer("✅ HWID успешно сброшен!", show_alert=True)
        # обновляем экран «Мой ключ»
        await cb_my_key(callback)
    else:
        await callback.answer("❌ Ошибка или HWID не был привязан.", show_alert=True)


# ── пробная версия ────────────────────────────────────────────


@dp.callback_query(F.data == "get_trial")
async def cb_get_trial(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        key = await activate_trial_period(session, callback.from_user.id)

    if key:
        await callback.message.edit_text(
            "🔥 <b>Пробная версия активирована!</b>\n\n"
            f"Вам выдана лицензия на <b>7 дней</b>.\n"
            f"Ваш ключ: <code>{key}</code>\n\n"
            "Он также доступен в разделе «Мой ключ».",
            reply_markup=get_back_menu(),
        )
    else:
        await callback.answer("❌ Вы уже использовали пробную версию.", show_alert=True)


# ── покупка ───────────────────────────────────────────────────


@dp.callback_query(F.data == "buy_key")
async def cb_buy_key(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "💳 <b>Выберите метод оплаты:</b>\n"
        "Лицензия выдаётся на 30 дней.\n"
        f"Стоимость составляет <b>{PRICE_RUB} RUB</b>.\n"
        "Стоимость указана без учёта комиссий сервисов.",
        reply_markup=get_payment_methods_menu(),
    )
    await callback.answer()


# ── Telegram Stars ────────────────────────────────────────────


@dp.callback_query(F.data == "pay_stars")
async def cb_pay_stars(callback: CallbackQuery) -> None:
    await callback.message.answer_invoice(
        title="Лицензия AdManager (30 дней)",
        description="Доступ к скрипту редактирования объявлений.",
        payload="license_30_days",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Лицензия", amount=PRICE_STARS)],
        start_parameter="buy_license",
    )
    await callback.answer()


@dp.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@dp.message(F.successful_payment)
async def success_payment_handler(message: Message) -> None:
    if message.successful_payment.invoice_payload != "license_30_days":
        return

    async with AsyncSessionLocal() as session:
        key = await add_license(session, owner_id=message.from_user.id, days=30)

    await message.answer(
        "✅ <b>Оплата прошла успешно!</b>\n\n"
        f"Твой ключ: <code>{key}</code>\n"
        "Он также доступен в меню «Мой ключ».",
    )
    await show_main_menu(message)


# ── Криптовалюта (CryptoCloud) ────────────────────────────────


@dp.callback_query(F.data == "pay_crypto")
async def cb_pay_crypto(callback: CallbackQuery) -> None:
    telegram_id = callback.from_user.id
    order_id = f"{telegram_id}_{int(time.time())}"

    await callback.message.edit_text("⏳ Генерирую ссылку на оплату...")

    invoice = await create_invoice(amount=PRICE_USD, order_id=order_id, currency="USD")
    if not invoice:
        await callback.message.edit_text(
            "❌ Не удалось создать счёт. Попробуйте позже.",
            reply_markup=get_back_menu(),
        )
        return

    pay_url = invoice["url"]
    payment_uuid = invoice["uuid"]

    async with AsyncSessionLocal() as session:
        try:
            await add_payment(session, payment_uuid, telegram_id)
        except Exception:
            logger.exception("Ошибка при сохранении платежа %s", payment_uuid)

    await callback.message.edit_text(
        "<b>Оплата криптовалютой</b>\n\n"
        f"Сумма: <b>{PRICE_USD} USD</b>\n"
        "Нажмите кнопку ниже для оплаты.\n"
        "После оплаты нажмите «Проверить оплату».",
        reply_markup=get_crypto_payment_menu(pay_url, payment_uuid, PRICE_USD),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("check_crypto:"))
async def cb_check_crypto(callback: CallbackQuery) -> None:
    payment_uuid = callback.data.split(":", maxsplit=1)[1]

    is_paid = await check_invoice_status(payment_uuid)
    if not is_paid:
        await callback.answer(
            "❌ Оплата ещё не подтверждена. Попробуйте чуть позже.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:
        key = await add_license(session, owner_id=callback.from_user.id, days=30)

    await callback.message.edit_text(
        "✅ <b>Оплата прошла успешно!</b>\n\n" f"Твой ключ: <code>{key}</code>",
        reply_markup=get_back_menu(),
    )
    await callback.answer()


# ── Tribute (карта) ───────────────────────────────────────────


@dp.callback_query(F.data == "pay_tribute")
async def cb_pay_tribute(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "<b>Оплата банковской картой (Tribute)</b>\n\n"
        f"Сумма: <b>{PRICE_RUB} RUB</b>\n"
        "Нажмите кнопку ниже, чтобы перейти к оплате.\n"
        "Лицензия активируется автоматически после успешного платежа.",
        reply_markup=get_tribute_payment_menu(TRIBUTE_URL, PRICE_RUB),
    )
    await callback.answer()


# ── поддержка ─────────────────────────────────────────────────


@dp.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "<b>Нашли ошибку?</b>\n\n" "Свяжитесь с разработчиком:\n" "@cnn_helper_support",
        reply_markup=get_back_menu(),
    )
    await callback.answer()


# ── запуск ────────────────────────────────────────────────────


async def main() -> None:
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN не задан — завершаю работу")
        sys.exit(1)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
