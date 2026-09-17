"""Alembic migration environment.

Uses a synchronous psycopg driver for migrations (independent of the app's async
runtime engine) and imports all module ORM models so autogenerate can see them.
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.infrastructure.db.base import Base

# Import model modules here as they are added, e.g.:
from app.modules.identity.infrastructure import models as identity_models  # noqa: F401
from app.modules.organisations.infrastructure import models as organisation_models  # noqa: F401
from app.modules.ai.infrastructure import models as ai_models  # noqa: F401
from app.modules.interior_design.infrastructure import models as interior_design_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_database_url() -> str:
    url = get_settings().database_url
    return url.replace("postgresql+asyncpg", "postgresql+psycopg")


def run_migrations_offline() -> None:
    url = _sync_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _sync_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
