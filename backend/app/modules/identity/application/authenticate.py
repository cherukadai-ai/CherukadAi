"""Use case: resolve an opaque session token into a trusted principal.

This is the single authentication decision point reused by the API dependencies
(authentication + authorization middleware equivalents in FastAPI).
"""
from __future__ import annotations

from app.application.base import UseCase
from app.core.exceptions import UnauthorizedError
from app.modules.identity.domain.models import AuthenticatedPrincipal
from app.modules.identity.domain.ports import IdentityUnitOfWork, SessionStore


class AuthenticateSession(UseCase[str | None, AuthenticatedPrincipal]):
    def __init__(self, uow: IdentityUnitOfWork, sessions: SessionStore) -> None:
        self._uow = uow
        self._sessions = sessions

    async def execute(self, payload: str | None) -> AuthenticatedPrincipal:
        if not payload:
            raise UnauthorizedError("Authentication required.")

        record = await self._sessions.resolve(payload)
        if record is None:
            raise UnauthorizedError("Session is invalid or has expired.")

        if record.is_platform_admin:
            admin = await self._uow.admins.get_by_id(record.principal_id)
            if admin is None or not admin.is_active:
                raise UnauthorizedError("Session is invalid or has expired.")
            return AuthenticatedPrincipal(principal_id=admin.id, email=admin.email, full_name=admin.full_name)
        user = await self._uow.users.get_by_id(record.principal_id)
        if user is None or not user.is_active or user.organisation_id != record.organisation_id:
            raise UnauthorizedError("Session is invalid or has expired.")
        from app.modules.permissions.domain.catalog import permissions_for_role
        return AuthenticatedPrincipal(principal_id=user.id, email=user.email, full_name=user.display_name, is_platform_admin=False, organisation_id=user.organisation_id, permissions=permissions_for_role(user.role))
