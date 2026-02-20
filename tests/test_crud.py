"""
Тесты для CRUD операций с лицензиями.
"""

import pytest
from datetime import datetime, timedelta, timezone

from src.database.crud import (
    activate_trial_period,
    add_license,
    get_user_license,
    reset_hwid,
    validate_license,
    LicenseStatus,
)
from src.database.models import License, User


@pytest.fixture
async def session(db_session):
    """Фикстура сессии БД."""
    yield db_session


@pytest.fixture
async def test_user(session):
    """Создаёт тестового пользователя."""
    user = User(telegram_id=987654, username="test_license_user")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


class TestValidateLicense:
    """Тесты для валидации лицензии."""

    @pytest.mark.asyncio
    async def test_validate_valid_license(self, session, test_user):
        """Валидация активной лицензии."""
        # Создаём лицензию
        license_obj = License(
            key="valid_key_123",
            hwid=None,
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            owner_id=test_user.telegram_id,
        )
        session.add(license_obj)
        await session.commit()

        # Валидируем
        is_valid, message, status = await validate_license(
            session, "valid_key_123", "test_hwid"
        )

        assert is_valid is True
        assert status == LicenseStatus.VALID
        assert message == "OK"

    @pytest.mark.asyncio
    async def test_validate_not_found(self, session):
        """Валидация несуществующей лицензии."""
        is_valid, message, status = await validate_license(
            session, "nonexistent_key", "test_hwid"
        )

        assert is_valid is False
        assert status == LicenseStatus.NOT_FOUND
        assert "не найден" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_inactive_license(self, session, test_user):
        """Валидация неактивной лицензии."""
        license_obj = License(
            key="inactive_key",
            hwid=None,
            is_active=False,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            owner_id=test_user.telegram_id,
        )
        session.add(license_obj)
        await session.commit()

        is_valid, message, status = await validate_license(
            session, "inactive_key", "test_hwid"
        )

        assert is_valid is False
        assert status == LicenseStatus.INACTIVE
        assert "заблокирован" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_expired_license(self, session, test_user):
        """Валидация просроченной лицензии."""
        license_obj = License(
            key="expired_key",
            hwid=None,
            is_active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            owner_id=test_user.telegram_id,
        )
        session.add(license_obj)
        await session.commit()

        is_valid, message, status = await validate_license(
            session, "expired_key", "test_hwid"
        )

        assert is_valid is False
        assert status == LicenseStatus.EXPIRED
        assert "истек" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_hwid_lock_first_activation(self, session, test_user):
        """HWID lock — первая активация."""
        license_obj = License(
            key="hwid_test_key",
            hwid=None,
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            owner_id=test_user.telegram_id,
        )
        session.add(license_obj)
        await session.commit()

        is_valid, message, status = await validate_license(
            session, "hwid_test_key", "first_hwid"
        )

        assert is_valid is True
        await session.refresh(license_obj)
        assert license_obj.hwid == "first_hwid"

    @pytest.mark.asyncio
    async def test_validate_hwid_mismatch(self, session, test_user):
        """HWID lock — несовпадение HWID."""
        license_obj = License(
            key="hwid_locked_key",
            hwid="existing_hwid",
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            owner_id=test_user.telegram_id,
        )
        session.add(license_obj)
        await session.commit()

        is_valid, message, status = await validate_license(
            session, "hwid_locked_key", "different_hwid"
        )

        assert is_valid is False
        assert status == LicenseStatus.HWID_MISMATCH
        assert "hwid" in message.lower()


class TestAddLicense:
    """Тесты для создания/продления лицензии."""

    @pytest.mark.asyncio
    async def test_add_new_license(self, session, test_user):
        """Создание новой лицензии."""
        key = await add_license(session, owner_id=test_user.telegram_id, days=30)

        assert key is not None
        assert len(key) == 32  # token_hex(16) = 32 символа

        license_obj = await get_user_license(session, test_user.telegram_id)
        assert license_obj is not None
        assert license_obj.key == key
        assert license_obj.is_active is True

    @pytest.mark.asyncio
    async def test_add_license_extend_existing(self, session, test_user):
        """Продление существующей лицензии."""
        # Создаём существующую лицензию
        initial_expires = datetime.now(timezone.utc) + timedelta(days=30)
        license_obj = License(
            key="existing_key",
            hwid=None,
            is_active=True,
            expires_at=initial_expires,
            owner_id=test_user.telegram_id,
        )
        session.add(license_obj)
        await session.commit()

        # Продлеваем
        new_key = await add_license(session, owner_id=test_user.telegram_id, days=30)

        assert new_key == "existing_key"  # Ключ не изменился

        await session.refresh(license_obj)
        # Срок должен увеличиться примерно на 30 дней
        expected_expires = initial_expires + timedelta(days=30)
        # Сравниваем с допуском в 2 секунды (для timezone конверсий)
        delta = abs(
            (
                license_obj.expires_at.replace(tzinfo=timezone.utc)
                if license_obj.expires_at.tzinfo is None
                else license_obj.expires_at
            )
            - expected_expires
        ).total_seconds()
        assert delta < 2

    @pytest.mark.asyncio
    async def test_add_license_reactivate_expired(self, session, test_user):
        """Реактивация просроченной лицензии."""
        # Создаём просроченную лицензию
        expired_expires = datetime.now(timezone.utc) - timedelta(days=1)
        license_obj = License(
            key="expired_key",
            hwid="old_hwid",
            is_active=True,
            expires_at=expired_expires,
            owner_id=test_user.telegram_id,
        )
        session.add(license_obj)
        await session.commit()

        # Реактивируем
        new_key = await add_license(session, owner_id=test_user.telegram_id, days=30)

        assert new_key == "expired_key"

        await session.refresh(license_obj)
        assert license_obj.is_active is True
        assert license_obj.hwid is None  # HWID сброшен
        # Новый срок должен быть примерно через 30 дней от сейчас
        expected_expires = datetime.now(timezone.utc) + timedelta(days=30)
        expires_at = license_obj.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        delta = abs((expires_at - expected_expires).total_seconds())
        assert delta < 2


class TestTrialPeriod:
    """Тесты для пробного периода."""

    @pytest.mark.asyncio
    async def test_activate_trial_first_time(self, session, test_user):
        """Активация пробного периода впервые."""
        key = await activate_trial_period(session, telegram_id=test_user.telegram_id)

        assert key is not None

        # Проверяем, что пользователь помечен как использовавший trial
        await session.refresh(test_user)
        assert test_user.isUsedTrial is True

        # Проверяем лицензию
        license_obj = await get_user_license(session, test_user.telegram_id)
        assert license_obj is not None
        assert license_obj.key == key

    @pytest.mark.asyncio
    async def test_activate_trial_already_used(self, session, test_user):
        """Повторная попытка активации пробного периода."""
        # Первый раз
        test_user.isUsedTrial = True
        await session.commit()

        # Вторая попытка
        key = await activate_trial_period(session, telegram_id=test_user.telegram_id)

        assert key is None  # Trial уже использован


class TestResetHWID:
    """Тесты для сброса HWID."""

    @pytest.mark.asyncio
    async def test_reset_hwid_success(self, session, test_user):
        """Успешный сброс HWID."""
        # Создаём лицензию с HWID
        license_obj = License(
            key="test_key",
            hwid="existing_hwid",
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            owner_id=test_user.telegram_id,
        )
        session.add(license_obj)
        await session.commit()

        # Сбрасываем
        result = await reset_hwid(session, test_user.telegram_id)

        assert result is True
        await session.refresh(license_obj)
        assert license_obj.hwid is None

    @pytest.mark.asyncio
    async def test_reset_hwid_no_license(self, session, test_user):
        """Сброс HWID при отсутствии лицензии."""
        result = await reset_hwid(session, test_user.telegram_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_reset_hwid_already_none(self, session, test_user):
        """Сброс HWID который уже None."""
        license_obj = License(
            key="test_key",
            hwid=None,
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            owner_id=test_user.telegram_id,
        )
        session.add(license_obj)
        await session.commit()

        result = await reset_hwid(session, test_user.telegram_id)
        assert result is False  # Не было что сбрасывать
