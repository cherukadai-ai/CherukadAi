"""Organisation-level AI feature wiring.

Revision ID: 0006_feature_wiring
Revises: 0005_ai_registry
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_feature_wiring"
down_revision: str | None = "0005_ai_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feature_wirings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("ai_product_id", sa.Uuid(), nullable=False),
        sa.Column("ai_feature_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="disabled"),
        sa.Column("configuration", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ai_product_id"], ["ai_products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ai_feature_id"], ["ai_features.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organisation_id", "ai_feature_id"),
    )
    for column in ("organisation_id", "ai_product_id", "ai_feature_id", "status"):
        op.create_index(f"ix_feature_wirings_{column}", "feature_wirings", [column])
    op.create_table(
        "feature_wiring_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("wiring_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["wiring_id"], ["feature_wirings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("wiring_id", "version"),
    )
    op.create_index("ix_feature_wiring_versions_wiring_id", "feature_wiring_versions", ["wiring_id"])


def downgrade() -> None:
    op.drop_table("feature_wiring_versions")
    op.drop_table("feature_wirings")