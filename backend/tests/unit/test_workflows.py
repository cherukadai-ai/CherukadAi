import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions import ConflictError, ValidationAppError
from app.infrastructure.db.base import Base
from app.modules.organisations.infrastructure.models import OrganisationModel
from app.modules.workflows.application.engine import WorkflowEngine
from app.modules.workflows.domain.validation import topological_order, validate_graph
from app.modules.workflows.infrastructure.models import WorkflowStatus


@pytest.mark.parametrize(
    "steps",
    [
        [
            {"key": "a", "type": "prompt", "depends_on": ["b"]},
            {"key": "b", "type": "prompt", "depends_on": ["a"]},
        ],
        [{"key": "a", "type": "unknown"}],
        [{"key": "a", "type": "prompt", "depends_on": ["missing"]}],
    ],
)
def test_invalid_workflow_graphs_are_rejected(steps):
    with pytest.raises(ValidationAppError):
        validate_graph(steps)


def test_graph_is_topologically_ordered():
    steps = [
        {"key": "output", "type": "storage", "depends_on": ["analysis"]},
        {"key": "analysis", "type": "ai_agent"},
    ]
    assert [step["key"] for step in topological_order(steps)] == ["analysis", "output"]


@pytest.fixture()
async def workflow_session(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/workflows.db")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_workflow_requires_validation_and_approval_before_publish(workflow_session):
    organisation = OrganisationModel(
        id=uuid.uuid4(), name="acme", display_name="Acme", email="a@acme.test"
    )
    workflow_session.add(organisation)
    await workflow_session.flush()
    engine = WorkflowEngine(workflow_session)
    workflow = await engine.create_workflow(organisation.id, "rooms", "Room analysis")
    version = await engine.create_version(workflow, [{"key": "prompt", "type": "prompt"}])
    with pytest.raises(ConflictError):
        await engine.publish_version(workflow, version)
    await engine.validate_version(version)
    await engine.approve_version(version)
    await engine.publish_version(workflow, version)
    assert workflow.status == WorkflowStatus.PUBLISHED
    assert workflow.published_version == 1


@pytest.mark.asyncio
async def test_unpublished_workflow_cannot_execute(workflow_session):
    organisation = OrganisationModel(
        id=uuid.uuid4(), name="acme", display_name="Acme", email="a@acme.test"
    )
    workflow_session.add(organisation)
    await workflow_session.flush()
    workflow = await WorkflowEngine(workflow_session).create_workflow(
        organisation.id, "draft", "Draft"
    )
    with pytest.raises(ConflictError):
        await WorkflowEngine(workflow_session).execute(workflow, {})
