"""Ports (interfaces) the identity application layer depends on.

Implementations live in `app.modules.identity.infrastructure`; the application
layer never imports SQLAlchemy, Redis, or FastAPI directly.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

from app.modules.identity.domain.models import OrganisationUser, PlatformAdmin, SessionRecord


class PlatformAdminRepository(Protocol):
    async def exists_any(self) -> bool:
        """True once at least one Super Admin exists (the permanent setup gate)."""
        ...

    async def get_by_email(self, email: str) -> PlatformAdmin | None: ...

    async def get_by_id(self, admin_id: uuid.UUID) -> PlatformAdmin | None: ...

    async def add(self, admin: PlatformAdmin) -> PlatformAdmin: ...

    async def update(self, admin: PlatformAdmin) -> None: ...


class OrganisationUserRepository(Protocol):
    async def get_by_email(self, email: str) -> OrganisationUser | None: ...
    async def get_by_id(self, user_id: uuid.UUID) -> OrganisationUser | None: ...


class PlatformSettingsRepository(Protocol):
    """Key/value platform-wide settings (e.g. the initial-setup marker)."""

    async def get(self, key: str) -> str | None: ...

    async def set_once(self, key: str, value: str) -> bool:
        """Insert only if the key is absent.

        Returns False when the key already exists. This is the race-safe guard
        that permanently closes first-time setup even under concurrent requests.
        """
        ...


class IdentityUnitOfWork(Protocol):
    """Transaction boundary for identity use cases."""

    @property
    def admins(self) -> PlatformAdminRepository: ...

    @property
    def settings(self) -> PlatformSettingsRepository: ...

    @property
    def users(self) -> OrganisationUserRepository: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class PasswordHasher(Protocol):
    def hash(self, plain_password: str) -> str: ...

    def verify(self, plain_password: str, password_hash: str) -> bool: ...


class SessionStore(Protocol):
    async def create(self, admin: PlatformAdmin, ttl_seconds: int) -> tuple[str, datetime]:
        """Create a session; returns (opaque token, expiry)."""
        ...

    async def create_user(
        self, user_id: uuid.UUID, email: str, display_name: str, organisation_id: uuid.UUID,
        permissions: frozenset[str], ttl_seconds: int,
    ) -> tuple[str, datetime]: ...

    async def resolve(self, token: str) -> SessionRecord | None: ...

    async def revoke(self, token: str) -> None: ...


class RateLimiter(Protocol):
    async def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Record one attempt. True while within the limit, False once exceeded."""
        ...
