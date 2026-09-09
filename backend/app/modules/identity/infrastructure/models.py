"""SQLAlchemy ORM models for the identity module (platform-level, not tenant-scoped)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.identity.domain.models import AdminStatus


class PlatformAdminModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "platform_admins"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    # Argon2id hash only. Plaintext passwords are never persisted.
    password_hash: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=AdminStatus.ACTIVE.value)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlatformSettingModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Platform-wide key/value settings (e.g. the initial-setup completion marker).

    The unique `key` doubles as the race-safe, permanent setup gate.
    """

    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
