from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FeatureWiringCreate(BaseModel):
    organisation_id: uuid.UUID
    ai_product_id: uuid.UUID
    ai_feature_id: uuid.UUID
    configuration: dict[str, Any] = Field(default_factory=dict)


class FeatureWiringUpdate(BaseModel):
    configuration: dict[str, Any] | None = None


class FeatureWiringResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    ai_product_id: uuid.UUID
    ai_feature_id: uuid.UUID
    status: str
    configuration: dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class FeatureWiringListResponse(BaseModel):
    items: list[FeatureWiringResponse]
    total: int