"""Organisation-level AI feature wiring and execution authorization."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_principal, require_platform_admin
from app.core.exceptions import ConflictError, FeatureDisabledError, ForbiddenError, NotFoundError
from app.infrastructure.db.session import get_db_session
from app.modules.ai.infrastructure.models import AIFeature, AIProduct
from app.modules.feature_wiring.api.schemas import (
    FeatureWiringCreate, FeatureWiringListResponse, FeatureWiringResponse, FeatureWiringUpdate,
)
from app.modules.feature_wiring.infrastructure.models import (
    FeatureWiring, FeatureWiringStatus, FeatureWiringVersion,
)
from app.modules.identity.domain.models import AuthenticatedPrincipal
from app.modules.organisations.infrastructure.models import OrganisationModel, OrganisationStatus

router = APIRouter(prefix="/feature-wiring", tags=["feature_wiring"])


async def _get_wiring(wiring_id: uuid.UUID, db: AsyncSession) -> FeatureWiring:
    wiring = await db.get(FeatureWiring, wiring_id)
    if wiring is None:
        raise NotFoundError("Feature wiring not found.")
    return wiring


async def _validate_references(payload: FeatureWiringCreate, db: AsyncSession) -> None:
    organisation = await db.get(OrganisationModel, payload.organisation_id)
    product = await db.get(AIProduct, payload.ai_product_id)
    feature = await db.get(AIFeature, payload.ai_feature_id)
    if organisation is None or product is None or feature is None or feature.product_id != product.id:
        raise NotFoundError("Organisation, AI product, or AI feature not found.")


async def _snapshot(wiring: FeatureWiring, db: AsyncSession) -> None:
    db.add(FeatureWiringVersion(
        wiring_id=wiring.id, version=wiring.version, configuration=wiring.configuration,
        status=wiring.status, created_at=datetime.now(timezone.utc),
    ))


@router.get("/list", response_model=FeatureWiringListResponse)
async def list_wirings(
    organisation_id: uuid.UUID | None = None,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db_session),
) -> FeatureWiringListResponse:
    if principal.is_platform_admin:
        if organisation_id is None:
            raise NotFoundError("Organisation not found.")
        target = organisation_id
    else:
        if principal.organisation_id is None or (organisation_id and organisation_id != principal.organisation_id):
            raise ForbiddenError("Cross-organisation access is not allowed.")
        target = principal.organisation_id
    items = list((await db.execute(
        select(FeatureWiring).where(FeatureWiring.organisation_id == target)
        .order_by(FeatureWiring.created_at.desc())
    )).scalars().all())
    return FeatureWiringListResponse(items=items, total=len(items))


@router.post("", response_model=FeatureWiringResponse, status_code=status.HTTP_201_CREATED)
async def create_wiring(
    payload: FeatureWiringCreate,
    _admin: AuthenticatedPrincipal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db_session),
) -> FeatureWiring:
    await _validate_references(payload, db)
    wiring = FeatureWiring(**payload.model_dump())
    db.add(wiring)
    try:
        await db.flush()
        await _snapshot(wiring, db)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("This AI feature is already wired for the organisation.") from exc
    await db.refresh(wiring)
    return wiring


@router.patch("/{wiring_id}", response_model=FeatureWiringResponse)
async def configure_wiring(
    wiring_id: uuid.UUID, payload: FeatureWiringUpdate,
    _admin: AuthenticatedPrincipal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db_session),
) -> FeatureWiring:
    wiring = await _get_wiring(wiring_id, db)
    if payload.configuration is not None:
        wiring.configuration = payload.configuration
        wiring.version += 1
        await _snapshot(wiring, db)
    await db.commit()
    await db.refresh(wiring)
    return wiring


async def _change_status(wiring_id: uuid.UUID, status_value: str, db: AsyncSession) -> FeatureWiring:
    wiring = await _get_wiring(wiring_id, db)
    wiring.status = status_value
    await _snapshot(wiring, db)
    await db.commit()
    await db.refresh(wiring)
    return wiring


@router.post("/{wiring_id}/enable", response_model=FeatureWiringResponse)
async def enable_wiring(wiring_id: uuid.UUID, _admin: AuthenticatedPrincipal = Depends(require_platform_admin), db: AsyncSession = Depends(get_db_session)) -> FeatureWiring:
    return await _change_status(wiring_id, FeatureWiringStatus.ENABLED, db)


@router.post("/{wiring_id}/disable", response_model=FeatureWiringResponse)
async def disable_wiring(wiring_id: uuid.UUID, _admin: AuthenticatedPrincipal = Depends(require_platform_admin), db: AsyncSession = Depends(get_db_session)) -> FeatureWiring:
    return await _change_status(wiring_id, FeatureWiringStatus.DISABLED, db)


@router.post("/{wiring_id}/publish", response_model=FeatureWiringResponse)
async def publish_wiring(wiring_id: uuid.UUID, _admin: AuthenticatedPrincipal = Depends(require_platform_admin), db: AsyncSession = Depends(get_db_session)) -> FeatureWiring:
    wiring = await _get_wiring(wiring_id, db)
    wiring.published_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(wiring)
    return wiring


@router.post("/{wiring_id}/rollback/{version}", response_model=FeatureWiringResponse)
async def rollback_wiring(wiring_id: uuid.UUID, version: int, _admin: AuthenticatedPrincipal = Depends(require_platform_admin), db: AsyncSession = Depends(get_db_session)) -> FeatureWiring:
    wiring = await _get_wiring(wiring_id, db)
    snapshot = (await db.execute(select(FeatureWiringVersion).where(
        FeatureWiringVersion.wiring_id == wiring_id, FeatureWiringVersion.version == version,
    ))).scalar_one_or_none()
    if snapshot is None:
        raise NotFoundError("Feature wiring version not found.")
    wiring.configuration = snapshot.configuration
    wiring.status = snapshot.status
    wiring.version += 1
    await _snapshot(wiring, db)
    await db.commit()
    await db.refresh(wiring)
    return wiring


@router.get("/me", response_model=FeatureWiringListResponse)
async def list_my_wirings(principal: AuthenticatedPrincipal = Depends(get_current_principal), db: AsyncSession = Depends(get_db_session)) -> FeatureWiringListResponse:
    if principal.is_platform_admin or principal.organisation_id is None:
        return FeatureWiringListResponse(items=[], total=0)
    organisation = await db.get(OrganisationModel, principal.organisation_id)
    if organisation is None:
        raise NotFoundError("Organisation not found.")
    items = list((await db.execute(select(FeatureWiring).where(
        FeatureWiring.organisation_id == organisation.id,
        FeatureWiring.status == FeatureWiringStatus.ENABLED,
    ))).scalars().all())
    return FeatureWiringListResponse(items=items, total=len(items))


async def require_enabled_feature(feature_id: uuid.UUID, principal: AuthenticatedPrincipal, db: AsyncSession) -> FeatureWiring:
    if principal.is_platform_admin or principal.organisation_id is None:
        raise FeatureDisabledError("AI feature execution requires an organisation context.")
    organisation = await db.get(OrganisationModel, principal.organisation_id)
    wiring = (await db.execute(select(FeatureWiring).where(
        FeatureWiring.organisation_id == principal.organisation_id,
        FeatureWiring.ai_feature_id == feature_id,
        FeatureWiring.status == FeatureWiringStatus.ENABLED,
    ))).scalar_one_or_none()
    if organisation is None or organisation.status != OrganisationStatus.ACTIVE:
        raise FeatureDisabledError("AI feature execution is unavailable for this organisation.")
    if wiring is None:
        raise FeatureDisabledError("The requested AI feature is not enabled for this organisation.")
    return wiring
