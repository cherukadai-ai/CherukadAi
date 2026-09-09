"""Identity entities shared by platform admins and organisation users."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AdminStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class OrganisationUserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass
class PlatformAdmin:
    """A platform Super Administrator account.

    `password_hash` is always a one-way Argon2id hash — plaintext passwords never
    reach the domain layer and are never persisted or returned.
    """

    id: uuid.UUID
    email: str
    full_name: str
    password_hash: str
    status: AdminStatus = AdminStatus.ACTIVE
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    @property
    def is_active(self) -> bool:
        return self.status == AdminStatus.ACTIVE

    def is_locked(self, now: datetime) -> bool:
        return self.locked_until is not None and self.locked_until > now


@dataclass
class OrganisationUser:
    id: uuid.UUID
    organisation_id: uuid.UUID
    email: str
    display_name: str
    password_hash: str
    role: str
    status: OrganisationUserStatus = OrganisationUserStatus.ACTIVE
    force_password_change: bool = True
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.status == OrganisationUserStatus.ACTIVE

    def is_locked(self, now: datetime) -> bool:
        return self.locked_until is not None and self.locked_until > now


@dataclass(frozen=True)
class SessionRecord:
    """Server-side session payload.

    The opaque session token presented by the client is never stored — only its
    SHA-256 digest is used as the storage key.
    """

    principal_id: uuid.UUID
    email: str
    expires_at: datetime
    is_platform_admin: bool = True
    organisation_id: uuid.UUID | None = None
    display_name: str = ""
    permissions: frozenset[str] = field(default_factory=frozenset)

    @property
    def admin_id(self) -> uuid.UUID:
        return self.principal_id


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Trusted caller identity resolved from a verified session.

    Constructed server-side only; never trust client-supplied IDs or roles.
    """

    principal_id: uuid.UUID
    email: str
    full_name: str
    is_platform_admin: bool = True
    organisation_id: uuid.UUID | None = None
    permissions: frozenset[str] = field(default_factory=frozenset)

    @property
    def admin_id(self) -> uuid.UUID:
        return self.principal_id

    @property
    def user_id(self) -> uuid.UUID:
        return self.principal_id

    def has_permission(self, permission: str) -> bool:
        return self.is_platform_admin or permission in self.permissions
