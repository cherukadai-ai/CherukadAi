import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions import FeatureDisabledError
from app.infrastructure.db.base import Base
from app.modules.ai.infrastructure.models import AIFeature, AIProduct
from app.modules.feature_wiring.api.routes import require_enabled_feature
from app.modules.feature_wiring.infrastructure.models import FeatureWiring, FeatureWiringStatus
from app.modules.identity.domain.models import AuthenticatedPrincipal
from app.modules.organisations.infrastructure.models import OrganisationModel, OrganisationStatus


@pytest.fixture()
async def wiring_session(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/wiring.db")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _seed(session, status=OrganisationStatus.ACTIVE, wiring_status=FeatureWiringStatus.ENABLED):
    organisation = OrganisationModel(id=uuid.uuid4(), name="acme", display_name="Acme", email="a@acme.test", status=status)
    product = AIProduct(id=uuid.uuid4(), code="INTERIOR", name="Interior Design AI")
    feature = AIFeature(id=uuid.uuid4(), code="IMAGE_ANALYSIS", name="Image Analysis", product_id=product.id)
    session.add_all([organisation, product, feature])
    await session.flush()
    session.add(FeatureWiring(organisation_id=organisation.id, ai_product_id=product.id, ai_feature_id=feature.id, status=wiring_status))
    await session.commit()
    return organisation, feature


@pytest.mark.asyncio
async def test_enabled_feature_is_authorized(wiring_session):
    organisation, feature = await _seed(wiring_session)
    principal = AuthenticatedPrincipal(uuid.uuid4(), "user@acme.test", "User", False, organisation.id)
    wiring = await require_enabled_feature(feature.id, principal, wiring_session)
    assert wiring.ai_feature_id == feature.id


@pytest.mark.asyncio
@pytest.mark.parametrize("status,wiring_status", [(OrganisationStatus.ACTIVE, FeatureWiringStatus.DISABLED), (OrganisationStatus.SUSPENDED, FeatureWiringStatus.ENABLED)])
async def test_disabled_or_suspended_feature_is_rejected(wiring_session, status, wiring_status):
    organisation, feature = await _seed(wiring_session, status, wiring_status)
    principal = AuthenticatedPrincipal(uuid.uuid4(), "user@acme.test", "User", False, organisation.id)
    with pytest.raises(FeatureDisabledError):
        await require_enabled_feature(feature.id, principal, wiring_session)


@pytest.mark.asyncio
async def test_cross_tenant_feature_is_rejected(wiring_session):
    organisation, feature = await _seed(wiring_session)
    principal = AuthenticatedPrincipal(uuid.uuid4(), "user@other.test", "User", False, uuid.uuid4())
    with pytest.raises(FeatureDisabledError):
        await require_enabled_feature(feature.id, principal, wiring_session)