from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RegistryCreate(BaseModel):
    code: str = Field(min_length=2, max_length=100, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    product_id: uuid.UUID
    configuration: dict[str, Any] = Field(default_factory=dict)


class ProductCreate(BaseModel):
    code: str = Field(min_length=2, max_length=100, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)


class ModelCreate(RegistryCreate):
    provider: str = Field(min_length=1, max_length=120)


class RegistryUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=100, pattern=r"^[A-Z0-9_]+$")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    product_id: uuid.UUID | None = None
    configuration: dict[str, Any] | None = None


class ModelUpdate(RegistryUpdate):
    provider: str | None = Field(default=None, min_length=1, max_length=120)


class RegistryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    product_id: uuid.UUID
    status: str
    version: int
    configuration: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    status: str
    version: int
    configuration: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ModelResponse(RegistryResponse):
    provider: str


class RegistryListResponse(BaseModel):
    items: list[Any]
    total: int