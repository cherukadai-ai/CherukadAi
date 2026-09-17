import uuid
from types import SimpleNamespace

import pytest

from app.modules.ai.domain.models import AIRequest
from app.modules.ai_orchestration.application.orchestrator import PromptResolver


@pytest.mark.asyncio
async def test_prompt_resolver_uses_registered_template_without_client_model_control():
    request = AIRequest(uuid.uuid4(), uuid.uuid4(), prompt="a bright kitchen")
    feature = SimpleNamespace(configuration={})
    agent = SimpleNamespace(configuration={"prompt": "Describe: {input}"})

    result = await PromptResolver().resolve(request, feature, {}, agent)

    assert result == "Describe: a bright kitchen"