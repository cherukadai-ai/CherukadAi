"""Shared helpers for identity integration tests."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.identity.infrastructure.models import PlatformAdminModel

SETUP_URL = "/api/v1/identity/setup"
SETUP_STATUS_URL = "/api/v1/identity/setup/status"
LOGIN_URL = "/api/v1/identity/login"
LOGOUT_URL = "/api/v1/identity/logout"
ME_URL = "/api/v1/identity/me"

VALID_PASSWORD = "Sup3rSecurePassw0rd!"


def setup_payload(
    *,
    email: str = "Admin@Example.com",
    full_name: str = "Root Admin",
    password: str = VALID_PASSWORD,
    confirm_password: str | None = None,
) -> dict[str, str]:
    return {
        "full_name": full_name,
        "email": email,
        "password": password,
        "confirm_password": confirm_password if confirm_password is not None else password,
    }


async def get_admin_row(
    session_factory: async_sessionmaker[AsyncSession], email: str
) -> PlatformAdminModel | None:
    async with session_factory() as session:
        result = await session.execute(
            select(PlatformAdminModel).where(PlatformAdminModel.email == email)
        )
        return result.scalar_one_or_none()


def assert_no_password_material(payload: object, raw_text: str, plaintext: str) -> None:
    """Recursively assert no response field carries password material."""

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                assert "password" not in str(key).lower(), f"leaked key: {key}"
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    assert plaintext not in raw_text
    assert "$argon2" not in raw_text
