"""Platform-admin API for the central AI product registry."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_platform_admin
from app.core.exceptions import ConflictError, NotFoundError
from app.infrastructure.db.session import get_db_session
from app.modules.ai.api.schemas import (
    ModelCreate, ModelResponse, ModelUpdate, ProductCreate, ProductResponse,
    RegistryCreate, RegistryListResponse, RegistryResponse, RegistryUpdate,
)
from app.modules.ai.infrastructure.models import (
    AIAgent, AIFeature, AIModel, AIProduct, AIRegistryStatus,
)
from app.modules.identity.domain.models import AuthenticatedPrincipal

router = APIRouter(prefix="/ai", tags=["ai"])


def _admin() -> Any:
    return Depends(require_platform_admin)


async def _get(model: type[Any], item_id: uuid.UUID, db: AsyncSession) -> Any:
    item = await db.get(model, item_id)
    if item is None:
        raise NotFoundError("Registry item not found.")
    return item


async def _commit(db: AsyncSession, item: Any) -> Any:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("A registry item with this code already exists in the scope.") from exc
    await db.refresh(item)
    return item


async def _ensure_product(product_id: uuid.UUID, db: AsyncSession) -> None:
    await _get(AIProduct, product_id, db)


@router.get("/products", response_model=RegistryListResponse)
async def list_products(
    _admin: AuthenticatedPrincipal = _admin(), db: AsyncSession = Depends(get_db_session),
) -> RegistryListResponse:
    items = list((await db.execute(select(AIProduct).order_by(AIProduct.created_at.desc()))).scalars())
    return RegistryListResponse(items=[ProductResponse.model_validate(item) for item in items], total=len(items))


@router.post("/products/create", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate, _admin: AuthenticatedPrincipal = _admin(), db: AsyncSession = Depends(get_db_session),
) -> AIProduct:
    item = AIProduct(**payload.model_dump())
    db.add(item)
    return await _commit(db, item)


@router.patch("/products/{item_id}", response_model=ProductResponse)
async def update_product(
    item_id: uuid.UUID, payload: RegistryUpdate, _admin: AuthenticatedPrincipal = _admin(), db: AsyncSession = Depends(get_db_session),
) -> AIProduct:
    item = await _get(AIProduct, item_id, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key != "product_id":
            setattr(item, key, value)
    return await _commit(db, item)


@router.get("/features", response_model=RegistryListResponse)
async def list_features(
    _admin: AuthenticatedPrincipal = _admin(), db: AsyncSession = Depends(get_db_session),
) -> RegistryListResponse:
    items = list((await db.execute(select(AIFeature).order_by(AIFeature.created_at.desc()))).scalars())
    return RegistryListResponse(items=[RegistryResponse.model_validate(item) for item in items], total=len(items))


@router.post("/features/create", response_model=RegistryResponse, status_code=status.HTTP_201_CREATED)
async def create_feature(
    payload: RegistryCreate, _admin: AuthenticatedPrincipal = _admin(), db: AsyncSession = Depends(get_db_session),
) -> AIFeature:
    await _ensure_product(payload.product_id, db)
    item = AIFeature(**payload.model_dump())
    db.add(item)
    return await _commit(db, item)


@router.patch("/features/{item_id}", response_model=RegistryResponse)
async def update_feature(
    item_id: uuid.UUID, payload: RegistryUpdate, _admin: AuthenticatedPrincipal = _admin(), db: AsyncSession = Depends(get_db_session),
) -> AIFeature:
    item = await _get(AIFeature, item_id, db)
    values = payload.model_dump(exclude_unset=True)
    if "product_id" in values:
        await _ensure_product(values["product_id"], db)
    for key, value in values.items():
        setattr(item, key, value)
    return await _commit(db, item)


async def _list_child(model: type[Any], response_model: type[Any], db: AsyncSession) -> RegistryListResponse:
    items = list((await db.execute(select(model).order_by(model.created_at.desc()))).scalars())
    return RegistryListResponse(items=[response_model.model_validate(item) for item in items], total=len(items))


@router.get("/agents", response_model=RegistryListResponse)
async def list_agents(
    _admin: AuthenticatedPrincipal = _admin(), db: AsyncSession = Depends(get_db_session),
) -> RegistryListResponse:
    return await _list_child(AIAgent, RegistryResponse, db)


@router.post("/agents/create", response_model=RegistryResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: RegistryCreate, _admin: AuthenticatedPrincipal = _admin(), db: AsyncSession = Depends(get_db_session),
) -> AIAgent:
    await _ensure_product(payload.product_id, db)
    item = AIAgent(**payload.model_dump())
    db.add(item)
    return await _commit(db, item)


@router.patch("/agents/{item_id}", response_model=RegistryResponse)
async def update_agent(
    item_id: uuid.UUID, payload: RegistryUpdate, _admin: AuthenticatedPrincipal = _admin(), db: AsyncSession = Depends(get_db_session),
) -> AIAgent:
    item = await _get(AIAgent, item_id, db)
    values = payload.model_dump(exclude_unset=True)
    if "product_id" in values:
        await _ensure_product(values["product_id"], db)
    for key, value in values.items():
        setattr(item, key, value)
    return await _commit(db, item)


@router.get("/models", response_model=RegistryListResponse)
async def list_models(
    _admin: AuthenticatedPrincipal = _admin(), db: AsyncSession = Depends(get_db_session),
) -> RegistryListResponse:
    return await _list_child(AIModel, ModelResponse, db)


@router.post("/models/create", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    payload: ModelCreate, _admin: AuthenticatedPrincipal = _admin(), db: AsyncSession = Depends(get_db_session),
) -> AIModel:
    await _ensure_product(payload.product_id, db)
    item = AIModel(**payload.model_dump())
    db.add(item)
    return await _commit(db, item)


@router.patch("/models/{item_id}", response_model=ModelResponse)
async def update_model(
    item_id: uuid.UUID, payload: ModelUpdate, _admin: AuthenticatedPrincipal = _admin(), db: AsyncSession = Depends(get_db_session),
) -> AIModel:
    item = await _get(AIModel, item_id, db)
    values = payload.model_dump(exclude_unset=True)
    if "product_id" in values:
        await _ensure_product(values["product_id"], db)
    for key, value in values.items():
        setattr(item, key, value)
    return await _commit(db, item)


async def _set_status(
    model: type[Any], item_id: uuid.UUID, status_value: str, db: AsyncSession,
) -> Any:
    item = await _get(model, item_id, db)
    item.status = status_value
    return await _commit(db, item)


async def _bump_version(model: type[Any], item_id: uuid.UUID, db: AsyncSession) -> Any:
    item = await _get(model, item_id, db)
    item.version += 1
    return await _commit(db, item)


def _lifecycle_endpoint(model: type[Any], status_value: str):
    async def endpoint(
        item_id: uuid.UUID,
        _admin: AuthenticatedPrincipal = Depends(require_platform_admin),
        db: AsyncSession = Depends(get_db_session),
    ) -> Any:
        return await _set_status(model, item_id, status_value, db)

    return endpoint


def _version_endpoint(model: type[Any]):
    async def endpoint(
        item_id: uuid.UUID,
        _admin: AuthenticatedPrincipal = Depends(require_platform_admin),
        db: AsyncSession = Depends(get_db_session),
    ) -> Any:
        return await _bump_version(model, item_id, db)

    return endpoint


for _path, _model, _response in (
    ("products", AIProduct, ProductResponse),
    ("features", AIFeature, RegistryResponse),
    ("agents", AIAgent, RegistryResponse),
    ("models", AIModel, ModelResponse),
):
    router.add_api_route(
        f"/{_path}/{{item_id}}/activate", _lifecycle_endpoint(_model, AIRegistryStatus.ACTIVE),
        methods=["POST"], response_model=_response,
    )
    router.add_api_route(
        f"/{_path}/{{item_id}}/deactivate", _lifecycle_endpoint(_model, AIRegistryStatus.INACTIVE),
        methods=["POST"], response_model=_response,
    )
    router.add_api_route(
        f"/{_path}/{{item_id}}/version", _version_endpoint(_model),
        methods=["POST"], response_model=_response,
    )
