"""Liveness/readiness endpoints.

- /healthz: process is up (no dependency checks) — used by orchestrators for liveness.
- /readyz: process + dependencies (DB, Redis) are reachable — used for readiness gating.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.infrastructure.cache.redis import get_redis
from app.infrastructure.db.session import get_engine

router = APIRouter(tags=["health"])
logger = structlog.get_logger(__name__)


@router.get("/healthz")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readiness() -> JSONResponse:
    checks: dict[str, str] = {}
    healthy = True

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - readiness must never raise
        logger.warning("readiness_check_failed", dependency="database", error=str(exc))
        checks["database"] = "unavailable"
        healthy = False

    try:
        redis = get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("readiness_check_failed", dependency="redis", error=str(exc))
        checks["redis"] = "unavailable"
        healthy = False

    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ok" if healthy else "degraded", "checks": checks},
    )
