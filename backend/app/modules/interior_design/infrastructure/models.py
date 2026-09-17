"""Tenant-scoped Interior Design AI Studio persistence models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InteriorDesignProject(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interior_design_projects"
    __table_args__ = (UniqueConstraint("organisation_id", "name"),)

    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(200))


class DesignAsset(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "interior_design_assets"

    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interior_design_projects.id", ondelete="CASCADE"), index=True)
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    original_filename: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interior_design_ai_jobs"

    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interior_design_projects.id", ondelete="CASCADE"), index=True)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    job_type: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    output_data: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AIJobStatus(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "interior_design_ai_job_statuses"

    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interior_design_ai_jobs.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DesignVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interior_design_versions"
    __table_args__ = (UniqueConstraint("project_id", "version_number"),)

    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interior_design_projects.id", ondelete="CASCADE"), index=True)
    source_asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interior_design_assets.id"), index=True)
    generated_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("interior_design_assets.id"), index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    prompt: Mapped[str] = mapped_column(Text)
    instructions: Mapped[dict] = mapped_column(JSON, default=dict)
    workflow: Mapped[dict] = mapped_column(JSON, default=dict)
    model: Mapped[str | None] = mapped_column(String(160))
    is_saved: Mapped[bool] = mapped_column(default=False, index=True)
