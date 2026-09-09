"""SQLAlchemy implementations of the identity repository ports."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.domain.models import AdminStatus, OrganisationUser, OrganisationUserStatus, PlatformAdmin
from app.modules.identity.domain.ports import (
    IdentityUnitOfWork,
    OrganisationUserRepository,
    PlatformAdminRepository,
    PlatformSettingsRepository,
)
from app.modules.organisations.infrastructure.models import OrganisationUserModel
from app.modules.identity.infrastructure.models import (
    PlatformAdminModel,
    PlatformSettingModel,
)


def _aware(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat stored values as UTC."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class SqlAlchemyPlatformAdminRepository(PlatformAdminRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists_any(self) -> bool:
        result = await self._session.execute(select(PlatformAdminModel.id).limit(1))
        return result.scalar_one_or_none() is not None

    async def get_by_email(self, email: str) -> PlatformAdmin | None:
        result = await self._session.execute(
            select(PlatformAdminModel).where(PlatformAdminModel.email == email)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def get_by_id(self, admin_id: uuid.UUID) -> PlatformAdmin | None:
        row = await self._session.get(PlatformAdminModel, admin_id)
        return self._to_domain(row) if row else None

    async def add(self, admin: PlatformAdmin) -> PlatformAdmin:
        model = PlatformAdminModel(
            id=admin.id,
            email=admin.email,
            full_name=admin.full_name,
            password_hash=admin.password_hash,
            status=admin.status.value,
            failed_login_attempts=admin.failed_login_attempts,
            locked_until=admin.locked_until,
            last_login_at=admin.last_login_at,
        )
        self._session.add(model)
        await self._session.flush()
        return admin

    async def update(self, admin: PlatformAdmin) -> None:
        model = await self._session.get(PlatformAdminModel, admin.id)
        if model is None:
            return
        model.full_name = admin.full_name
        model.status = admin.status.value
        model.failed_login_attempts = admin.failed_login_attempts
        model.locked_until = admin.locked_until
        model.last_login_at = admin.last_login_at
        await self._session.flush()

    @staticmethod
    def _to_domain(model: PlatformAdminModel) -> PlatformAdmin:
        return PlatformAdmin(
            id=model.id,
            email=model.email,
            full_name=model.full_name,
            password_hash=model.password_hash,
            status=AdminStatus(model.status),
            failed_login_attempts=model.failed_login_attempts,
            locked_until=_aware(model.locked_until),
            last_login_at=_aware(model.last_login_at),
            created_at=_aware(model.created_at),
            updated_at=_aware(model.updated_at),
        )


class SqlAlchemyPlatformSettingsRepository(PlatformSettingsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> str | None:
        result = await self._session.execute(
            select(PlatformSettingModel.value).where(PlatformSettingModel.key == key)
        )
        return result.scalar_one_or_none()

    async def set_once(self, key: str, value: str) -> bool:
        try:
            # Savepoint keeps the outer transaction usable after a unique violation.
            async with self._session.begin_nested():
                self._session.add(PlatformSettingModel(key=key, value=value))
                await self._session.flush()
            return True
        except IntegrityError:
            return False


class SqlAlchemyOrganisationUserRepository(OrganisationUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> OrganisationUser | None:
        result = await self._session.execute(select(OrganisationUserModel).where(OrganisationUserModel.email == email))
        rows = list(result.scalars().all())
        return self._to_domain(rows[0]) if len(rows) == 1 else None

    async def get_by_id(self, user_id: uuid.UUID) -> OrganisationUser | None:
        row = await self._session.get(OrganisationUserModel, user_id)
        return self._to_domain(row) if row else None

    @staticmethod
    def _to_domain(model: OrganisationUserModel) -> OrganisationUser:
        return OrganisationUser(id=model.id, organisation_id=model.organisation_id, email=model.email, display_name=model.display_name, password_hash=model.password_hash, role=model.role, status=OrganisationUserStatus(model.status), force_password_change=model.force_password_change, failed_login_attempts=model.failed_login_attempts, locked_until=_aware(model.locked_until), last_login_at=_aware(model.last_login_at))


class SqlAlchemyIdentityUnitOfWork(IdentityUnitOfWork):
    """One AsyncSession per request; use cases decide when to commit."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._admins = SqlAlchemyPlatformAdminRepository(session)
        self._settings = SqlAlchemyPlatformSettingsRepository(session)
        self._users = SqlAlchemyOrganisationUserRepository(session)

    @property
    def admins(self) -> SqlAlchemyPlatformAdminRepository:
        return self._admins

    @property
    def settings(self) -> SqlAlchemyPlatformSettingsRepository:
        return self._settings

    @property
    def users(self) -> SqlAlchemyOrganisationUserRepository:
        return self._users

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
