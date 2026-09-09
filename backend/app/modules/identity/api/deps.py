"""Identity module dependency wiring.

FastAPI dependencies are the framework's middleware equivalents: every protected
route resolves the caller through `get_current_principal` (authentication) and
`require_platform_admin` (authorization). They read only the verified server-side
session — never client-supplied user IDs or roles.

NB: imports `get_db_session` directly from infrastructure (not `app.api.deps`)
to keep the dependency direction acyclic — `app.api.deps` re-exports from here.
"""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError
from app.infrastructure.cache.redis import get_redis
from app.infrastructure.db.session import get_db_session
from app.modules.identity.application.authenticate import AuthenticateSession
from app.modules.identity.application.login import Login
from app.modules.identity.application.logout import Logout
from app.modules.identity.application.setup_super_admin import SetupSuperAdmin
from app.modules.identity.domain.models import AuthenticatedPrincipal
from app.modules.identity.domain.ports import (
    IdentityUnitOfWork,
    PasswordHasher,
    RateLimiter,
    SessionStore,
)
from app.modules.identity.domain.services import PasswordPolicy
from app.modules.identity.infrastructure.password_hasher import Argon2PasswordHasher
from app.modules.identity.infrastructure.rate_limiter import InMemoryRateLimiter, RedisRateLimiter
from app.modules.identity.infrastructure.repositories import SqlAlchemyIdentityUnitOfWork
from app.modules.identity.infrastructure.session_store import InMemorySessionStore, RedisSessionStore

_local_session_store = InMemorySessionStore()
_local_rate_limiter = InMemoryRateLimiter()


def get_identity_uow(db: AsyncSession = Depends(get_db_session)) -> IdentityUnitOfWork:
    return SqlAlchemyIdentityUnitOfWork(db)


def get_password_hasher() -> PasswordHasher:
    return Argon2PasswordHasher()


def get_session_store() -> SessionStore:
    if get_settings().environment == "local":
        return _local_session_store
    return RedisSessionStore(get_redis())


def get_rate_limiter() -> RateLimiter:
    if get_settings().environment == "local":
        return _local_rate_limiter
    return RedisRateLimiter(get_redis())


def get_setup_use_case(
    uow: IdentityUnitOfWork = Depends(get_identity_uow),
    hasher: PasswordHasher = Depends(get_password_hasher),
) -> SetupSuperAdmin:
    settings = get_settings()
    return SetupSuperAdmin(
        uow,
        hasher,
        PasswordPolicy(min_length=settings.password_min_length),
        required_setup_token=settings.super_admin_setup_token,
    )


def get_login_use_case(
    uow: IdentityUnitOfWork = Depends(get_identity_uow),
    hasher: PasswordHasher = Depends(get_password_hasher),
    sessions: SessionStore = Depends(get_session_store),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> Login:
    settings = get_settings()
    return Login(
        uow,
        hasher,
        sessions,
        rate_limiter,
        max_failed_attempts=settings.max_failed_login_attempts,
        lockout_seconds=settings.account_lockout_seconds,
        rate_limit_attempts=settings.login_rate_limit_attempts,
        rate_limit_window_seconds=settings.login_rate_limit_window_seconds,
        session_ttl_seconds=settings.session_ttl_seconds,
    )


def get_logout_use_case(sessions: SessionStore = Depends(get_session_store)) -> Logout:
    return Logout(sessions)


async def get_current_principal(
    request: Request,
    uow: IdentityUnitOfWork = Depends(get_identity_uow),
    sessions: SessionStore = Depends(get_session_store),
) -> AuthenticatedPrincipal:
    """Authentication middleware: resolve the session cookie to a trusted principal."""
    token = request.cookies.get(get_settings().session_cookie_name)
    return await AuthenticateSession(uow, sessions).execute(token)


def require_platform_admin(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> AuthenticatedPrincipal:
    """Authorization middleware: require platform-admin (Super Admin) privileges."""
    if not principal.is_platform_admin:
        raise ForbiddenError("Platform administrator privileges are required.")
    return principal
