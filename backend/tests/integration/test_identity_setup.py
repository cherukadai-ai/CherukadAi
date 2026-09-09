"""First-time Super Admin setup (Phase 3).

Covers: first admin creation, permanent rejection of further setup attempts,
password validation, and the guarantee that passwords are never stored in
plaintext or returned by the API.
"""
from __future__ import annotations

from app.core.security import verify_password
from tests.integration.identity_helpers import (
    LOGIN_URL,
    ME_URL,
    SETUP_STATUS_URL,
    SETUP_URL,
    VALID_PASSWORD,
    assert_no_password_material,
    get_admin_row,
    setup_payload,
)


async def test_setup_status_reports_setup_required_initially(identity_rig):
    response = identity_rig.client.get(SETUP_STATUS_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["setupRequired"] is True
    assert body["setupTokenRequired"] is False


async def test_first_super_admin_can_be_created(identity_rig):
    client = identity_rig.client

    response = client.post(SETUP_URL, json=setup_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["isPlatformAdmin"] is True
    assert body["email"] == "admin@example.com"  # normalized to lowercase
    assert body["displayName"] == "Root Admin"
    assert body["userId"]

    # The caller is signed in immediately via an HTTP-only session cookie.
    cookie = client.cookies.get("cherukadai_session")
    assert cookie
    set_cookie_header = response.headers["set-cookie"]
    assert "httponly" in set_cookie_header.lower()
    assert "samesite=lax" in set_cookie_header.lower()

    me = client.get(ME_URL)
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"


async def test_second_setup_attempt_is_permanently_rejected(identity_rig):
    client = identity_rig.client

    first = client.post(SETUP_URL, json=setup_payload())
    assert first.status_code == 201

    # Status endpoint flips and the endpoint closes — even for a different email.
    status_response = client.get(SETUP_STATUS_URL)
    assert status_response.json()["setupRequired"] is False

    second = client.post(SETUP_URL, json=setup_payload(email="other@example.com"))
    assert second.status_code == 403
    assert second.json()["title"] == "setup_already_completed"

    # Rejection is stable: repeated attempts keep failing.
    third = client.post(SETUP_URL, json=setup_payload(email="third@example.com"))
    assert third.status_code == 403

    # And no second account was created.
    assert await get_admin_row(identity_rig.session_factory, "other@example.com") is None


async def test_setup_rejects_short_password(identity_rig):
    response = identity_rig.client.post(SETUP_URL, json=setup_payload(password="Short1"))
    assert response.status_code == 422
    assert await get_admin_row(identity_rig.session_factory, "admin@example.com") is None


async def test_setup_rejects_password_without_digit(identity_rig):
    response = identity_rig.client.post(
        SETUP_URL, json=setup_payload(password="NoDigitsHereAtAll")
    )
    assert response.status_code == 422


async def test_setup_rejects_mismatched_password_confirmation(identity_rig):
    response = identity_rig.client.post(
        SETUP_URL,
        json=setup_payload(confirm_password="DifferentPassw0rd1"),
    )
    assert response.status_code == 422
    assert await get_admin_row(identity_rig.session_factory, "admin@example.com") is None


async def test_setup_rejects_invalid_email(identity_rig):
    response = identity_rig.client.post(SETUP_URL, json=setup_payload(email="not-an-email"))
    assert response.status_code == 422


async def test_password_is_stored_as_argon2_hash_never_plaintext(identity_rig):
    client = identity_rig.client
    response = client.post(SETUP_URL, json=setup_payload())
    assert response.status_code == 201

    row = await get_admin_row(identity_rig.session_factory, "admin@example.com")
    assert row is not None
    assert row.password_hash.startswith("$argon2")
    assert VALID_PASSWORD not in row.password_hash
    assert verify_password(VALID_PASSWORD, row.password_hash)


async def test_password_is_never_returned_by_any_endpoint(identity_rig):
    client = identity_rig.client

    setup_response = client.post(SETUP_URL, json=setup_payload())
    assert_no_password_material(setup_response.json(), setup_response.text, VALID_PASSWORD)

    client.post(LOGIN_URL, json={"email": "admin@example.com", "password": VALID_PASSWORD})
    login_response = client.post(
        LOGIN_URL, json={"email": "admin@example.com", "password": VALID_PASSWORD}
    )
    assert_no_password_material(login_response.json(), login_response.text, VALID_PASSWORD)

    me_response = client.get(ME_URL)
    assert_no_password_material(me_response.json(), me_response.text, VALID_PASSWORD)

    # Even failed attempts must not echo password material.
    bad_response = client.post(
        LOGIN_URL, json={"email": "admin@example.com", "password": "Wr0ngPassw0rd999"}
    )
    assert_no_password_material(bad_response.json(), bad_response.text, VALID_PASSWORD)
