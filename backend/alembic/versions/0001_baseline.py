"""baseline: enable required Postgres extensions

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-05

"""
from collections.abc import Sequence

from alembic import op

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    # pgvector is enabled when the first embedding-bearing table is introduced
    # (Interior Design AI phase) — not required for the platform foundation.


def downgrade() -> None:
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
