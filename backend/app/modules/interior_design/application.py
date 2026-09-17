"""Use-case helpers for secure project ownership and job transitions."""
from __future__ import annotations

from datetime import UTC, datetime
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.identity.domain.models import AuthenticatedPrincipal
from app.modules.interior_design.infrastructure.models import InteriorDesignProject


async def owned_project(db: AsyncSession, project_id: uuid.UUID, principal: AuthenticatedPrincipal) -> InteriorDesignProject:
    if principal.organisation_id is None:
        raise NotFoundError("Project not found.")
    project = (await db.execute(select(InteriorDesignProject).where(
        InteriorDesignProject.id == project_id,
        InteriorDesignProject.organisation_id == principal.organisation_id,
    ))).scalar_one_or_none()
    if project is None:
        raise NotFoundError("Project not found.")
    return project


def now() -> datetime:
    return datetime.now(UTC)
