"""Celery jobs for image analysis and design generation."""
from __future__ import annotations

import asyncio
import base64
import binascii
import json
from datetime import UTC, datetime
import uuid

from sqlalchemy import select

from app.core.config import get_settings
from app.infrastructure.db.session import get_session_factory
from app.modules.ai.domain.models import AIRequest, AIRequestType
from app.modules.ai.infrastructure.factory import build_ai_providers
from app.modules.ai.application.service import AIExecutionService
from app.modules.interior_design.infrastructure.models import AIJob, AIJobStatus, DesignAsset, DesignVersion
from app.modules.interior_design.infrastructure.storage import PrivateAssetStorage
from app.workers.celery_app import celery_app

JOB_QUEUED = "QUEUED"
JOB_PROCESSING = "PROCESSING"
JOB_COMPLETED = "COMPLETED"
JOB_FAILED = "FAILED"


def _now() -> datetime:
    return datetime.now(UTC)


async def _run(job_id: str) -> None:
    factory = get_session_factory()
    async with factory() as db:
        job = await db.get(AIJob, uuid.UUID(job_id))
        if job is None:
            return
        job.status = JOB_PROCESSING
        job.started_at = _now()
        db.add(AIJobStatus(job_id=job.id, status=JOB_PROCESSING, message="AI operation started", created_at=_now()))
        await db.commit()
        try:
            settings = get_settings()
            providers = build_ai_providers(settings)
            storage = PrivateAssetStorage()
            source = await db.get(DesignAsset, uuid.UUID(str(job.input_data["source_asset_id"])))
            if source is None:
                raise ValueError("Source image was not found.")
            image = base64.b64encode(storage.read(job.organisation_id, job.project_id, source.storage_key)).decode()
            request_type = AIRequestType.IMAGE_ANALYSIS if job.job_type == "ANALYSIS" else AIRequestType.IMAGE_GENERATION
            request = AIRequest(
                organisation_id=job.organisation_id,
                user_id=job.requested_by_user_id,
                project_id=job.project_id,
                prompt=job.input_data["prompt"],
                image_data=image,
                parameters=job.input_data.get("parameters", {}),
                provider=job.input_data.get("provider", "openai"),
                model=job.input_data.get("model"),
                request_type=request_type,
            )
            response = await AIExecutionService(providers).execute(request)
            if not response.succeeded:
                raise ValueError(response.error_message or "AI provider failed.")
            if request_type == AIRequestType.IMAGE_ANALYSIS:
                try:
                    analysis = json.loads(response.content or "{}")
                except json.JSONDecodeError:
                    analysis = {"description": response.content or ""}
                job.output_data = {"analysis": analysis, "provider": response.provider, "model": response.model}
            else:
                image_data = (response.data[0].get("b64_json") if response.data else None)
                if not image_data:
                    raise ValueError("AI provider returned no generated image.")
                try:
                    generated = base64.b64decode(image_data, validate=True)
                except (binascii.Error, ValueError) as exc:
                    raise ValueError("AI provider returned invalid image data.") from exc
                key, size = storage.save_generated(generated, job.organisation_id, job.project_id)
                asset = DesignAsset(
                    organisation_id=job.organisation_id, project_id=job.project_id,
                    uploaded_by_user_id=job.requested_by_user_id, kind="generated",
                    storage_key=key, content_type="image/png", original_filename="generated.png",
                    size_bytes=size, metadata_json={"job_id": str(job.id)}, created_at=_now(),
                )
                db.add(asset)
                await db.flush()
                previous = (await db.execute(select(DesignVersion).where(
                    DesignVersion.project_id == job.project_id
                ).order_by(DesignVersion.version_number.desc()))).scalars().first()
                version = DesignVersion(
                    organisation_id=job.organisation_id, project_id=job.project_id,
                    source_asset_id=source.id, generated_asset_id=asset.id,
                    created_by_user_id=job.requested_by_user_id,
                    version_number=(previous.version_number + 1 if previous else 1),
                    prompt=job.input_data["prompt"], instructions=job.input_data.get("instructions", {}),
                    workflow=job.input_data.get("workflow", {}), model=response.model, is_saved=False,
                )
                db.add(version)
                await db.flush()
                job.output_data = {"version_id": str(version.id), "asset_id": str(asset.id), "provider": response.provider, "model": response.model}
            job.status = JOB_COMPLETED
            job.completed_at = _now()
            db.add(AIJobStatus(job_id=job.id, status=JOB_COMPLETED, message="AI operation completed", created_at=_now()))
        except Exception as exc:
            job.status = JOB_FAILED
            job.error_message = str(exc)
            job.completed_at = _now()
            db.add(AIJobStatus(job_id=job.id, status=JOB_FAILED, message=str(exc)[:500], created_at=_now()))
        await db.commit()


@celery_app.task(name="interior_design.process_job")
def process_job(job_id: str) -> None:
    asyncio.run(_run(job_id))
