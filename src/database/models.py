# Copyright (c) 2026 Yauheni Sytsevich. All Rights Reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited.
# Proprietary and confidential.

import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.db import Base


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False, index=True
    )

    username: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )

    registration_date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    isUsedTrial: Mapped[bool] = mapped_column(Boolean, default=False)
    # Связь с лицензиями (один ко многим)
    licenses: Mapped[list["License"]] = relationship(back_populates="owner")

    cryptocloud_payments: Mapped[list["CryptocloudPayments"]] = relationship(
        back_populates="payer"
    )


class License(Base):
    __tablename__ = "licenses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    hwid: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # === Новое поле: Связь с User ===
    # nullable=True: лицензия может не принадлежать никому
    owner_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), nullable=True
    )

    # ORM связь для удобства (license.owner вернет объект User)
    owner: Mapped["User"] = relationship(back_populates="licenses")


class CryptocloudPayments(Base):
    __tablename__ = "cryptocloud_payments"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    check_id: Mapped[str] = mapped_column(String(64))
    isPaid: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    payer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), nullable=True
    )

    payer: Mapped["User"] = relationship(back_populates="cryptocloud_payments")
