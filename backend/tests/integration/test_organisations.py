from __future__ import annotations

from tests.integration.identity_helpers import SETUP_URL, setup_payload


def test_super_admin_can_manage_and_search_organisations(identity_rig):
    client = identity_rig.client
    setup = client.post(SETUP_URL, json=setup_payload())
    assert setup.status_code == 201

    first = client.post(
        "/api/v1/organisations/create",
        json={"name": "alpha", "display_name": "Alpha Studio", "email": "alpha@example.com"},
    )
    second = client.post(
        "/api/v1/organisations/create",
        json={"name": "beta", "display_name": "Beta Studio", "email": "beta@example.com"},
    )
    assert first.status_code == second.status_code == 201
    first_id = first.json()["id"]

    listed = client.get("/api/v1/organisations?search=Alpha")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == first_id

    suspended = client.post(f"/api/v1/organisations/{first_id}/suspend")
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"

    forged = client.get("/api/v1/organisations/00000000-0000-0000-0000-000000000000")
    assert forged.status_code == 404