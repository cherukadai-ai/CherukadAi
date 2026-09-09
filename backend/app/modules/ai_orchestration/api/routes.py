"""AI execution endpoints protected by organisation feature wiring."""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.db.session import get_db_session
from app.modules.ai.application.service import AIExecutionService
from app.modules.ai.domain.models import AIRequest, AIRequestType
from app.modules.ai.infrastructure.factory import build_ai_providers
from app.modules.ai.infrastructure.models import AIExecution
from app.modules.feature_wiring.api.routes import require_enabled_feature
from app.modules.identity.api.deps import get_current_principal
from app.modules.identity.domain.models import AuthenticatedPrincipal


class ExecutionRequest(BaseModel):
    input: dict = Field(default_factory=dict)
    provider: str = "openai"
    model: str | None = None
    project_id: uuid.UUID | None = None
    workflow_id: uuid.UUID | None = None
    request_type: Literal["text", "image_analysis", "image_generation"] = "text"

router = APIRouter(prefix="/ai-orchestration", tags=["ai_orchestration"])


@router.post("/features/{feature_id}/execute")
async def execute_feature(
    feature_id: uuid.UUID,
    payload: ExecutionRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    wiring = await require_enabled_feature(feature_id, principal, db)
    if principal.organisation_id is None:
        return {
            "feature_id": str(feature_id),
            "status": "rejected",
            "error": "organisation_required",
        }
    request = AIRequest(
        organisation_id=principal.organisation_id,
        user_id=principal.user_id,
        project_id=payload.project_id,
        feature_id=feature_id,
        workflow_id=payload.workflow_id,
        provider=payload.provider,
        model=payload.model,
        prompt=str(payload.input.get("prompt", "")),
        image_url=payload.input.get("image_url"),
        image_data=payload.input.get("image_data"),
        parameters=payload.input.get("parameters", {}),
        request_type=AIRequestType(payload.request_type),
    )
    response = await AIExecutionService(build_ai_providers(get_settings())).execute(request)
    db.add(
        AIExecution(
            organisation_id=request.organisation_id,
            user_id=request.user_id,
            project_id=request.project_id,
            feature_id=request.feature_id,
            workflow_id=request.workflow_id,
            provider=response.provider,
            model=response.model,
            status=response.status,
            duration_ms=response.duration_ms,
            usage_metadata={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.total_tokens,
                **response.usage.metadata,
            },
            error_code=response.error_code,
            error_message=response.error_message,
            created_at=response.created_at,
        )
    )
    await db.commit()
    return {
        "feature_id": str(feature_id),
        "wiring_version": wiring.version,
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
