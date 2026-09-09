"""Tenant domain values used by authentication and application services."""
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class OrganisationMembership:
    user_id: uuid.UUID
    organisation_id: uuid.UUID
    permissions: frozenset[str]
    organisation_status: str
