"""AI execution endpoints protected by organisation feature wiring."""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import FeatureDisabledError
from app.infrastructure.db.session import get_db_session
from app.modules.ai.domain.models import AIRequest, AIRequestType
from app.modules.ai.infrastructure.factory import build_ai_providers
from app.modules.ai_orchestration.application.orchestrator import AIOrchestrator
from app.modules.permissions.api.routes import require_permission
from app.modules.identity.domain.models import AuthenticatedPrincipal


class ExecutionRequest(BaseModel):
    input: dict = Field(default_factory=dict)
    project_id: uuid.UUID | None = None
    request_type: Literal["text", "image_analysis", "image_generation"] = "text"

router = APIRouter(prefix="/ai-orchestration", tags=["ai_orchestration"])


@router.post("/features/{feature_id}/execute")
async def execute_feature(
    feature_id: uuid.UUID,
    payload: ExecutionRequest,
    principal: AuthenticatedPrincipal = Depends(require_permission("ai.execute")),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    if principal.organisation_id is None:
        raise FeatureDisabledError("AI feature execution requires an organisation context.")
    request = AIRequest(
        organisation_id=principal.organisation_id,
        user_id=principal.user_id,
        project_id=payload.project_id,
        feature_id=feature_id,
        prompt=str(payload.input.get("prompt", "")),
        image_url=payload.input.get("image_url"),
        image_data=payload.input.get("image_data"),
        parameters=payload.input.get("parameters", {}),
        request_type=AIRequestType(payload.request_type),
    )
    response = await AIOrchestrator(db, build_ai_providers(get_settings())).execute(request, principal)
    return {
        "feature_id": str(feature_id),
        "provider": response.provider,
        "model": response.model,
        "input": payload.input,
        "status": response.status,
        "content": response.content,
        "data": response.data,
        "usage": response.usage.metadata,
        "duration_ms": response.duration_ms,
        "error": (
            {"code": response.error_code, "message": response.error_message}
            if response.error_code
            else None
        ),
    }
