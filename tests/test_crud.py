"""
Tests for license CRUD operations.
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
    """Database session fixture."""
    yield db_session


@pytest.fixture
async def test_user(session):
    """Creates a test user."""
    user = User(telegram_id=987654, username="test_license_user")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


class TestValidateLicense:
    """Tests for license validation."""

    @pytest.mark.asyncio
    async def test_validate_valid_license(self, session, test_user):
        """Validation of an active license."""
        # Create license
        license_obj = License(
            key="valid_key_123",
            hwid=None,
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            owner_id=test_user.telegram_id,
        )
        session.add(license_obj)
        await session.commit()

        # Validate
        is_valid, message, status = await validate_license(
            session, "valid_key_123", "test_hwid"
        )

        assert is_valid is True
        assert status == LicenseStatus.VALID
        assert message == "OK"

    @pytest.mark.asyncio
    async def test_validate_not_found(self, session):
        """Validation of a non-existent license."""
        is_valid, message, status = await validate_license(
            session, "nonexistent_key", "test_hwid"
        )

        assert is_valid is False
        assert status == LicenseStatus.NOT_FOUND
        assert "not found" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_inactive_license(self, session, test_user):
        """Validation of an inactive license."""
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
        assert "blocked" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_expired_license(self, session, test_user):
        """Validation of an expired license."""
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
        assert "expired" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_hwid_lock_first_activation(self, session, test_user):
        """HWID lock — first activation."""
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
        """HWID lock — HWID mismatch."""
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
    """Tests for creating/extending a license."""

    @pytest.mark.asyncio
    async def test_add_new_license(self, session, test_user):
        """Creating a new license."""
        key = await add_license(session, owner_id=test_user.telegram_id, days=30)

        assert key is not None
        assert len(key) == 32  # token_hex(16) = 32 characters

        license_obj = await get_user_license(session, test_user.telegram_id)
        assert license_obj is not None
        assert license_obj.key == key
        assert license_obj.is_active is True

    @pytest.mark.asyncio
    async def test_add_license_extend_existing(self, session, test_user):
        """Extending an existing license."""
        # Create an existing license
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

        # Extend
        new_key = await add_license(session, owner_id=test_user.telegram_id, days=30)

        assert new_key == "existing_key"  # Key did not change

        await session.refresh(license_obj)
        # Term should be increased by approximately 30 days
        expected_expires = initial_expires + timedelta(days=30)
        # Compare with tolerance of 2 seconds (for timezone conversions)
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
        """Reactivation of an expired license."""
        # Create an expired license
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

        # Reactivate
        new_key = await add_license(session, owner_id=test_user.telegram_id, days=30)

        assert new_key == "expired_key"

        await session.refresh(license_obj)
        assert license_obj.is_active is True
        # HWID is preserved on reactivation (not reset anymore)
        assert license_obj.hwid == "old_hwid"
        # New term should be approximately 30 days from now
        expected_expires = datetime.now(timezone.utc) + timedelta(days=30)
        expires_at = license_obj.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        delta = abs((expires_at - expected_expires).total_seconds())
        assert delta < 2


class TestTrialPeriod:
    """Tests for trial period."""

    @pytest.mark.asyncio
    async def test_activate_trial_first_time(self, session, test_user):
        """Activating trial period for the first time."""
        key = await activate_trial_period(session, telegram_id=test_user.telegram_id)

        assert key is not None

        # Check that user is marked as having used trial
        await session.refresh(test_user)
        assert test_user.isUsedTrial is True

        # Check license
        license_obj = await get_user_license(session, test_user.telegram_id)
        assert license_obj is not None
        assert license_obj.key == key

    @pytest.mark.asyncio
    async def test_activate_trial_already_used(self, session, test_user):
        """Repeated attempt to activate trial period."""
        # First time
        test_user.isUsedTrial = True
        await session.commit()

        # Second attempt
        key = await activate_trial_period(session, telegram_id=test_user.telegram_id)

        assert key is None  # Trial already used


class TestResetHWID:
    """Tests for HWID reset."""

    @pytest.mark.asyncio
    async def test_reset_hwid_success(self, session, test_user):
        """Successful HWID reset."""
        # Create license with HWID
        license_obj = License(
            key="test_key",
            hwid="existing_hwid",
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            owner_id=test_user.telegram_id,
        )
        session.add(license_obj)
        await session.commit()

        # Reset
        result = await reset_hwid(session, test_user.telegram_id)

        assert result is True
        await session.refresh(license_obj)
        assert license_obj.hwid is None

    @pytest.mark.asyncio
    async def test_reset_hwid_no_license(self, session, test_user):
        """HWID reset when no license exists."""
        result = await reset_hwid(session, test_user.telegram_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_reset_hwid_already_none(self, session, test_user):
        """HWID reset when already None."""
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
        assert result is False  # Nothing to reset
