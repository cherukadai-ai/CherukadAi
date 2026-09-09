"""Authentication behavior (Phase 3): login, logout, account status,
failed-login tracking/lockout, rate limiting, and auth middleware."""
from __future__ import annotations

from sqlalchemy import update

from app.modules.identity.infrastructure.models import PlatformAdminModel
from tests.integration.identity_helpers import (
    LOGIN_URL,
    LOGOUT_URL,
    ME_URL,
    SETUP_URL,
    VALID_PASSWORD,
    get_admin_row,
    setup_payload,
)


def _create_admin(client, email: str = "admin@example.com", password: str = VALID_PASSWORD):
    response = client.post(SETUP_URL, json=setup_payload(email=email, password=password))
    assert response.status_code == 201
    return response


async def test_login_with_valid_credentials_succeeds(identity_rig):
    client = identity_rig.client
    _create_admin(client)
    client.post(LOGOUT_URL)  # clear the auto-login session from setup

    response = client.post(
        LOGIN_URL, json={"email": "ADMIN@example.com", "password": VALID_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin@example.com"
    assert body["isPlatformAdmin"] is True
    assert client.cookies.get("cherukadai_session")

    me = client.get(ME_URL)
    assert me.status_code == 200
    assert me.json()["userId"] == body["userId"]

    row = await get_admin_row(identity_rig.session_factory, "admin@example.com")
    assert row.failed_login_attempts == 0
    assert row.last_login_at is not None


async def test_login_with_wrong_password_is_rejected_and_tracked(identity_rig):
    client = identity_rig.client
    _create_admin(client)

    response = client.post(
        LOGIN_URL, json={"email": "admin@example.com", "password": "Wr0ngPassw0rd1"}
    )

    assert response.status_code == 401
    assert response.json()["title"] == "invalid_credentials"

    row = await get_admin_row(identity_rig.session_factory, "admin@example.com")
    assert row.failed_login_attempts == 1
    assert row.locked_until is None


async def test_login_with_unknown_email_returns_same_generic_error(identity_rig):
    """No account enumeration: unknown email and wrong password look identical."""
    client = identity_rig.client
    _create_admin(client)

    unknown = client.post(
        LOGIN_URL, json={"email": "ghost@example.com", "password": "Wr0ngPassw0rd1"}
    )
    wrong_password = client.post(
        LOGIN_URL, json={"email": "admin@example.com", "password": "Wr0ngPassw0rd1"}
    )

    assert unknown.status_code == 401
    assert wrong_password.status_code == 401
    assert unknown.json()["title"] == wrong_password.json()["title"] == "invalid_credentials"
    assert unknown.json()["detail"] == wrong_password.json()["detail"]


async def test_disabled_admin_cannot_login_and_loses_existing_session(identity_rig):
    client = identity_rig.client
    _create_admin(client)
    assert client.get(ME_URL).status_code == 200

    # Disable the account directly at the persistence layer (admin action).
    async with identity_rig.session_factory() as session:
        await session.execute(
            update(PlatformAdminModel)
            .where(PlatformAdminModel.email == "admin@example.com")
            .values(status="disabled")
        )
        await session.commit()

    # Existing session is immediately invalid...
    assert client.get(ME_URL).status_code == 401

    # ...and fresh logins are refused even with the correct password.
    response = client.post(
        LOGIN_URL, json={"email": "admin@example.com", "password": VALID_PASSWORD}
    )
    assert response.status_code == 403
    assert response.json()["title"] == "account_disabled"


async def test_account_locks_after_max_failed_attempts(identity_rig):
    client = identity_rig.client
    _create_admin(client)

    for _ in range(5):  # MAX_FAILED_LOGIN_ATTEMPTS default
        response = client.post(
            LOGIN_URL, json={"email": "admin@example.com", "password": "Wr0ngPassw0rd1"}
        )
        assert response.status_code == 401

    row = await get_admin_row(identity_rig.session_factory, "admin@example.com")
    assert row.failed_login_attempts == 5
    assert row.locked_until is not None

    # Even the correct password is refused while locked.
    locked = client.post(
        LOGIN_URL, json={"email": "admin@example.com", "password": VALID_PASSWORD}
    )
    assert locked.status_code == 403
    assert locked.json()["title"] == "account_locked"


async def test_login_rate_limit_rejects_excess_attempts(identity_rig):
    client = identity_rig.client

    last_status = None
    for _ in range(10):  # LOGIN_RATE_LIMIT_ATTEMPTS default
        response = client.post(
            LOGIN_URL, json={"email": "ghost@example.com", "password": "Wr0ngPassw0rd1"}
        )
        assert response.status_code == 401
        last_status = response.status_code
    assert last_status == 401

    blocked = client.post(
        LOGIN_URL, json={"email": "ghost@example.com", "password": "Wr0ngPassw0rd1"}
    )
    assert blocked.status_code == 429
    assert blocked.json()["title"] == "rate_limit_exceeded"


async def test_unauthenticated_requests_are_rejected(identity_rig):
    client = identity_rig.client

    me = client.get(ME_URL)
    assert me.status_code == 401
    assert me.json()["title"] == "unauthorized"

    logout = client.post(LOGOUT_URL)
    assert logout.status_code == 401

    # A forged/unknown session cookie is not accepted either.
    forged = client.get(ME_URL, cookies={"cherukadai_session": "forged-token-value"})
    assert forged.status_code == 401


async def test_logout_revokes_the_session_server_side(identity_rig):
    client = identity_rig.client
    _create_admin(client)
    assert client.get(ME_URL).status_code == 200

    logout = client.post(LOGOUT_URL)
    assert logout.status_code == 204

    # Same token can never be used again — revocation is server-side, and the
    # cookie is cleared from the jar.
    assert client.get(ME_URL).status_code == 401
    assert client.cookies.get("cherukadai_session") is None


async def test_session_from_setup_is_revoked_by_logout(identity_rig):
    client = identity_rig.client
    _create_admin(client)
    token = client.cookies.get("cherukadai_session")
    assert token

    client.post(LOGOUT_URL)

    replay = client.get(ME_URL, cookies={"cherukadai_session": token})
    assert replay.status_code == 401
