"""Shared pytest fixtures.

Sets safe, non-secret test environment variables before the app/config module is
imported anywhere, so tests never touch real infrastructure by accident.
"""
from __future__ import annotations

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://cherukadai:cherukadai@localhost:5432/cherukadai_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("LOG_JSON", "false")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def app():
    get_settings.cache_clear()
    return create_app()


@pytest.fixture()
def client(app) -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


# --- Identity module fixtures -------------------------------------------------
#
# Identity integration tests run against a throwaway file-based SQLite database
# (created per test, so tests are fully isolated) with in-memory session store
# and rate limiter substituted for Redis via dependency overrides.

from collections.abc import AsyncIterator  # noqa: E402
from dataclasses import dataclass  # noqa: E402

from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.db.base import Base  # noqa: E402
from app.infrastructure.db.session import get_db_session  # noqa: E402
from app.modules.identity.api.deps import (  # noqa: E402
    get_rate_limiter,
    get_session_store,
)
from app.modules.identity.infrastructure import models as identity_models  # noqa: E402,F401
from app.modules.organisations.infrastructure import models as organisation_models  # noqa: E402,F401
from app.modules.ai.infrastructure import models as ai_models  # noqa: E402,F401
from app.modules.identity.infrastructure.rate_limiter import InMemoryRateLimiter  # noqa: E402
from app.modules.identity.infrastructure.session_store import InMemorySessionStore  # noqa: E402


@dataclass
class IdentityTestRig:
    """Everything an identity integration test needs, freshly isolated per test."""

    client: TestClient
    session_factory: async_sessionmaker[AsyncSession]
    session_store: InMemorySessionStore
    rate_limiter: InMemoryRateLimiter


@pytest.fixture()
async def identity_rig(app, tmp_path) -> AsyncIterator[IdentityTestRig]:
    db_url = f"sqlite+aiosqlite:///{tmp_path}/identity_test.db"
    engine: AsyncEngine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    session_store = InMemorySessionStore()
    rate_limiter = InMemoryRateLimiter()

    async def _override_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_session_store] = lambda: session_store
    app.dependency_overrides[get_rate_limiter] = lambda: rate_limiter
    try:
        with TestClient(app) as test_client:
            yield IdentityTestRig(
                client=test_client,
                session_factory=session_factory,
                session_store=session_store,
                rate_limiter=rate_limiter,
            )
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
