"""Platform administration endpoints for organisations."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_platform_admin
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.infrastructure.db.session import get_db_session
from app.modules.identity.domain.models import AuthenticatedPrincipal
from app.modules.identity.infrastructure.password_hasher import Argon2PasswordHasher
from app.modules.organisations.api.schemas import (
    OrganisationCreate, OrganisationListResponse, OrganisationResponse, OrganisationUpdate,
)
from app.modules.organisations.infrastructure.models import (
    OrganisationModel, OrganisationSettingsModel, OrganisationStatus, OrganisationUserModel,
    OrganisationLoginEventModel,
)
from app.modules.identity.infrastructure.password_hasher import Argon2PasswordHasher
from app.modules.organisations.api.schemas import LoginHistoryResponse, OrganisationUserCreate, OrganisationUserResponse, PasswordResetRequest
from app.modules.permissions.api.routes import require_permission
from app.modules.permissions.domain.catalog import ROLES

router = APIRouter(prefix="/organisations", tags=["organisations"])


@router.get("", response_model=OrganisationListResponse)
async def list_organisations(
    search: str | None = Query(default=None, max_length=160),
    _admin: AuthenticatedPrincipal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db_session),
) -> OrganisationListResponse:
    query = select(OrganisationModel).order_by(OrganisationModel.created_at.desc())
    if search:
        query = query.where(
            OrganisationModel.name.ilike(f"%{search}%")
            | OrganisationModel.display_name.ilike(f"%{search}%")
            | OrganisationModel.email.ilike(f"%{search}%")
        )
    items = list((await db.execute(query)).scalars().all())
    return OrganisationListResponse(items=items, total=len(items))


@router.post("/create", response_model=OrganisationResponse, status_code=status.HTTP_201_CREATED)
async def create_organisation(
    payload: OrganisationCreate,
    _admin: AuthenticatedPrincipal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db_session),
) -> OrganisationModel:
    organisation = OrganisationModel(
        name=payload.name, display_name=payload.display_name, email=str(payload.email),
        phone=payload.phone, address=payload.address, logo=payload.logo,
    )
    db.add(organisation)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("An organisation with this name already exists.") from exc
    db.add(OrganisationSettingsModel(organisation_id=organisation.id))
    if payload.admin_email and payload.admin_display_name and payload.admin_password:
        db.add(OrganisationUserModel(
            organisation_id=organisation.id, email=str(payload.admin_email),
            display_name=payload.admin_display_name,
            password_hash=Argon2PasswordHasher().hash(payload.admin_password),
            permissions_json='["organisation:admin"]',
        ))
    await db.commit()
    await db.refresh(organisation)
    return organisation


async def _get(organisation_id: str, db: AsyncSession) -> OrganisationModel:
    try:
        parsed_id = uuid.UUID(organisation_id)
    except ValueError as exc:
        raise NotFoundError("Organisation not found.") from exc
    organisation = await db.get(OrganisationModel, parsed_id)
    if not organisation:
        raise NotFoundError("Organisation not found.")
    return organisation


@router.get("/{organisation_id}", response_model=OrganisationResponse)
async def get_organisation(organisation_id: str, _admin: AuthenticatedPrincipal = Depends(require_platform_admin), db: AsyncSession = Depends(get_db_session)) -> OrganisationModel:
    return await _get(organisation_id, db)


@router.patch("/edit/{organisation_id}", response_model=OrganisationResponse)
async def update_organisation(organisation_id: str, payload: OrganisationUpdate, _admin: AuthenticatedPrincipal = Depends(require_platform_admin), db: AsyncSession = Depends(get_db_session)) -> OrganisationModel:
    organisation = await _get(organisation_id, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(organisation, key, str(value) if key == "email" else value)
    await db.commit()
    await db.refresh(organisation)
    return organisation


async def _set_status(organisation_id: str, status_value: str, db: AsyncSession) -> OrganisationModel:
    organisation = await _get(organisation_id, db)
    organisation.status = status_value
    await db.commit()
    await db.refresh(organisation)
    return organisation


@router.post("/{organisation_id}/activate", response_model=OrganisationResponse)
async def activate_organisation(organisation_id: str, _admin: AuthenticatedPrincipal = Depends(require_platform_admin), db: AsyncSession = Depends(get_db_session)) -> OrganisationModel:
    return await _set_status(organisation_id, OrganisationStatus.ACTIVE, db)


@router.post("/{organisation_id}/suspend", response_model=OrganisationResponse)
async def suspend_organisation(organisation_id: str, _admin: AuthenticatedPrincipal = Depends(require_platform_admin), db: AsyncSession = Depends(get_db_session)) -> OrganisationModel:
    return await _set_status(organisation_id, OrganisationStatus.SUSPENDED, db)


@router.post("/{organisation_id}/archive", response_model=OrganisationResponse)
async def archive_organisation(organisation_id: str, _admin: AuthenticatedPrincipal = Depends(require_platform_admin), db: AsyncSession = Depends(get_db_session)) -> OrganisationModel:
    return await _set_status(organisation_id, OrganisationStatus.ARCHIVED, db)


def _target_organisation(principal: AuthenticatedPrincipal, organisation_id: uuid.UUID | None) -> uuid.UUID:
    if principal.is_platform_admin:
        if organisation_id is None:
            raise NotFoundError("Organisation not found.")
        return organisation_id
    if principal.organisation_id is None or (organisation_id and organisation_id != principal.organisation_id):
        raise ForbiddenError("Cross-organisation access is not allowed.")
    return principal.organisation_id


@router.post("/{organisation_id}/users/create", response_model=OrganisationUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(organisation_id: uuid.UUID, payload: OrganisationUserCreate, principal: AuthenticatedPrincipal = Depends(require_permission("user.create")), db: AsyncSession = Depends(get_db_session)) -> OrganisationUserModel:
    target = _target_organisation(principal, organisation_id)
    if payload.role not in ROLES:
        raise ConflictError("Unknown organisation role.")
    user = OrganisationUserModel(organisation_id=target, email=payload.email.lower(), display_name=payload.name, password_hash=Argon2PasswordHasher().hash(payload.temporary_password), role=payload.role, force_password_change=True)
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("A user with this email already exists in the organisation.") from exc
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{organisation_id}/users", response_model=list[OrganisationUserResponse])
async def list_users(organisation_id: uuid.UUID, principal: AuthenticatedPrincipal = Depends(require_permission("user.read")), db: AsyncSession = Depends(get_db_session)) -> list[OrganisationUserModel]:
    target = _target_organisation(principal, organisation_id)
    return list((await db.execute(select(OrganisationUserModel).where(OrganisationUserModel.organisation_id == target).order_by(OrganisationUserModel.created_at.desc()))).scalars().all())


async def _get_user(organisation_id: uuid.UUID, user_id: uuid.UUID, principal: AuthenticatedPrincipal, db: AsyncSession) -> OrganisationUserModel:
    target = _target_organisation(principal, organisation_id)
    user = await db.get(OrganisationUserModel, user_id)
    if user is None or user.organisation_id != target:
        raise NotFoundError("Organisation user not found.")
    return user


@router.post("/{organisation_id}/users/{user_id}/activate", response_model=OrganisationUserResponse)
async def activate_user(organisation_id: uuid.UUID, user_id: uuid.UUID, principal: AuthenticatedPrincipal = Depends(require_permission("user.update")), db: AsyncSession = Depends(get_db_session)) -> OrganisationUserModel:
    user = await _get_user(organisation_id, user_id, principal, db); user.status = OrganisationStatus.ACTIVE; await db.commit(); await db.refresh(user); return user


@router.post("/{organisation_id}/users/{user_id}/deactivate", response_model=OrganisationUserResponse)
async def deactivate_user(organisation_id: uuid.UUID, user_id: uuid.UUID, principal: AuthenticatedPrincipal = Depends(require_permission("user.disable")), db: AsyncSession = Depends(get_db_session)) -> OrganisationUserModel:
    user = await _get_user(organisation_id, user_id, principal, db); user.status = "disabled"; await db.commit(); await db.refresh(user); return user


@router.post("/{organisation_id}/users/{user_id}/password-reset", response_model=OrganisationUserResponse)
async def reset_user_password(organisation_id: uuid.UUID, user_id: uuid.UUID, payload: PasswordResetRequest, principal: AuthenticatedPrincipal = Depends(require_permission("user.update")), db: AsyncSession = Depends(get_db_session)) -> OrganisationUserModel:
    user = await _get_user(organisation_id, user_id, principal, db); user.password_hash = Argon2PasswordHasher().hash(payload.temporary_password); user.force_password_change = True; user.failed_login_attempts = 0; user.locked_until = None; await db.commit(); await db.refresh(user); return user


@router.post("/{organisation_id}/users/{user_id}/force-password-change", response_model=OrganisationUserResponse)
async def force_user_password_change(organisation_id: uuid.UUID, user_id: uuid.UUID, principal: AuthenticatedPrincipal = Depends(require_permission("user.update")), db: AsyncSession = Depends(get_db_session)) -> OrganisationUserModel:
    user = await _get_user(organisation_id, user_id, principal, db); user.force_password_change = True; await db.commit(); await db.refresh(user); return user


@router.get("/{organisation_id}/users/{user_id}/login-history", response_model=list[LoginHistoryResponse])
async def user_login_history(organisation_id: uuid.UUID, user_id: uuid.UUID, principal: AuthenticatedPrincipal = Depends(require_permission("user.read")), db: AsyncSession = Depends(get_db_session)) -> list[OrganisationLoginEventModel]:
    await _get_user(organisation_id, user_id, principal, db)
    return list((await db.execute(select(OrganisationLoginEventModel).where(OrganisationLoginEventModel.user_id == user_id).order_by(OrganisationLoginEventModel.created_at.desc()))).scalars().all())
