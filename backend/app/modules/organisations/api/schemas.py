from __future__ import annotations

import uuid
from datetime import datetime

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrganisationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    display_name: str = Field(min_length=2, max_length=200)
    email: str
    phone: str | None = None
    address: str | None = None
    logo: str | None = None
    admin_email: str | None = None
    admin_display_name: str | None = None
    admin_password: str | None = Field(default=None, min_length=8)


class OrganisationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    display_name: str | None = Field(default=None, min_length=2, max_length=200)
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    logo: str | None = None


class OrganisationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    display_name: str
    email: str
    phone: str | None
    address: str | None
    logo: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class OrganisationListResponse(BaseModel):
    items: list[OrganisationResponse]
    total: int


class OrganisationUserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    temporary_password: str = Field(min_length=12, max_length=1024)
    role: str


class OrganisationUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    organisation_id: uuid.UUID
    display_name: str
    email: str
    role: str
    status: str
    force_password_change: bool
    failed_login_attempts: int
    last_login_at: datetime | None


class PasswordResetRequest(BaseModel):
    temporary_password: str = Field(min_length=12, max_length=1024)


class LoginHistoryResponse(BaseModel):
    id: uuid.UUID
    succeeded: bool
    ip_address: str | None
    user_agent: str | None
    reason: str | None
    created_at: datetime