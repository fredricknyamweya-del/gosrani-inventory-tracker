"""Health endpoint tests."""


def test_health_returns_api_envelope_without_caching(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"data": {"status": "ok"}}
    assert response.headers["Cache-Control"] == "no-store"
