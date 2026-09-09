"""The single source of truth for organisation roles and permissions."""
from __future__ import annotations

from typing import Final

ROLE_ORGANISATION_ADMIN: Final = "ORGANISATION_ADMIN"
ROLE_ORGANISATION_MANAGER: Final = "ORGANISATION_MANAGER"
ROLE_PROFESSIONAL_USER: Final = "PROFESSIONAL_USER"
ROLE_USER: Final = "USER"

PERMISSIONS: Final = frozenset({
    "organisation.read", "organisation.update",
    "user.create", "user.read", "user.update", "user.disable",
    "project.create", "project.read", "project.update", "project.delete",
    "ai.execute",
    "feature.read", "feature.execute", "feature.configure",
})

ROLE_PERMISSIONS: Final[dict[str, frozenset[str]]] = {
    ROLE_ORGANISATION_ADMIN: frozenset(PERMISSIONS),
    ROLE_ORGANISATION_MANAGER: frozenset({
        "organisation.read", "user.create", "user.read", "user.update",
        "project.create", "project.read", "project.update", "project.delete",
        "ai.execute", "feature.read", "feature.execute",
    }),
    ROLE_PROFESSIONAL_USER: frozenset({"organisation.read", "project.create", "project.read", "project.update", "ai.execute", "feature.read", "feature.execute"}),
    ROLE_USER: frozenset({"organisation.read", "project.read", "feature.read"}),
}

ROLES: Final = frozenset(ROLE_PERMISSIONS)


def permissions_for_role(role: str) -> frozenset[str]:
    try:
        return ROLE_PERMISSIONS[role]
    except KeyError as exc:
        raise ValueError(f"Unknown organisation role: {role}") from exc