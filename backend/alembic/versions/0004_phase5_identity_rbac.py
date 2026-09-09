"""Phase 5 organisation credentials, RBAC metadata, and login history.

Revision ID: 0004_phase5_identity_rbac
Revises: 0003_organisations
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "0004_phase5_identity_rbac"
down_revision: str | None = "0003_organisations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organisation_users", sa.Column("role", sa.String(40), nullable=False, server_default="USER"))
    op.add_column("organisation_users", sa.Column("force_password_change", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("organisation_users", sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("organisation_users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("organisation_users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_organisation_users_role", "organisation_users", ["role"])
    op.create_table(
        "organisation_login_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organisation_id", sa.Uuid(), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ip_address", sa.String(64)), sa.Column("user_agent", sa.String(500)),
        sa.Column("reason", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["organisation_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_organisation_login_events"),
    )
    op.create_index("ix_organisation_login_events_user_id", "organisation_login_events", ["user_id"])
    op.create_index("ix_organisation_login_events_organisation_id", "organisation_login_events", ["organisation_id"])


def downgrade() -> None:
    op.drop_table("organisation_login_events")
    op.drop_index("ix_organisation_users_role", table_name="organisation_users")
    for column in ("last_login_at", "locked_until", "failed_login_attempts", "force_password_change", "role"):
        op.drop_column("organisation_users", column)