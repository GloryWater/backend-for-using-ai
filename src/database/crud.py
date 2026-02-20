import logging
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import CryptocloudPayments, License, User

logger = logging.getLogger(__name__)


class LicenseStatus(str, Enum):
    VALID = "valid"
    NOT_FOUND = "not_found"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    HWID_MISMATCH = "hwid_mismatch"


async def validate_license(
    db: AsyncSession, key: str, hwid: str
) -> tuple[bool, str, LicenseStatus]:
    """
    Валидация лицензии с детальной информацией о статусе.

    Returns:
        tuple: (is_valid, message, status_enum)
    """
    try:
        stmt = select(License).where(License.key == key)
        result = await db.execute(stmt)
        license_obj = result.scalar_one_or_none()

        if not license_obj:
            logger.warning(
                "License not found: key=%s***", key[-4:] if len(key) > 4 else key
            )
            return False, "Ключ не найден", LicenseStatus.NOT_FOUND

        if not license_obj.is_active:
            logger.warning(
                "License is inactive: key=%s***", key[-4:] if len(key) > 4 else key
            )
            return False, "Ключ заблокирован", LicenseStatus.INACTIVE

        now = datetime.now(timezone.utc)
        expires_at = license_obj.expires_at
        # Приводим к timezone-aware если нужно
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            logger.warning(
                "License expired: key=%s***, expired_at=%s",
                key[-4:] if len(key) > 4 else key,
                license_obj.expires_at,
            )
            return False, "Срок действия подписки истек", LicenseStatus.EXPIRED

        # === LOGIC: HWID LOCK ===
        if license_obj.hwid is None:
            license_obj.hwid = hwid
            await db.commit()
            logger.info(
                "License activated: key=%s***, hwid=%s",
                key[-4:] if len(key) > 4 else key,
                hwid[:8],
            )
        elif license_obj.hwid != hwid:
            logger.warning(
                "HWID mismatch: key=%s***, expected=%s***, got=%s***",
                key[-4:] if len(key) > 4 else key,
                license_obj.hwid[:8],
                hwid[:8],
            )
            return (
                False,
                "HWID не совпадает (Привязка к другому ПК)",
                LicenseStatus.HWID_MISMATCH,
            )

        return True, "OK", LicenseStatus.VALID

    except SQLAlchemyError as e:
        logger.exception("Database error during license validation: %s", e)
        return False, "Ошибка базы данных", LicenseStatus.NOT_FOUND


async def get_or_create_user(
    db: AsyncSession, telegram_id: int, username: str | None
) -> bool:
    """
    Возвращает True, если пользователь уже был, False если новый.
    """
    try:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            return True  # Уже был

        # Создаем нового
        user = User(telegram_id=telegram_id, username=username)
        db.add(user)
        await db.commit()
        logger.info(
            "New user registered: telegram_id=%d, username=%s", telegram_id, username
        )
        return False  # Новый

    except SQLAlchemyError as e:
        logger.exception("Database error during user creation: %s", e)
        raise


async def get_user_license(db: AsyncSession, owner_id: int) -> License | None:
    stmt = select(License).where(License.owner_id == owner_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def reset_hwid(db: AsyncSession, telegram_id: int) -> bool:
    """Сбрасывает HWID у лицензии пользователя."""
    lic = await get_user_license(db, telegram_id)
    if lic and lic.hwid is not None:
        lic.hwid = None
        await db.commit()
        return True
    return False


async def add_license(db: AsyncSession, owner_id: int, days: int = 30) -> str:
    """Создает или продлевает лицензию пользователя."""
    try:
        stmt = select(License).where(License.owner_id == owner_id)
        result = await db.execute(stmt)
        existing_license = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        duration = timedelta(days=days)

        if existing_license:
            # Приводим expires_at к timezone-aware если нужно
            existing_expires = existing_license.expires_at
            if existing_expires.tzinfo is None:
                existing_expires = existing_expires.replace(tzinfo=timezone.utc)

            if existing_expires > now:
                existing_license.expires_at = existing_expires + duration
                logger.info(
                    "License extended: owner_id=%d, new_expires=%s, added_days=%d",
                    owner_id,
                    existing_license.expires_at,
                    days,
                )
            else:
                existing_license.expires_at = now + duration
                logger.info(
                    "License reactivated: owner_id=%d, new_expires=%s",
                    owner_id,
                    existing_license.expires_at,
                )

            existing_license.is_active = True
            existing_license.hwid = None
            key = existing_license.key
        else:
            key = secrets.token_hex(16)
            new_expires = now + duration

            new_license = License(
                key=key,
                expires_at=new_expires,
                is_active=True,
                owner_id=owner_id,
            )
            db.add(new_license)
            logger.info(
                "New license created: owner_id=%d, key=%s***, expires=%s",
                owner_id,
                key[-4:],
                new_expires,
            )

        await db.commit()
        return key

    except SQLAlchemyError as e:
        logger.exception("Database error during license creation: %s", e)
        raise


async def activate_trial_period(db: AsyncSession, telegram_id: int) -> str | None:
    """
    Пытается активировать пробный период.
    Возвращает ключ, если успешно.
    Возвращает None, если пробный период уже был использован.
    """
    # 1. Получаем пользователя
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        # Если пользователя вдруг нет (странно, но возможно), создаем заглушку или выходим
        return None

    # 2. Проверяем, брал ли он уже пробник
    if user.isUsedTrial:
        return None

    # 3. Активируем пробник
    # Помечаем, что пробник использован
    user.isUsedTrial = True

    # Создаем/обновляем лицензию на 7 дней (используем существующую логику add_license)
    key = await add_license(db, owner_id=telegram_id, days=7)

    # Сохраняем изменения в User (add_license делает commit, но на всякий случай убедимся)
    await db.commit()

    return key


async def add_payment(
    session: AsyncSession, check_id: str, payer_id: int | None
) -> CryptocloudPayments:
    new_payment = CryptocloudPayments(
        check_id=check_id, payer_id=payer_id, isPaid=False
    )
    session.add(new_payment)
    await session.commit()
    await session.refresh(new_payment)
    return new_payment


async def set_payment_success_and_get_user(
    session: AsyncSession, check_id: str
) -> int | None:
    stmt = (
        update(CryptocloudPayments)
        .where(CryptocloudPayments.check_id == check_id)
        .values(isPaid=True)
        .returning(CryptocloudPayments.payer_id)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar()
