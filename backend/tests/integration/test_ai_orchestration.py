import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions import FeatureDisabledError
from app.infrastructure.db.base import Base
from app.modules.ai.domain.models import AIRequest, AIResponse, AIResponseStatus
from app.modules.ai.infrastructure.models import AIAgent, AIFeature, AIModel, AIProduct
from app.modules.ai_orchestration.application.orchestrator import AIOrchestrator
from app.modules.feature_wiring.infrastructure.models import FeatureWiring, FeatureWiringStatus
from app.modules.identity.domain.models import AuthenticatedPrincipal
from app.modules.organisations.infrastructure.models import OrganisationModel


class FakeProvider:
    provider_name = "fake"
    calls = 0

    async def generate_text(self, request):
        self.calls += 1
        return AIResponse(provider="fake", model=request.model or "fake-model", status=AIResponseStatus.SUCCEEDED, content=request.prompt)


@pytest.fixture()
async def orchestration_session(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/orchestration.db")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _seed(session, enabled=True):
    organisation = OrganisationModel(id=uuid.uuid4(), name=f"org-{uuid.uuid4()}", display_name="Org", email="org@test")
    product = AIProduct(id=uuid.uuid4(), code="PRODUCT", name="Product")
    feature = AIFeature(id=uuid.uuid4(), code="FEATURE", name="Feature", product_id=product.id, configuration={"workflow": {"agent_code": "AGENT", "model_code": "MODEL", "prompt": "Run {input}"}})
    agent = AIAgent(id=uuid.uuid4(), code="AGENT", name="Agent", product_id=product.id)
    model = AIModel(id=uuid.uuid4(), code="MODEL", name="Model", provider="fake", product_id=product.id)
    wiring = FeatureWiring(organisation_id=organisation.id, ai_product_id=product.id, ai_feature_id=feature.id, status=FeatureWiringStatus.ENABLED if enabled else FeatureWiringStatus.DISABLED)
    session.add_all([organisation, product, feature, agent, model, wiring])
    await session.commit()
    return organisation, feature


@pytest.mark.asyncio
async def test_unwired_feature_is_rejected_before_provider_call(orchestration_session):
    organisation, feature = await _seed(orchestration_session, enabled=False)
    provider = FakeProvider()
    principal = AuthenticatedPrincipal(uuid.uuid4(), "user@test", "User", False, organisation.id, frozenset({"ai.execute"}))
    request = AIRequest(organisation.id, principal.user_id, feature_id=feature.id, prompt="input")

    with pytest.raises(FeatureDisabledError):
        await AIOrchestrator(orchestration_session, {"fake": provider}).execute(request, principal)
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_orchestrator_resolves_server_configuration_and_stores_result(orchestration_session):
    organisation, feature = await _seed(orchestration_session)
    provider = FakeProvider()
    principal = AuthenticatedPrincipal(uuid.uuid4(), "user@test", "User", False, organisation.id, frozenset({"ai.execute"}))
    request = AIRequest(organisation.id, principal.user_id, feature_id=feature.id, prompt="input")

    response = await AIOrchestrator(orchestration_session, {"fake": provider}).execute(request, principal)

    assert response.content == "Run input"
    assert provider.calls == 1