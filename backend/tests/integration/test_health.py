def test_liveness_endpoint(client):
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_returns_dependency_checks(client):
    response = client.get("/api/v1/readyz")
    assert response.status_code in (200, 503)
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert set(body["checks"]) == {"database", "redis"}


def test_request_id_is_generated_and_echoed(client):
    response = client.get("/api/v1/healthz")
    assert "x-request-id" in response.headers


def test_request_id_is_forwarded_when_provided(client):
    response = client.get("/api/v1/healthz", headers={"X-Request-ID": "test-correlation-id"})
    assert response.headers["x-request-id"] == "test-correlation-id"
