"""API routes for the identity module.

Covers first-time Super Admin setup (self-closing, enforced server-side) and
session-based authentication. Organisation-user identity arrives with the
tenancy/RBAC phases.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.modules.identity.api.deps import (
    get_current_principal,
    get_login_use_case,
    get_logout_use_case,
    get_session_store,
    get_setup_use_case,
    require_platform_admin,
)
from app.modules.identity.api.schemas import (
    LoginRequest,
    PlatformAdminSessionResponse,
    SetupStatusResponse,
    SetupSuperAdminRequest,
    OrganisationLoginRequest, OrganisationSessionResponse,
    ChangePasswordRequest,
)
from app.modules.identity.application.login import Login, LoginInput
from app.modules.identity.application.logout import Logout
from app.modules.identity.application.setup_super_admin import (
    SetupSuperAdmin,
    SetupSuperAdminInput,
)
from app.modules.identity.domain.models import AuthenticatedPrincipal
from app.modules.identity.domain.ports import SessionStore
from app.infrastructure.db.session import get_db_session
from app.modules.organisations.infrastructure.models import OrganisationLoginEventModel, OrganisationUserModel, OrganisationStatus
from app.modules.permissions.domain.catalog import permissions_for_role
from app.core.exceptions import UnauthorizedError
from app.modules.identity.infrastructure.password_hasher import Argon2PasswordHasher

router = APIRouter(prefix="/identity", tags=["identity"])


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=get_settings().session_cookie_name, path="/")


@router.get("/setup/status", response_model=SetupStatusResponse)
async def setup_status(
    use_case: SetupSuperAdmin = Depends(get_setup_use_case),
) -> SetupStatusResponse:
    """Public pre-flight for the setup screen. The write endpoint re-enforces the
    gate — this response is a UX hint only, never an authorization decision."""
    settings = get_settings()
    return SetupStatusResponse(
        setup_required=await use_case.setup_required(),
        setup_token_required=settings.super_admin_setup_token is not None,
    )


@router.post(
    "/setup",
    status_code=status.HTTP_201_CREATED,
    response_model=PlatformAdminSessionResponse,
)
async def create_super_admin(
    payload: SetupSuperAdminRequest,
    response: Response,
    use_case: SetupSuperAdmin = Depends(get_setup_use_case),
    sessions: SessionStore = Depends(get_session_store),
) -> PlatformAdminSessionResponse:
    """Create the first Super Administrator.

    Permanently rejects further attempts once any Super Admin exists. On success
    the caller is signed in immediately (HTTP-only session cookie).
    """
    result = await use_case.execute(
        SetupSuperAdminInput(
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
            setup_token=payload.setup_token,
        )
    )
    token, _ = await sessions.create(result.admin, get_settings().session_ttl_seconds)
    _set_session_cookie(response, token)
    return PlatformAdminSessionResponse.from_admin(result.admin)


@router.post("/login", response_model=PlatformAdminSessionResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    use_case: Login = Depends(get_login_use_case),
) -> PlatformAdminSessionResponse:
    client_host = request.client.host if request.client else "unknown"
    result = await use_case.execute(
        LoginInput(email=payload.email, password=payload.password, ip_address=client_host)
    )
    _set_session_cookie(response, result.session_token)
    return PlatformAdminSessionResponse.from_admin(result.admin)


@router.post("/organisation/login", response_model=OrganisationSessionResponse)
async def organisation_login(payload: OrganisationLoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db_session), sessions: SessionStore = Depends(get_session_store)) -> OrganisationSessionResponse:
    user = (await db.execute(select(OrganisationUserModel).where(OrganisationUserModel.organisation_id == payload.organisation_id, OrganisationUserModel.email == payload.email.lower()))).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    event = OrganisationLoginEventModel(user_id=user.id, organisation_id=payload.organisation_id, succeeded=False, ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"), reason="invalid_credentials") if user else None
    if user is None or user.status != OrganisationStatus.ACTIVE or (user.locked_until and user.locked_until.replace(tzinfo=timezone.utc) > now):
        if event is not None:
            db.add(event); await db.commit()
        raise UnauthorizedError("Invalid email or password.")
    if not Argon2PasswordHasher().verify(payload.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= get_settings().max_failed_login_attempts:
            user.locked_until = now + timedelta(seconds=get_settings().account_lockout_seconds)
        event.user_id = user.id; event.reason = "invalid_credentials"; db.add(event); await db.commit(); raise UnauthorizedError("Invalid email or password.")
    user.failed_login_attempts = 0; user.locked_until = None; user.last_login_at = now
    event.user_id = user.id; event.succeeded = True; event.reason = None; db.add(event); await db.commit()
    token, _ = await sessions.create_user(user.id, user.email, user.display_name, user.organisation_id, permissions_for_role(user.role), get_settings().session_ttl_seconds)
    _set_session_cookie(response, token)
    return OrganisationSessionResponse(user_id=user.id, organisation_id=user.organisation_id, email=user.email, display_name=user.display_name, permissions=sorted(permissions_for_role(user.role)), force_password_change=user.force_password_change)


@router.post("/organisation/change-password", response_model=OrganisationSessionResponse)
async def change_organisation_password(payload: ChangePasswordRequest, response: Response, principal: AuthenticatedPrincipal = Depends(get_current_principal), db: AsyncSession = Depends(get_db_session), sessions: SessionStore = Depends(get_session_store)) -> OrganisationSessionResponse:
    if principal.is_platform_admin or principal.organisation_id is None:
        raise UnauthorizedError("Organisation-user authentication required.")
    user = await db.get(OrganisationUserModel, principal.user_id)
    if user is None or user.status != OrganisationStatus.ACTIVE or not Argon2PasswordHasher().verify(payload.current_password, user.password_hash):
        raise UnauthorizedError("Current password is invalid.")
    user.password_hash = Argon2PasswordHasher().hash(payload.new_password)
    user.force_password_change = False
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()
    return OrganisationSessionResponse(user_id=user.id, organisation_id=user.organisation_id, email=user.email, display_name=user.display_name, permissions=sorted(permissions_for_role(user.role)), force_password_change=False)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    use_case: Logout = Depends(get_logout_use_case),
) -> Response:
    token = request.cookies.get(get_settings().session_cookie_name)
    if token:
        await use_case.execute(token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookie(response)
    return response


@router.delete("/sessions/current", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_current_session(request: Request, principal: AuthenticatedPrincipal = Depends(get_current_principal), sessions: SessionStore = Depends(get_session_store)) -> Response:
    token = request.cookies.get(get_settings().session_cookie_name)
    if token:
        await sessions.revoke(token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookie(response)
    return response


@router.get("/me", response_model=PlatformAdminSessionResponse)
async def me(
    principal: AuthenticatedPrincipal = Depends(require_platform_admin),
) -> PlatformAdminSessionResponse:
    return PlatformAdminSessionResponse.from_principal(principal)
