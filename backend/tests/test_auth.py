from fastapi.testclient import TestClient
from app.main import app


def test_health_is_public(monkeypatch):
    monkeypatch.setenv("BACKEND_API_KEY", "secret")
    assert TestClient(app).get("/health").status_code == 200


def test_protected_endpoint_requires_api_key(monkeypatch):
    monkeypatch.setenv("BACKEND_API_KEY", "secret")
    client = TestClient(app)
    assert client.get("/jobs").status_code == 401
    assert client.get("/jobs", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/jobs", headers={"X-API-Key": "secret"}).status_code == 200


def test_missing_server_key_fails_closed(monkeypatch):
    monkeypatch.delenv("BACKEND_API_KEY", raising=False)
    assert TestClient(app).get("/jobs").status_code == 401
