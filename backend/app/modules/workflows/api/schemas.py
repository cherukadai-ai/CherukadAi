from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class WorkflowCreate(BaseModel):
    organisation_id: uuid.UUID
    slug: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class WorkflowStepInput(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    name: str | None = None
    type: str
    depends_on: list[str] = Field(default_factory=list)
    configuration: dict = Field(default_factory=dict)


class WorkflowVersionCreate(BaseModel):
    steps: list[WorkflowStepInput] = Field(min_length=1)


class WorkflowExecutionRequest(BaseModel):
    input_data: dict = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    id: uuid.UUID
    organisation_id: uuid.UUID
    slug: str
    name: str
    description: str | None
    status: str
    current_version: int
    published_version: int | None

    model_config = {"from_attributes": True}


class WorkflowVersionResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    version: int
    status: str
    definition: dict
    validated_at: datetime | None
    approved_at: datetime | None
    published_at: datetime | None

    model_config = {"from_attributes": True}
