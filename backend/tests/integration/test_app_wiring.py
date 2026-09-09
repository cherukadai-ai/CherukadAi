"""Verifies the module-boundary wiring itself (Phase 2 scope), not business logic."""

EXPECTED_MODULE_PREFIXES = {
    "/identity",
    "/organisations",
    "/users",
    "/permissions",
    "/ai",
    "/ai-orchestration",
    "/features",
    "/feature-wiring",
    "/agents",
    "/workflows",
    "/projects",
    "/files",
    "/audit",
    "/usage",
}


def test_openapi_schema_generates_without_errors(client):
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"]


def test_all_modules_are_wired_into_the_api(app):
    registered_prefixes = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        for prefix in EXPECTED_MODULE_PREFIXES:
            if path.startswith(f"/api/v1{prefix}"):
                registered_prefixes.add(prefix)

    assert registered_prefixes == EXPECTED_MODULE_PREFIXES


def test_no_duplicate_route_paths(app):
    paths = [getattr(route, "path", "") for route in app.routes]
    assert len(paths) == len(set(paths))
