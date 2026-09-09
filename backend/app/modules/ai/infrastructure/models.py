"""Persistence models for the platform-wide AI registry."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AIRegistryStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"


class AIProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_products"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=AIRegistryStatus.ACTIVE, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)


class AIFeature(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_features"
    __table_args__ = (UniqueConstraint("product_id", "code"),)

    code: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_products.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default=AIRegistryStatus.ACTIVE, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)


class AIAgent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_agents"
    __table_args__ = (UniqueConstraint("product_id", "code"),)

    code: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_products.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default=AIRegistryStatus.ACTIVE, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)


class AIModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_models"
    __table_args__ = (UniqueConstraint("product_id", "code"),)

    code: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(200))
    provider: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_products.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default=AIRegistryStatus.ACTIVE, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)


class AIExecution(UUIDPrimaryKeyMixin, Base):
    """Audit record for one provider-independent AI request."""

    __tablename__ = "ai_executions"

    organisation_id: Mapped[uuid.UUID] = mapped_column(index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    feature_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(30), index=True)
    duration_ms: Mapped[int] = mapped_column(Integer)
    usage_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))