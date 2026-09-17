"""Interior Design AI Studio projects, assets, jobs, and versions.

Revision ID: 0009_interior_design_studio
Revises: 0008_workflows
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_interior_design_studio"
down_revision: str | None = "0008_workflows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _index(table: str, column: str) -> None:
    op.create_index(f"ix_{table}_{column}", table, [column])


def upgrade() -> None:
    op.create_table(
        "interior_design_projects",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("organisation_id", "name"),
    )
    op.create_table(
        "interior_design_assets",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False), sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False), sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False), sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False), sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["interior_design_projects.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("storage_key"),
    )
    op.create_table(
        "interior_design_ai_jobs",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("organisation_id", sa.Uuid(), nullable=False), sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False), sa.Column("job_type", sa.String(40), nullable=False), sa.Column("status", sa.String(20), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=False), sa.Column("output_data", sa.JSON()), sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["project_id"], ["interior_design_projects.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "interior_design_ai_job_statuses",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("job_id", sa.Uuid(), nullable=False), sa.Column("status", sa.String(20), nullable=False),
        sa.Column("message", sa.String(500)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["interior_design_ai_jobs.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "interior_design_versions",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("organisation_id", sa.Uuid(), nullable=False), sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_asset_id", sa.Uuid(), nullable=False), sa.Column("generated_asset_id", sa.Uuid()), sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False), sa.Column("prompt", sa.Text(), nullable=False), sa.Column("instructions", sa.JSON(), nullable=False),
        sa.Column("workflow", sa.JSON(), nullable=False), sa.Column("model", sa.String(160)), sa.Column("is_saved", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["project_id"], ["interior_design_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_asset_id"], ["interior_design_assets.id"]), sa.ForeignKeyConstraint(["generated_asset_id"], ["interior_design_assets.id"]), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("project_id", "version_number"),
    )
    for table, columns in {
        "interior_design_projects": ("organisation_id",), "interior_design_assets": ("organisation_id", "project_id", "kind"),
        "interior_design_ai_jobs": ("organisation_id", "project_id", "job_type", "status"), "interior_design_ai_job_statuses": ("job_id", "status"),
        "interior_design_versions": ("organisation_id", "project_id", "source_asset_id", "generated_asset_id", "is_saved"),
    }.items():
        for column in columns:
            _index(table, column)


def downgrade() -> None:
    op.drop_table("interior_design_versions")
    op.drop_table("interior_design_ai_job_statuses")
    op.drop_table("interior_design_ai_jobs")
    op.drop_table("interior_design_assets")
    op.drop_table("interior_design_projects")
