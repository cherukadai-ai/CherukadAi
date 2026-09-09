"""Session stores: Redis-backed (production) and in-memory (tests/single-process).

Sessions are opaque random tokens stored server-side only. The store key is the
SHA-256 digest of the token — the raw token exists solely in the client's
HTTP-only cookie and is never persisted.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from redis.asyncio import Redis

from app.modules.identity.domain.models import PlatformAdmin, SessionRecord
from app.modules.identity.domain.ports import SessionStore

_KEY_PREFIX = "identity:session:"


def _storage_key(token: str) -> str:
    return _KEY_PREFIX + hashlib.sha256(token.encode("utf-8")).hexdigest()


def _serialize(record: SessionRecord) -> str:
    return json.dumps(
        {
            "principal_id": str(record.principal_id),
            "email": record.email,
            "expires_at": record.expires_at.isoformat(),
            "is_platform_admin": record.is_platform_admin,
            "organisation_id": str(record.organisation_id) if record.organisation_id else None,
            "display_name": record.display_name,
            "permissions": sorted(record.permissions),
        }
    )


def _deserialize(raw: str) -> SessionRecord:
    data = json.loads(raw)
    expires_at = datetime.fromisoformat(data["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    principal_id = data.get("principal_id") or data.get("admin_id")
    return SessionRecord(
        principal_id=uuid.UUID(principal_id),
        email=data["email"],
        expires_at=expires_at,
        is_platform_admin=data.get("is_platform_admin", True),
        organisation_id=uuid.UUID(data["organisation_id"]) if data.get("organisation_id") else None,
        display_name=data.get("display_name", ""),
        permissions=frozenset(data.get("permissions", [])),
    )


class RedisSessionStore(SessionStore):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def create(self, admin: PlatformAdmin, ttl_seconds: int) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        record = SessionRecord(principal_id=admin.id, email=admin.email, expires_at=expires_at, display_name=admin.full_name)
        await self._redis.set(_storage_key(token), _serialize(record), ex=ttl_seconds)
        return token, expires_at

    async def create_user(self, user_id, email, display_name, organisation_id, permissions, ttl_seconds):
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        record = SessionRecord(principal_id=user_id, email=email, expires_at=expires_at, is_platform_admin=False, organisation_id=organisation_id, display_name=display_name, permissions=permissions)
        await self._redis.set(_storage_key(token), _serialize(record), ex=ttl_seconds)
        return token, expires_at

    async def resolve(self, token: str) -> SessionRecord | None:
        raw = await self._redis.get(_storage_key(token))
        if raw is None:
            return None
        return _deserialize(raw)

    async def revoke(self, token: str) -> None:
        await self._redis.delete(_storage_key(token))


class InMemorySessionStore(SessionStore):
    """Process-local store used by tests and single-process local runs."""

    def __init__(self) -> None:
        self._records: dict[str, SessionRecord] = {}

    async def create(self, admin: PlatformAdmin, ttl_seconds: int) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        self._records[_storage_key(token)] = SessionRecord(
            principal_id=admin.id, email=admin.email, expires_at=expires_at, display_name=admin.full_name
        )
        return token, expires_at

    async def create_user(self, user_id, email, display_name, organisation_id, permissions, ttl_seconds):
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        self._records[_storage_key(token)] = SessionRecord(principal_id=user_id, email=email, expires_at=expires_at, is_platform_admin=False, organisation_id=organisation_id, display_name=display_name, permissions=permissions)
        return token, expires_at

    async def resolve(self, token: str) -> SessionRecord | None:
        record = self._records.get(_storage_key(token))
        if record is None:
            return None
        if record.expires_at <= datetime.now(timezone.utc):
            del self._records[_storage_key(token)]
            return None
        return record

    async def revoke(self, token: str) -> None:
        self._records.pop(_storage_key(token), None)
