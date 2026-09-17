from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WorkflowStatus:
    DRAFT = "draft"
    VALIDATED = "validated"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class WorkflowStepType:
    PROMPT = "prompt"
    AI_AGENT = "ai_agent"
    AI_PROVIDER = "ai_provider"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    STORAGE = "storage"
    CONDITIONAL = "conditional"


class WorkflowExecutionStatus:
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class WorkflowExecutionStepStatus:
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class Workflow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflows"
    __table_args__ = (UniqueConstraint("organisation_id", "slug"),)

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(20), default=WorkflowStatus.DRAFT, index=True)
    current_version: Mapped[int] = mapped_column(Integer, default=0)
    published_version: Mapped[int | None] = mapped_column(Integer)


class WorkflowVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_versions"
    __table_args__ = (UniqueConstraint("workflow_id", "version"),)

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=WorkflowStatus.DRAFT, index=True)
    definition: Mapped[dict] = mapped_column(JSON, default=dict)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkflowStep(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workflow_steps"
    __table_args__ = (UniqueConstraint("workflow_version_id", "key"),)

    workflow_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_versions.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(30))
    depends_on: Mapped[list] = mapped_column(JSON, default=list)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    position: Mapped[int] = mapped_column(Integer, default=0)


class WorkflowExecution(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workflow_executions"

    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), index=True)
    workflow_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_versions.id"), index=True
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"), index=True)
    status: Mapped[str] = mapped_column(
        String(20), default=WorkflowExecutionStatus.RUNNING, index=True
    )
    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    output_data: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkflowExecutionStep(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workflow_execution_steps"

    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_executions.id", ondelete="CASCADE"), index=True
    )
    workflow_step_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_steps.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=WorkflowExecutionStepStatus.PENDING)
    input_data: Mapped[dict | None] = mapped_column(JSON)
    output_data: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
