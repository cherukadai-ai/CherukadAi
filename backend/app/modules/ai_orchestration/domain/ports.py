"""Ports for the provider-independent AI orchestration boundary."""
from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from app.modules.ai.domain.models import AIRequest, AIResponse
from app.modules.ai.domain.ports import IAIProvider
from app.modules.feature_wiring.infrastructure.models import FeatureWiring
from app.modules.identity.domain.models import AuthenticatedPrincipal


@dataclass(frozen=True)
class ResolvedExecution:
    request: AIRequest
    feature: Any
    wiring: FeatureWiring
    workflow: Mapping[str, Any]
    agent: Any
    prompt: str
    provider: IAIProvider
    model: Any


class IWorkflowResolver(Protocol):
    async def resolve(self, feature: Any, wiring: FeatureWiring) -> Mapping[str, Any]: ...


class IAIAgentResolver(Protocol):
    async def resolve(self, feature: Any, workflow: Mapping[str, Any]) -> Any: ...


class IPromptResolver(Protocol):
    async def resolve(
        self, request: AIRequest, feature: Any, workflow: Mapping[str, Any], agent: Any
    ) -> str: ...


class IFeatureAccessService(Protocol):
    async def authorize(
        self, feature_id: uuid.UUID, principal: AuthenticatedPrincipal
    ) -> FeatureWiring: ...


class IAIOrchestrator(Protocol):
    async def execute(self, request: AIRequest, principal: AuthenticatedPrincipal) -> AIResponse: ...