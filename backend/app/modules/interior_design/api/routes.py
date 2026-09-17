"""Interior Design AI Studio API."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_db_session
from app.modules.identity.domain.models import AuthenticatedPrincipal
from app.modules.interior_design.application import owned_project
from app.modules.interior_design.infrastructure.models import AIJob, AIJobStatus, DesignAsset, DesignVersion, InteriorDesignProject
from app.modules.interior_design.infrastructure.storage import PrivateAssetStorage
from app.modules.interior_design.worker import JOB_QUEUED, process_job
from app.modules.permissions.api.routes import require_permission

router = APIRouter(prefix="/interior-design", tags=["interior_design"])


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=10000)
    instructions: dict = Field(default_factory=dict)
    workflow: dict = Field(default_factory=dict)
    provider: str = "openai"
    model: str | None = None
    parameters: dict = Field(default_factory=dict)


@router.post("/projects")
async def create_project(payload: ProjectCreate, principal: AuthenticatedPrincipal = Depends(require_permission("project.create")), db: AsyncSession = Depends(get_db_session)) -> dict:
    if principal.organisation_id is None:
        raise HTTPException(403, "An organisation context is required.")
    project = InteriorDesignProject(organisation_id=principal.organisation_id, created_by_user_id=principal.user_id, name=payload.name)
    db.add(project)
    await db.commit()
    return {"id": str(project.id), "name": project.name}


@router.get("/project-list")
async def list_projects(principal: AuthenticatedPrincipal = Depends(require_permission("project.read")), db: AsyncSession = Depends(get_db_session)) -> list[dict]:
    if principal.organisation_id is None:
        return []
    projects = (await db.execute(select(InteriorDesignProject).where(
        InteriorDesignProject.organisation_id == principal.organisation_id
    ).order_by(InteriorDesignProject.created_at.desc()))).scalars().all()
    return [{"id": str(project.id), "name": project.name} for project in projects]


@router.post("/projects/{project_id}/original", status_code=202)
async def upload_original(project_id: uuid.UUID, upload: UploadFile = File(...), principal: AuthenticatedPrincipal = Depends(require_permission("project.update")), db: AsyncSession = Depends(get_db_session)) -> dict:
    project = await owned_project(db, project_id, principal)
    try:
        key, size = await PrivateAssetStorage().save_upload(upload, project.organisation_id, project.id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    asset = DesignAsset(
        organisation_id=project.organisation_id, project_id=project.id, uploaded_by_user_id=principal.user_id,
        kind="original", storage_key=key, content_type=upload.content_type or "application/octet-stream",
        original_filename=upload.filename or "original", size_bytes=size, metadata_json={},
        created_at=datetime.now(UTC),
    )
    db.add(asset)
    await db.flush()
    job = AIJob(
        organisation_id=project.organisation_id, project_id=project.id, requested_by_user_id=principal.user_id,
        job_type="ANALYSIS", status=JOB_QUEUED, input_data={
            "source_asset_id": str(asset.id),
            "prompt": "Analyze this interior image as structured JSON with room_type, walls, floor, ceiling, windows, doors, furniture, lighting, colours, materials, and architectural_elements.",
        },
    )
    db.add(job)
    await db.flush()
    db.add(AIJobStatus(job_id=job.id, status=JOB_QUEUED, message="Analysis queued", created_at=datetime.now(UTC)))
    await db.commit()
    process_job.delay(str(job.id))
    return {"asset_id": str(asset.id), "analysis_job_id": str(job.id), "status": JOB_QUEUED}


@router.post("/projects/{project_id}/generate", status_code=202)
async def generate_design(project_id: uuid.UUID, payload: GenerateRequest, principal: AuthenticatedPrincipal = Depends(require_permission("ai.execute")), db: AsyncSession = Depends(get_db_session)) -> dict:
    project = await owned_project(db, project_id, principal)
    source = (await db.execute(select(DesignAsset).where(
        DesignAsset.project_id == project.id, DesignAsset.organisation_id == project.organisation_id, DesignAsset.kind == "original"
    ).order_by(DesignAsset.created_at.desc()))).scalars().first()
    if source is None:
        raise HTTPException(400, "Upload an original architecture image first.")
    job = AIJob(
        organisation_id=project.organisation_id, project_id=project.id, requested_by_user_id=principal.user_id,
        job_type="GENERATION", status=JOB_QUEUED, input_data={
            "source_asset_id": str(source.id), "prompt": payload.prompt, "instructions": payload.instructions,
            "workflow": payload.workflow, "provider": payload.provider, "model": payload.model, "parameters": payload.parameters,
        },
    )
    db.add(job)
    await db.flush()
    db.add(AIJobStatus(job_id=job.id, status=JOB_QUEUED, message="Generation queued", created_at=datetime.now(UTC)))
    await db.commit()
    process_job.delay(str(job.id))
    return {"job_id": str(job.id), "status": JOB_QUEUED}


@router.get("/jobs/{job_id}")
async def get_job(job_id: uuid.UUID, principal: AuthenticatedPrincipal = Depends(require_permission("project.read")), db: AsyncSession = Depends(get_db_session)) -> dict:
    job = (await db.execute(select(AIJob).where(AIJob.id == job_id, AIJob.organisation_id == principal.organisation_id))).scalar_one_or_none()
    if job is None:
        raise HTTPException(404, "Job not found.")
    statuses = (await db.execute(select(AIJobStatus).where(AIJobStatus.job_id == job.id).order_by(AIJobStatus.created_at))).scalars().all()
    return {"id": str(job.id), "type": job.job_type, "status": job.status, "output": job.output_data, "error": job.error_message, "statuses": [{"status": item.status, "message": item.message} for item in statuses]}


@router.get("/projects/{project_id}/analysis")
async def get_analysis(project_id: uuid.UUID, principal: AuthenticatedPrincipal = Depends(require_permission("project.read")), db: AsyncSession = Depends(get_db_session)) -> dict:
    await owned_project(db, project_id, principal)
    job = (await db.execute(select(AIJob).where(AIJob.project_id == project_id, AIJob.job_type == "ANALYSIS").order_by(AIJob.created_at.desc()))).scalars().first()
    if job is None:
        raise HTTPException(404, "No image analysis exists for this project.")
    return {"job_id": str(job.id), "status": job.status, "analysis": (job.output_data or {}).get("analysis"), "error": job.error_message}


@router.get("/projects/{project_id}/versions")
async def list_versions(project_id: uuid.UUID, principal: AuthenticatedPrincipal = Depends(require_permission("project.read")), db: AsyncSession = Depends(get_db_session)) -> list[dict]:
    await owned_project(db, project_id, principal)
    versions = (await db.execute(select(DesignVersion).where(DesignVersion.project_id == project_id).order_by(DesignVersion.version_number.desc()))).scalars().all()
    return [{"id": str(version.id), "version": version.version_number, "prompt": version.prompt, "instructions": version.instructions, "workflow": version.workflow, "model": version.model, "saved": version.is_saved, "generated_asset_id": str(version.generated_asset_id) if version.generated_asset_id else None} for version in versions]


@router.post("/versions/{version_id}/save")
async def save_version(version_id: uuid.UUID, principal: AuthenticatedPrincipal = Depends(require_permission("project.update")), db: AsyncSession = Depends(get_db_session)) -> dict:
    version = (await db.execute(select(DesignVersion).where(DesignVersion.id == version_id, DesignVersion.organisation_id == principal.organisation_id))).scalar_one_or_none()
    if version is None:
        raise HTTPException(404, "Design version not found.")
    version.is_saved = True
    await db.commit()
    return {"id": str(version.id), "version": version.version_number, "saved": True}


@router.get("/assets/{asset_id}")
async def get_asset(asset_id: uuid.UUID, principal: AuthenticatedPrincipal = Depends(require_permission("project.read")), db: AsyncSession = Depends(get_db_session)) -> Response:
    asset = (await db.execute(select(DesignAsset).where(DesignAsset.id == asset_id, DesignAsset.organisation_id == principal.organisation_id))).scalar_one_or_none()
    if asset is None:
        raise HTTPException(404, "Asset not found.")
    project = await db.get(InteriorDesignProject, asset.project_id)
    if project is None:
        raise HTTPException(404, "Project not found.")
    return Response(content=PrivateAssetStorage().read(asset.organisation_id, project.id, asset.storage_key), media_type=asset.content_type, headers={"Content-Disposition": f'inline; filename="{asset.original_filename}"'})
