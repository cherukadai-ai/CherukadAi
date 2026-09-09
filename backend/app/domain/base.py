""""Shared kernel" domain primitives used across all modules."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.core.exceptions import ForbiddenError


@dataclass(frozen=True)
class TenantContext:
    """Resolved, trusted identity of the caller for the duration of one request.

    This is constructed exactly once per request from the verified session — never
    from client-supplied organisation/user IDs — and threaded through every
    tenant-scoped repository call and permission check.
    """

    organisation_id: uuid.UUID
    user_id: uuid.UUID
    permissions: frozenset[str] = field(default_factory=frozenset)
    is_platform_admin: bool = False

    @classmethod
    def from_membership(
        cls,
        *,
        organisation_id: uuid.UUID,
        user_id: uuid.UUID,
        permissions: set[str] | frozenset[str],
        organisation_status: str,
    ) -> "TenantContext":
        if organisation_status != "active":
            raise ForbiddenError("This organisation is not active.", organisation_status=organisation_status)
        return cls(
            organisation_id=organisation_id,
            user_id=user_id,
            permissions=frozenset(permissions),
        )

    def has_permission(self, permission: str) -> bool:
        return self.is_platform_admin or permission in self.permissions


class Entity:
    """Marker base class for domain entities (identity-based equality by id)."""

    id: uuid.UUID

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
