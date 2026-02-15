import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import CryptocloudPayments, License, User


async def validate_license(db: AsyncSession, key: str, hwid: str) -> tuple[bool, str]:
    stmt = select(License).where(License.key == key)
    result = await db.execute(stmt)
    license_obj = result.scalar_one_or_none()

    if not license_obj:
        return False, "Ключ не найден"
    if not license_obj.is_active:
        return False, "Ключ заблокирован"
    if license_obj.expires_at < datetime.now(timezone.utc):
        return False, "Срок действия подписки истек"

    # === LOGIC: HWID LOCK ===
    if license_obj.hwid is None:
        license_obj.hwid = hwid
        await db.commit()
    elif license_obj.hwid != hwid:
        return False, "HWID не совпадает (Привязка к другому ПК)"

    return True, "OK"


async def get_or_create_user(
    db: AsyncSession, telegram_id: int, username: str | None
) -> bool:
    """
    Возвращает True, если пользователь уже был, False если новый.
    """
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        return True  # Уже был

    # Создаем нового
    user = User(telegram_id=telegram_id, username=username)
    db.add(user)
    await db.commit()
    return False  # Новый


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
    stmt = select(License).where(License.owner_id == owner_id)
    result = await db.execute(stmt)
    existing_license = result.scalar_one_or_none()

    # Текущее время в UTC
    now = datetime.now(timezone.utc)
    # Период продления
    duration = timedelta(days=days)

    if existing_license:
        # Если лицензия существует, проверяем, активна ли она по времени
        if existing_license.expires_at > now:
            # Сценарий: Подписка еще действует -> добавляем дни к текущему сроку
            existing_license.expires_at += duration
        else:
            # Сценарий: Подписка истекла -> считаем срок от текущего момента
            existing_license.expires_at = now + duration

        existing_license.is_active = True
        existing_license.hwid = None  # Сброс HWID при продлении
        key = existing_license.key
    else:
        # Создаем новую лицензию
        key = secrets.token_hex(16)
        new_expires = now + duration

        new_license = License(
            key=key, expires_at=new_expires, is_active=True, owner_id=owner_id
        )
        db.add(new_license)

    await db.commit()
    return key


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
