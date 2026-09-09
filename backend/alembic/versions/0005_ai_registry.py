"""Central AI product, feature, agent, and model registry.

Revision ID: 0005_ai_registry
Revises: 0004_phase5_identity_rbac
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_ai_registry"
down_revision: str | None = "0004_phase5_identity_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _common_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("configuration", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table("ai_products", *_common_columns(), sa.PrimaryKeyConstraint("id", name="pk_ai_products"))
    op.create_index("ix_ai_products_code", "ai_products", ["code"], unique=True)
    op.create_index("ix_ai_products_status", "ai_products", ["status"])

    for table in ("ai_features", "ai_agents", "ai_models"):
        columns = _common_columns()
        columns.append(sa.Column("product_id", sa.Uuid(), nullable=False))
        if table == "ai_models":
            columns.append(sa.Column("provider", sa.String(120), nullable=False))
        op.create_table(
            table,
            *columns,
            sa.ForeignKeyConstraint(["product_id"], ["ai_products.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
            sa.UniqueConstraint("product_id", "code", name=f"uq_{table}_product_id"),
        )
        op.create_index(f"ix_{table}_code", table, ["code"])
        op.create_index(f"ix_{table}_product_id", table, ["product_id"])
        op.create_index(f"ix_{table}_status", table, ["status"])


def downgrade() -> None:
    for table in ("ai_models", "ai_agents", "ai_features"):
        op.drop_table(table)
    op.drop_index("ix_ai_products_status", table_name="ai_products")
    op.drop_index("ix_ai_products_code", table_name="ai_products")
    op.drop_table("ai_products")