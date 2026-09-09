"""Use case: first-time Super Admin setup.

The gate is enforced server-side in two layers:
1. Fast path: a completed-setup marker or any existing admin closes setup.
2. Race-safe path: `settings.set_once` inserts the marker inside a unique-key
   transaction, so even concurrent first requests can create exactly one admin.
Once closed, setup is permanently closed — it never depends on frontend hiding.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.application.base import UseCase
from app.modules.identity.domain.exceptions import (
    InvalidSetupTokenError,
    SetupAlreadyCompletedError,
)
from app.modules.identity.domain.models import PlatformAdmin, utcnow
from app.modules.identity.domain.ports import (
    IdentityUnitOfWork,
    PasswordHasher,
)
from app.modules.identity.domain.services import PasswordPolicy

INITIAL_SETUP_COMPLETED_KEY = "initial_setup_completed"


@dataclass(frozen=True)
class SetupSuperAdminInput:
    full_name: str
    email: str
    password: str
    setup_token: str | None = None


@dataclass(frozen=True)
class SetupSuperAdminResult:
    admin: PlatformAdmin


class SetupSuperAdmin(UseCase[SetupSuperAdminInput, SetupSuperAdminResult]):
    def __init__(
        self,
        uow: IdentityUnitOfWork,
        hasher: PasswordHasher,
        policy: PasswordPolicy,
        *,
        required_setup_token: str | None = None,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._policy = policy
        self._required_setup_token = required_setup_token

    async def execute(self, payload: SetupSuperAdminInput) -> SetupSuperAdminResult:
        email = payload.email.strip().lower()
        full_name = payload.full_name.strip()

        if await self._is_setup_completed():
            raise SetupAlreadyCompletedError(
                "Initial setup has already been completed. Sign in instead."
            )

        # Optional second factor for first install, only when explicitly configured.
        if self._required_setup_token is not None and payload.setup_token != self._required_setup_token:
            raise InvalidSetupTokenError("A valid setup token is required for initial setup.")

        self._policy.validate(payload.password, email=email)

        admin = PlatformAdmin(
            id=uuid.uuid4(),
            email=email,
            full_name=full_name,
            password_hash=self._hasher.hash(payload.password),
        )

        # Write the completion marker first: the unique key makes this the
        # race-safe gate. If a concurrent request already wrote it, we refuse.
        if not await self._uow.settings.set_once(INITIAL_SETUP_COMPLETED_KEY, utcnow().isoformat()):
            raise SetupAlreadyCompletedError(
                "Initial setup has already been completed. Sign in instead."
            )
        await self._uow.admins.add(admin)
        await self._uow.commit()
        return SetupSuperAdminResult(admin=admin)

    async def _is_setup_completed(self) -> bool:
        if await self._uow.settings.get(INITIAL_SETUP_COMPLETED_KEY) is not None:
            return True
        return await self._uow.admins.exists_any()

    async def setup_required(self) -> bool:
        """Query used by the public status endpoint."""
        return not await self._is_setup_completed()
