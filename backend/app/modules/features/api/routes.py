"""API routes for the features module.

Phase 2 scope: module boundary + wiring only. Business endpoints are added in
later phases once the domain/application layers for this module are implemented.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/features", tags=["features"])


@router.get("/_module", include_in_schema=False)
async def module_status() -> dict[str, str]:
    """Lightweight marker confirming this module is wired into the API surface."""
    return {"module": "features", "status": "scaffolded"}
