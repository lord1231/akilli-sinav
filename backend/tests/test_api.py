from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_api_information() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"
    assert response.json()["version"] == app.version


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_auth_routes_are_registered() -> None:
    response = client.post("/api/auth/login", json={"email": "bad@example.com", "password": "wrong"})
    assert response.status_code == 401


def test_protected_profile_requires_token() -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_exam_routes_are_registered() -> None:
    response = client.get("/api/exams")
    assert response.status_code == 401
