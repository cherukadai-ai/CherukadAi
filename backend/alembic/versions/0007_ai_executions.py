"""AI provider execution audit records.

Revision ID: 0007_ai_executions
Revises: 0006_feature_wiring
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_ai_executions"
down_revision: str | None = "0006_feature_wiring"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid()),
        sa.Column("feature_id", sa.Uuid()),
        sa.Column("workflow_id", sa.Uuid()),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(160), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("usage_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error_code", sa.String(80)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "organisation_id",
        "user_id",
        "project_id",
        "feature_id",
        "workflow_id",
        "provider",
        "status",
    ):
        op.create_index(f"ix_ai_executions_{column}", "ai_executions", [column])


def downgrade() -> None:
    op.drop_table("ai_executions")
