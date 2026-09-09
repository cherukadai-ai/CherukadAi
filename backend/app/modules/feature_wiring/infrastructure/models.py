from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FeatureWiringStatus:
    DISABLED = "disabled"
    ENABLED = "enabled"


class FeatureWiring(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "feature_wirings"
    __table_args__ = (UniqueConstraint("organisation_id", "ai_feature_id"),)

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), index=True
    )
    ai_product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_products.id", ondelete="CASCADE"), index=True
    )
    ai_feature_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_features.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default=FeatureWiringStatus.DISABLED, index=True)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FeatureWiringVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "feature_wiring_versions"
    __table_args__ = (UniqueConstraint("wiring_id", "version"),)

    wiring_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feature_wirings.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))