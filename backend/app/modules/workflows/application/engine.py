from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.modules.workflows.domain.validation import topological_order, validate_graph
from app.modules.workflows.infrastructure.models import (
    Workflow,
    WorkflowExecution,
    WorkflowExecutionStatus,
    WorkflowExecutionStep,
    WorkflowExecutionStepStatus,
    WorkflowStatus,
    WorkflowStep,
    WorkflowVersion,
)

StepHandler = Callable[[dict, dict, dict], Awaitable[dict]]


class WorkflowEngine:
    """Builds, validates, publishes, and executes data-only workflow definitions."""

    def __init__(self, session: AsyncSession, handlers: dict[str, StepHandler] | None = None):
        self.session = session
        self.handlers = handlers or {}

    async def create_workflow(
        self, organisation_id: uuid.UUID, slug: str, name: str, description: str | None = None
    ) -> Workflow:
        workflow = Workflow(
            organisation_id=organisation_id, slug=slug, name=name, description=description
        )
        self.session.add(workflow)
        await self.session.flush()
        return workflow

    async def create_version(self, workflow: Workflow, steps: list[dict]) -> WorkflowVersion:
        if workflow.status == WorkflowStatus.PUBLISHED:
            raise ConflictError("Create a new version before changing a published workflow.")
        validate_graph(steps)
        version = workflow.current_version + 1
        workflow.current_version = version
        workflow.status = WorkflowStatus.DRAFT
        workflow_version = WorkflowVersion(
            workflow_id=workflow.id, version=version, definition={"steps": steps}
        )
        self.session.add(workflow_version)
        await self.session.flush()
        self.session.add_all(
            [
                WorkflowStep(
                    workflow_version_id=workflow_version.id,
                    key=step["key"],
                    name=step.get("name") or step["key"],
                    type=step["type"],
                    depends_on=step.get("depends_on", []),
                    configuration=step.get("configuration", {}),
                    position=index,
                )
                for index, step in enumerate(steps)
            ]
        )
        await self.session.flush()
        return workflow_version

    async def validate_version(self, workflow_version: WorkflowVersion) -> WorkflowVersion:
        validate_graph(workflow_version.definition.get("steps", []))
        workflow_version.status = WorkflowStatus.VALIDATED
        workflow_version.validated_at = datetime.now(UTC)
        return workflow_version

    async def approve_version(self, workflow_version: WorkflowVersion) -> WorkflowVersion:
        if workflow_version.status != WorkflowStatus.VALIDATED:
            raise ConflictError("Only validated workflow versions can be approved.")
        workflow_version.status = WorkflowStatus.APPROVED
        workflow_version.approved_at = datetime.now(UTC)
        return workflow_version

    async def publish_version(
        self, workflow: Workflow, workflow_version: WorkflowVersion
    ) -> WorkflowVersion:
        if workflow_version.status != WorkflowStatus.APPROVED:
            raise ConflictError("Only approved workflow versions can be published.")
        workflow_version.status = WorkflowStatus.PUBLISHED
        workflow_version.published_at = datetime.now(UTC)
        workflow.status = WorkflowStatus.PUBLISHED
        workflow.published_version = workflow_version.version
        return workflow_version

    async def rollback(self, workflow: Workflow, version: int) -> WorkflowVersion:
        target = (
            await self.session.execute(
                select(WorkflowVersion).where(
                    WorkflowVersion.workflow_id == workflow.id,
                    WorkflowVersion.version == version,
                )
            )
        ).scalar_one_or_none()
        if target is None:
            raise NotFoundError("Workflow version not found.")
        if target.status not in {WorkflowStatus.APPROVED, WorkflowStatus.PUBLISHED}:
            raise ConflictError("Only approved or published versions can be rolled back to.")
        workflow.published_version = target.version
        workflow.status = WorkflowStatus.PUBLISHED
        target.status = WorkflowStatus.PUBLISHED
        target.published_at = datetime.now(UTC)
        return target

    async def archive(self, workflow: Workflow) -> Workflow:
        if workflow.status == WorkflowStatus.ARCHIVED:
            raise ConflictError("Workflow is already archived.")
        workflow.status = WorkflowStatus.ARCHIVED
        if workflow.published_version is not None:
            published = (await self.session.execute(select(WorkflowVersion).where(
                WorkflowVersion.workflow_id == workflow.id,
                WorkflowVersion.version == workflow.published_version,
            ))).scalar_one_or_none()
            if published is not None:
                published.status = WorkflowStatus.ARCHIVED
        return workflow

    async def execute(self, workflow: Workflow, input_data: dict) -> WorkflowExecution:
        if workflow.status != WorkflowStatus.PUBLISHED or workflow.published_version is None:
            raise ConflictError("Only published workflows can execute in production.")
        version = (
            await self.session.execute(
                select(WorkflowVersion).where(
                    WorkflowVersion.workflow_id == workflow.id,
                    WorkflowVersion.version == workflow.published_version,
                    WorkflowVersion.status == WorkflowStatus.PUBLISHED,
                )
            )
        ).scalar_one_or_none()
        if version is None:
            raise ConflictError("The published workflow version is unavailable.")
        steps = topological_order(version.definition.get("steps", []))
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            workflow_version_id=version.id,
            organisation_id=workflow.organisation_id,
            input_data=input_data,
            status=WorkflowExecutionStatus.RUNNING,
            created_at=datetime.now(UTC),
        )
        self.session.add(execution)
        await self.session.flush()
        context = dict(input_data)
        try:
            for step in steps:
                handler = self.handlers.get(step["type"])
                if handler is None:
                    raise ValidationAppError(
                        f"No registered handler for workflow step type: {step['type']}."
                    )
                record = WorkflowExecutionStep(
                    execution_id=execution.id,
                    workflow_step_id=(
                        await self.session.execute(
                            select(WorkflowStep.id).where(
                                WorkflowStep.workflow_version_id == version.id,
                                WorkflowStep.key == step["key"],
                            )
                        )
                    ).scalar_one(),
                    status=WorkflowExecutionStepStatus.RUNNING,
                    input_data=dict(context),
                    started_at=datetime.now(UTC),
                )
                self.session.add(record)
                await self.session.flush()
                result = await handler(step.get("configuration", {}), context, input_data)
                context[step["key"]] = result
                record.output_data = result
                record.status = WorkflowExecutionStepStatus.SUCCEEDED
                record.completed_at = datetime.now(UTC)
            execution.status = WorkflowExecutionStatus.SUCCEEDED
            execution.output_data = context
        except Exception as exc:
            execution.status = WorkflowExecutionStatus.FAILED
            execution.error_message = str(exc)
        finally:
            execution.completed_at = datetime.now(UTC)
        return execution
