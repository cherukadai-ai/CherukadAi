from __future__ import annotations

from tests.integration.identity_helpers import SETUP_URL, setup_payload


def _create_org(client, name: str) -> str:
    response = client.post("/api/v1/organisations/create", json={"name": name, "display_name": name, "email": f"{name}@example.com"})
    assert response.status_code == 201
    return response.json()["id"]


def test_phase5_rbac_isolation_disabled_users_and_password_lifecycle(identity_rig):
    client = identity_rig.client
    assert client.post(SETUP_URL, json=setup_payload()).status_code == 201
    org_a = _create_org(client, "alpha")
    org_b = _create_org(client, "beta")

    created = client.post(f"/api/v1/organisations/{org_a}/users/create", json={
        "name": "Alpha Manager", "email": "manager@example.com",
        "temporary_password": "TemporaryPassw0rd!", "role": "ORGANISATION_MANAGER",
    })
    assert created.status_code == 201
    user_id = created.json()["id"]
    assert created.json()["force_password_change"] is True

    user_client = identity_rig.client
    login = user_client.post("/api/v1/identity/organisation/login", json={
        "organisation_id": org_a, "email": "manager@example.com", "password": "TemporaryPassw0rd!",
    })
    assert login.status_code == 200
    assert "user.create" in login.json()["permissions"]
    assert "feature.configure" not in login.json()["permissions"]

    failed_login = user_client.post("/api/v1/identity/organisation/login", json={
        "organisation_id": org_a, "email": "manager@example.com", "password": "WrongPassword!",
    })
    assert failed_login.status_code == 401
    history = user_client.get(f"/api/v1/organisations/{org_a}/users/{user_id}/login-history")
    assert history.status_code == 200
    assert any(event["succeeded"] is False for event in history.json())

    cross_tenant = user_client.get(f"/api/v1/organisations/{org_b}/users")
    assert cross_tenant.status_code in (403, 404)
    forged_id = user_client.post(f"/api/v1/organisations/{org_a}/users/00000000-0000-0000-0000-000000000000/deactivate")
    assert forged_id.status_code == 403

    denied = user_client.post(f"/api/v1/organisations/{org_a}/users/create", json={
        "name": "Another", "email": "another@example.com", "temporary_password": "TemporaryPassw0rd!", "role": "USER",
    })
    assert denied.status_code == 201

    reset = user_client.post(f"/api/v1/organisations/{org_a}/users/{user_id}/password-reset", json={"temporary_password": "NewTemporaryPassw0rd!"})
    assert reset.status_code == 200

    # Re-authenticate the platform admin because the shared test client now has the user cookie.
    admin_login = client.post("/api/v1/identity/login", json={"email": "admin@example.com", "password": "Sup3rSecurePassw0rd!"})
    assert admin_login.status_code == 200
    disabled = client.post(f"/api/v1/organisations/{org_a}/users/{user_id}/deactivate")
    assert disabled.status_code == 200
    user_login = client.post("/api/v1/identity/organisation/login", json={"organisation_id": org_a, "email": "manager@example.com", "password": "TemporaryPassw0rd!"})
    assert user_login.status_code == 401