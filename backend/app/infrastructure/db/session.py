"""Async SQLAlchemy engine/session management.

`get_db_session` is the plain FastAPI dependency for unscoped access (platform/
Super-Admin routes). `get_tenant_db_session` additionally sets the Postgres GUCs
consumed by Row-Level Security policies, from the *verified* TenantContext only.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.domain.base import TenantContext

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(), expire_on_commit=False, autoflush=False
        )
    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def get_tenant_db_session(tenant: TenantContext) -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        # SET LOCAL scopes the GUC to this transaction only; never trust client input here.
        await session.execute(
            text("SET LOCAL app.current_org_id = :org_id"),
            {"org_id": str(tenant.organisation_id)},
        )
        await session.execute(
            text("SET LOCAL app.current_user_id = :user_id"),
            {"user_id": str(tenant.user_id)},
        )
        yield session


async def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
