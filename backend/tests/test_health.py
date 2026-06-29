def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_response_shape(client):
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert isinstance(data["uptime_seconds"], float)
    assert data["uptime_seconds"] >= 0
