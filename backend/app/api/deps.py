"""Shared FastAPI dependencies (DI wiring lives here, not in route bodies)."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_db_session

# Platform-wide authentication/authorization dependencies, owned by the identity
# module and re-exported here for other modules to protect their routes:
# `get_current_principal` authenticates, `require_platform_admin` authorizes.
from app.modules.identity.api.deps import (  # noqa: F401
    get_current_principal,
    require_platform_admin,
)

DbSession = AsyncIterator[AsyncSession]


async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in get_db_session():
        yield session


# NOTE: `get_current_tenant_context` (session -> TenantContext resolution) is
# intentionally deferred to the tenancy/RBAC phase; organisation-scoped modules
# are not implemented yet.
