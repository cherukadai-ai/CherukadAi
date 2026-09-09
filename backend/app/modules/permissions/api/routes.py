"""Central permission catalog and authorization policy surface."""
from fastapi import APIRouter, Depends
from app.core.exceptions import ForbiddenError
from app.modules.identity.api.deps import get_current_principal
from app.modules.identity.domain.models import AuthenticatedPrincipal

from app.modules.permissions.domain.catalog import PERMISSIONS, ROLE_PERMISSIONS

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("/_module", include_in_schema=False)
async def module_status() -> dict[str, str]:
    """Lightweight marker confirming this module is wired into the API surface."""
    return {"module": "permissions", "status": "scaffolded"}


@router.get("", include_in_schema=False)
async def list_permissions() -> dict[str, object]:
    return {"permissions": sorted(PERMISSIONS), "roles": ROLE_PERMISSIONS}


def require_permission(permission: str):
    if permission not in PERMISSIONS:
        raise ValueError(f"Unknown permission: {permission}")

    def dependency(principal: AuthenticatedPrincipal = Depends(get_current_principal)) -> AuthenticatedPrincipal:
        if not principal.has_permission(permission):
            raise ForbiddenError("You do not have permission to perform this action.", permission=permission)
        return principal

    return dependency
