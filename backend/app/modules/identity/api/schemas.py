"""Request/response DTOs for the identity API.

Responses never contain password material: there is intentionally no field for
passwords or password hashes in any response model.
"""
from __future__ import annotations

import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from app.modules.identity.domain.models import AuthenticatedPrincipal, PlatformAdmin

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SetupStatusResponse(CamelModel):
    setup_required: bool
    setup_token_required: bool


class SetupSuperAdminRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)
    confirm_password: str = Field(min_length=1, max_length=1024)
    setup_token: str | None = Field(default=None, max_length=256)

    @field_validator("email")
    @classmethod
    def _email_format(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("A valid email address is required.")
        return value

    @model_validator(mode="after")
    def _passwords_match(self) -> SetupSuperAdminRequest:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def _email_format(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("A valid email address is required.")
        return value


class OrganisationLoginRequest(LoginRequest):
    organisation_id: uuid.UUID


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=12, max_length=1024)


class PlatformAdminSessionResponse(CamelModel):
    """The session payload returned by setup/login/me. No credentials included."""

    user_id: uuid.UUID
    email: str
    display_name: str
    is_platform_admin: bool = True

    @classmethod
    def from_admin(cls, admin: PlatformAdmin) -> PlatformAdminSessionResponse:
        return cls(
            user_id=admin.id,
            email=admin.email,
            display_name=admin.full_name,
            is_platform_admin=True,
        )

    @classmethod
    def from_principal(cls, principal: AuthenticatedPrincipal) -> PlatformAdminSessionResponse:
        return cls(
            user_id=principal.admin_id,
            email=principal.email,
            display_name=principal.full_name,
            is_platform_admin=principal.is_platform_admin,
        )


class OrganisationSessionResponse(CamelModel):
    user_id: uuid.UUID
    organisation_id: uuid.UUID
    email: str
    display_name: str
    is_platform_admin: bool = False
    permissions: list[str]
    force_password_change: bool


