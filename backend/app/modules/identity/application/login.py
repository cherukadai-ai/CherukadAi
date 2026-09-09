"""Use case: Super Admin login with rate limiting and failed-attempt tracking."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application.base import UseCase
from app.core.exceptions import RateLimitExceededError
from app.modules.identity.domain.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    InvalidCredentialsError,
)
from app.modules.identity.domain.models import PlatformAdmin, utcnow
from app.modules.identity.domain.ports import (
    IdentityUnitOfWork,
    PasswordHasher,
    RateLimiter,
    SessionStore,
)

_INVALID_CREDENTIALS_MESSAGE = "Invalid email or password."


@dataclass(frozen=True)
class LoginInput:
    email: str
    password: str
    ip_address: str


@dataclass(frozen=True)
class LoginResult:
    admin: PlatformAdmin
    session_token: str
    session_expires_at: datetime


class Login(UseCase[LoginInput, LoginResult]):
    def __init__(
        self,
        uow: IdentityUnitOfWork,
        hasher: PasswordHasher,
        sessions: SessionStore,
        rate_limiter: RateLimiter,
        *,
        max_failed_attempts: int,
        lockout_seconds: int,
        rate_limit_attempts: int,
        rate_limit_window_seconds: int,
        session_ttl_seconds: int,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._sessions = sessions
        self._rate_limiter = rate_limiter
        self._max_failed_attempts = max_failed_attempts
        self._lockout_seconds = lockout_seconds
        self._rate_limit_attempts = rate_limit_attempts
        self._rate_limit_window_seconds = rate_limit_window_seconds
        self._session_ttl_seconds = session_ttl_seconds
        self._timing_equalization_hash: str | None = None

    async def execute(self, payload: LoginInput) -> LoginResult:
        email = payload.email.strip().lower()
        await self._enforce_rate_limit(email, payload.ip_address)

        admin = await self._uow.admins.get_by_email(email)
        if admin is None:
            self._equalize_timing(payload.password)
            raise InvalidCredentialsError(_INVALID_CREDENTIALS_MESSAGE)

        now = utcnow()
        if not admin.is_active:
            raise AccountDisabledError("This account has been disabled.")
        if admin.is_locked(now):
            retry_after = int((admin.locked_until - now).total_seconds()) if admin.locked_until else 0
            raise AccountLockedError(
                "This account is temporarily locked after too many failed attempts. "
                "Try again later.",
                retry_after_seconds=max(retry_after, 0),
            )

        if not self._hasher.verify(payload.password, admin.password_hash):
            await self._record_failed_attempt(admin, now)
            raise InvalidCredentialsError(_INVALID_CREDENTIALS_MESSAGE)

        admin.failed_login_attempts = 0
        admin.locked_until = None
        admin.last_login_at = now
        await self._uow.admins.update(admin)
        await self._uow.commit()

        token, expires_at = await self._sessions.create(admin, self._session_ttl_seconds)
        return LoginResult(admin=admin, session_token=token, session_expires_at=expires_at)

    async def _enforce_rate_limit(self, email: str, ip_address: str) -> None:
        window = self._rate_limit_window_seconds
        limit = self._rate_limit_attempts
        ip_allowed = await self._rate_limiter.hit(f"login:ip:{ip_address}", limit, window)
        email_allowed = await self._rate_limiter.hit(f"login:email:{email}", limit, window)
        if not (ip_allowed and email_allowed):
            raise RateLimitExceededError(
                "Too many login attempts. Try again later.",
                retry_after_seconds=window,
            )

    async def _record_failed_attempt(self, admin: PlatformAdmin, now: datetime) -> None:
        admin.failed_login_attempts += 1
        if admin.failed_login_attempts >= self._max_failed_attempts:
            admin.locked_until = now + timedelta(seconds=self._lockout_seconds)
        await self._uow.admins.update(admin)
        # Failed-attempt tracking must survive the 401 response — commit explicitly.
        await self._uow.commit()

    def _equalize_timing(self, password: str) -> None:
        """Run a verification against a dummy hash so unknown-email responses take
        the same time as wrong-password responses (no account enumeration via timing)."""
        if self._timing_equalization_hash is None:
            self._timing_equalization_hash = self._hasher.hash("timing-equalization-dummy")
        self._hasher.verify(password, self._timing_equalization_hash)
