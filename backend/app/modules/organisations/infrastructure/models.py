"""Relational models for tenant ownership and organisation administration."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OrganisationStatus:
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class OrganisationModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organisations"

    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)
    logo: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default=OrganisationStatus.ACTIVE, index=True)


class OrganisationSettingsModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organisation_settings"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), unique=True, index=True
    )
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    settings_json: Mapped[str] = mapped_column(Text, default="{}")


class OrganisationUserModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organisation_users"
    __table_args__ = (UniqueConstraint("organisation_id", "email"),)

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(320), index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=OrganisationStatus.ACTIVE)
    role: Mapped[str] = mapped_column(String(40), default="USER", index=True)
    force_password_change: Mapped[bool] = mapped_column(default=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrganisationLoginEventModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "organisation_login_events"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisation_users.id", ondelete="CASCADE"), index=True)
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), index=True)
    succeeded: Mapped[bool] = mapped_column(default=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    reason: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(__import__("datetime").timezone.utc))