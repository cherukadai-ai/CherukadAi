"""Application service that owns the complete AI execution pipeline."""
from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import FeatureDisabledError, NotFoundError, ValidationAppError
from app.modules.ai.application.service import AIExecutionService
from app.modules.ai.domain.models import AIRequest, AIResponse
from app.modules.ai.infrastructure.models import AIAgent, AIFeature, AIExecution, AIModel, AIProduct
from app.modules.ai.infrastructure.models import AIRegistryStatus
from app.modules.ai_orchestration.domain.ports import (
    IAIAgentResolver,
    IAIOrchestrator,
    IFeatureAccessService,
    IPromptResolver,
    IWorkflowResolver,
)
from app.modules.feature_wiring.infrastructure.models import FeatureWiring, FeatureWiringStatus
from app.modules.identity.domain.models import AuthenticatedPrincipal
from app.modules.organisations.infrastructure.models import OrganisationModel, OrganisationStatus


def _configured(source: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if source.get(key) is not None:
            return source[key]
    return None


class FeatureAccessService(IFeatureAccessService):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def authorize(
        self, feature_id: uuid.UUID, principal: AuthenticatedPrincipal
    ) -> FeatureWiring:
        if principal.organisation_id is None or not principal.has_permission("ai.execute"):
            raise FeatureDisabledError("AI feature execution is not authorized.")
        organisation = await self._db.get(OrganisationModel, principal.organisation_id)
        wiring = (await self._db.execute(select(FeatureWiring).where(
            FeatureWiring.organisation_id == principal.organisation_id,
            FeatureWiring.ai_feature_id == feature_id,
            FeatureWiring.status == FeatureWiringStatus.ENABLED,
        ))).scalar_one_or_none()
        if organisation is None or organisation.status != OrganisationStatus.ACTIVE or wiring is None:
            raise FeatureDisabledError("The requested AI feature is not enabled for this organisation.")
        return wiring


class WorkflowResolver(IWorkflowResolver):
    async def resolve(self, feature: AIFeature, wiring: FeatureWiring) -> Mapping[str, Any]:
        configuration = {**feature.configuration, **wiring.configuration}
        workflow = configuration.get("workflow")
        if isinstance(workflow, Mapping):
            return workflow
        workflow_code = workflow or configuration.get("workflow_code")
        if not workflow_code:
            raise ValidationAppError("The enabled AI feature has no workflow configured.")
        return {"code": workflow_code, **configuration.get("workflow_configuration", {})}


class AIAgentResolver(IAIAgentResolver):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def resolve(self, feature: AIFeature, workflow: Mapping[str, Any]) -> AIAgent:
        agent_id = workflow.get("agent_id")
        agent_code = workflow.get("agent_code") or workflow.get("agent")
        query = select(AIAgent).where(
            AIAgent.product_id == feature.product_id,
            AIAgent.status == AIRegistryStatus.ACTIVE,
        )
        if agent_id:
            query = query.where(AIAgent.id == uuid.UUID(str(agent_id)))
        elif agent_code:
            query = query.where(AIAgent.code == str(agent_code))
        else:
            raise ValidationAppError("The resolved workflow has no agent configured.")
        agent = (await self._db.execute(query)).scalar_one_or_none()
        if agent is None:
            raise NotFoundError("The configured AI agent was not found.")
        return agent


class PromptResolver(IPromptResolver):
    async def resolve(
        self, request: AIRequest, feature: AIFeature, workflow: Mapping[str, Any], agent: AIAgent
    ) -> str:
        template = workflow.get("prompt") or agent.configuration.get("prompt")
        template = template or feature.configuration.get("prompt")
        if not template:
            return request.prompt
        try:
            return str(template).format(request=request.prompt, input=request.prompt)
        except (KeyError, ValueError) as exc:
            raise ValidationAppError("The configured prompt is invalid.") from exc


class AIOrchestrator(IAIOrchestrator):
    def __init__(self, db: AsyncSession, providers: Mapping[str, object]) -> None:
        self._db = db
        self._providers = providers
        self._feature_access = FeatureAccessService(db)
        self._workflow_resolver = WorkflowResolver()
        self._agent_resolver = AIAgentResolver(db)
        self._prompt_resolver = PromptResolver()

    async def execute(self, request: AIRequest, principal: AuthenticatedPrincipal) -> AIResponse:
        if request.feature_id is None:
            raise ValidationAppError("An AI feature is required for execution.")
        if request.organisation_id != principal.organisation_id or request.user_id != principal.user_id:
            raise FeatureDisabledError("The execution identity does not match the authenticated user.")
        wiring = await self._feature_access.authorize(request.feature_id, principal)
        feature = await self._resolve_feature(request.feature_id)
        workflow = await self._workflow_resolver.resolve(feature, wiring)
        agent = await self._agent_resolver.resolve(feature, workflow)
        prompt = await self._prompt_resolver.resolve(request, feature, workflow, agent)
        model = await self._resolve_model(feature, wiring, workflow)
        provider = self._providers.get(model.provider)
        if provider is None:
            raise ValidationAppError("The configured AI provider is not available.")
        resolved = AIRequest(
            organisation_id=request.organisation_id,
            user_id=request.user_id,
            project_id=request.project_id,
            feature_id=request.feature_id,
            prompt=prompt,
            image_url=request.image_url,
            image_data=request.image_data,
            parameters=request.parameters,
            request_type=request.request_type,
            provider=model.provider,
            model=model.code,
        )
        response = await AIExecutionService({model.provider: provider}).execute(resolved)
        self._validate_output(response)
        await self._store(resolved, response, workflow)
        return response

    @staticmethod
    def _validate_output(response: AIResponse) -> None:
        if response.succeeded and not response.content and not response.data:
            raise ValidationAppError("The AI provider returned an empty result.")

    async def _resolve_feature(self, feature_id: uuid.UUID) -> AIFeature:
        feature = await self._db.get(AIFeature, feature_id)
        if feature is None or feature.status != AIRegistryStatus.ACTIVE:
            raise NotFoundError("AI feature not found.")
        product = await self._db.get(AIProduct, feature.product_id)
        if product is None or product.status != AIRegistryStatus.ACTIVE:
            raise FeatureDisabledError("The AI product for this feature is unavailable.")
        return feature

    async def _resolve_model(
        self, feature: AIFeature, wiring: FeatureWiring, workflow: Mapping[str, Any]
    ) -> AIModel:
        configuration = {**feature.configuration, **wiring.configuration, **workflow}
        model_id = _configured(configuration, "model_id")
        model_code = _configured(configuration, "model_code", "model")
        query = select(AIModel).where(
            AIModel.product_id == feature.product_id,
            AIModel.status == AIRegistryStatus.ACTIVE,
        )
        if model_id:
            query = query.where(AIModel.id == uuid.UUID(str(model_id)))
        elif model_code:
            query = query.where(AIModel.code == str(model_code))
        else:
            raise ValidationAppError("The resolved workflow has no model configured.")
        model = (await self._db.execute(query)).scalar_one_or_none()
        if model is None:
            raise NotFoundError("The configured AI model was not found.")
        return model

    async def _store(self, request: AIRequest, response: AIResponse, workflow: Mapping[str, Any]) -> None:
        self._db.add(AIExecution(
            organisation_id=request.organisation_id,
            user_id=request.user_id,
            project_id=request.project_id,
            feature_id=request.feature_id,
            workflow_id=uuid.UUID(str(workflow["id"])) if workflow.get("id") else None,
            provider=response.provider,
            model=response.model,
            status=response.status,
            duration_ms=response.duration_ms,
            usage_metadata={"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens, "total_tokens": response.usage.total_tokens, **response.usage.metadata},
            error_code=response.error_code,
            error_message=response.error_message,
            created_at=response.created_at,
        ))
        await self._db.commit()