"""organisations, settings, and tenant users

Revision ID: 0003_organisations
Revises: 0002_identity
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_organisations"
down_revision: str | None = "0002_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organisations",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(160), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False), sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(50)), sa.Column("address", sa.Text()), sa.Column("logo", sa.String(1000)),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_organisations"),
    )
    op.create_index("ix_organisations_name", "organisations", ["name"], unique=True)
    op.create_index("ix_organisations_email", "organisations", ["email"])
    op.create_index("ix_organisations_status", "organisations", ["status"])
    op.create_table(
        "organisation_settings",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"), sa.Column("settings_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_organisation_settings"),
        sa.UniqueConstraint("organisation_id", name="uq_organisation_settings_organisation_id"),
    )
    op.create_index("ix_organisation_settings_organisation_id", "organisation_settings", ["organisation_id"])
    op.create_table(
        "organisation_users",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False), sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("permissions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_organisation_users"),
        sa.UniqueConstraint("organisation_id", "email", name="uq_organisation_users_organisation_id"),
    )
    op.create_index("ix_organisation_users_organisation_id", "organisation_users", ["organisation_id"])
    op.create_index("ix_organisation_users_email", "organisation_users", ["email"])


def downgrade() -> None:
    op.drop_table("organisation_users")
    op.drop_table("organisation_settings")
    op.drop_index("ix_organisations_status", table_name="organisations")
    op.drop_index("ix_organisations_email", table_name="organisations")
    op.drop_index("ix_organisations_name", table_name="organisations")
    op.drop_table("organisations")