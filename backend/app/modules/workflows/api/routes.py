"""Workflow authoring, lifecycle, and execution endpoints."""
# FastAPI dependencies are intentionally declared in endpoint signatures.
# ruff: noqa: B008

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_platform_admin
from app.core.exceptions import NotFoundError
from app.infrastructure.db.session import get_db_session
from app.modules.identity.domain.models import AuthenticatedPrincipal
from app.modules.workflows.api.schemas import (
    WorkflowCreate,
    WorkflowExecutionRequest,
    WorkflowResponse,
    WorkflowVersionCreate,
    WorkflowVersionResponse,
)
from app.modules.workflows.application.engine import WorkflowEngine
from app.modules.workflows.infrastructure.models import Workflow, WorkflowVersion

router = APIRouter(prefix="/workflows", tags=["workflows"])


async def _workflow(workflow_id: uuid.UUID, db: AsyncSession) -> Workflow:
    workflow = await db.get(Workflow, workflow_id)
    if workflow is None:
        raise NotFoundError("Workflow not found.")
    return workflow


async def _version(version_id: uuid.UUID, db: AsyncSession) -> WorkflowVersion:
    version = await db.get(WorkflowVersion, version_id)
    if version is None:
        raise NotFoundError("Workflow version not found.")
    return version


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    _admin: AuthenticatedPrincipal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db_session),
) -> Workflow:
    workflow = await WorkflowEngine(db).create_workflow(**payload.model_dump())
    await db.commit()
    await db.refresh(workflow)
    return workflow


@router.post(
    "/{workflow_id}/versions",
    response_model=WorkflowVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_version(
    workflow_id: uuid.UUID,
    payload: WorkflowVersionCreate,
    _admin: AuthenticatedPrincipal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db_session),
) -> WorkflowVersion:
    workflow = await _workflow(workflow_id, db)
    version = await WorkflowEngine(db).create_version(
        workflow, [step.model_dump() for step in payload.steps]
    )
    await db.commit()
    await db.refresh(version)
    return version


@router.post("/versions/{version_id}/validate", response_model=WorkflowVersionResponse)
async def validate_version(
    version_id: uuid.UUID,
    _admin: AuthenticatedPrincipal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db_session),
) -> WorkflowVersion:
    version = await _version(version_id, db)
    await WorkflowEngine(db).validate_version(version)
    await db.commit()
    return version


@router.post("/versions/{version_id}/approve", response_model=WorkflowVersionResponse)
async def approve_version(
    version_id: uuid.UUID,
    _admin: AuthenticatedPrincipal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db_session),
) -> WorkflowVersion:
    version = await _version(version_id, db)
    await WorkflowEngine(db).approve_version(version)
    await db.commit()
    return version


@router.post("/{workflow_id}/versions/{version_id}/publish", response_model=WorkflowVersionResponse)
async def publish_version(
    workflow_id: uuid.UUID,
    version_id: uuid.UUID,
    _admin: AuthenticatedPrincipal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db_session),
) -> WorkflowVersion:
    workflow = await _workflow(workflow_id, db)
    version = await _version(version_id, db)
    if version.workflow_id != workflow.id:
        raise NotFoundError("Workflow version not found.")
    await WorkflowEngine(db).publish_version(workflow, version)
    await db.commit()
    return version


@router.post("/{workflow_id}/rollback/{version}", response_model=WorkflowVersionResponse)
async def rollback(
    workflow_id: uuid.UUID,
    version: int,
    _admin: AuthenticatedPrincipal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db_session),
) -> WorkflowVersion:
    workflow = await _workflow(workflow_id, db)
    result = await WorkflowEngine(db).rollback(workflow, version)
    await db.commit()
    return result

@router.post("/{workflow_id}/archive", response_model=WorkflowResponse)
async def archive(
    workflow_id: uuid.UUID,
    _admin: AuthenticatedPrincipal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db_session),
) -> Workflow:
    workflow = await _workflow(workflow_id, db)
    await WorkflowEngine(db).archive(workflow)
    await db.commit()
    await db.refresh(workflow)
    return workflow


@router.post("/{workflow_id}/execute", response_model=dict)
async def execute(
    workflow_id: uuid.UUID,
    payload: WorkflowExecutionRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    workflow = await _workflow(workflow_id, db)
    execution = await WorkflowEngine(db).execute(workflow, payload.input_data)
    await db.commit()
    return {"id": execution.id, "status": execution.status, "output_data": execution.output_data}


@router.get("/{workflow_id}/executions", response_model=list[dict])
async def execution_history(
    workflow_id: uuid.UUID,
    _admin: AuthenticatedPrincipal = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    await _workflow(workflow_id, db)
    from app.modules.workflows.infrastructure.models import WorkflowExecution

    executions = (
        (
            await db.execute(
                select(WorkflowExecution)
                .where(WorkflowExecution.workflow_id == workflow_id)
                .order_by(WorkflowExecution.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": item.id,
            "status": item.status,
            "output_data": item.output_data,
            "created_at": item.created_at,
        }
        for item in executions
    ]
