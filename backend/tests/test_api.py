from uuid import uuid4

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


def test_parent_registration_and_login() -> None:
    email = f"parent-{uuid4()}@example.com"
    registered = client.post("/api/auth/register", json={
        "email": email, "password": "Long-Test-Password-2026", "full_name": "Test Veli"
    })
    assert registered.status_code == 201
    assert registered.json()["role"] == "parent"
    login = client.post("/api/auth/login", json={
        "email": email, "password": "Long-Test-Password-2026"
    })
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["access_token"]


def test_parent_can_create_student_only_with_consent() -> None:
    email = f"parent-{uuid4()}@example.com"
    client.post("/api/auth/register", json={
        "email": email, "password": "Long-Test-Password-2026", "full_name": "Test Veli"
    })
    token = client.post("/api/auth/login", json={
        "email": email, "password": "Long-Test-Password-2026"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    denied = client.post("/api/auth/students", headers=headers, json={
        "email": f"child-{uuid4()}@example.com", "password": "Long-Child-Password-2026",
        "full_name": "Test Öğrenci", "grade_level": 4, "consent_confirmed": False
    })
    assert denied.status_code == 422
    created = client.post("/api/auth/students", headers=headers, json={
        "email": f"child-{uuid4()}@example.com", "password": "Long-Child-Password-2026",
        "full_name": "Test Öğrenci", "grade_level": 4, "consent_confirmed": True
    })
    assert created.status_code == 201
    assert created.json()["role"] == "student"
    students = client.get("/api/auth/students", headers=headers)
    assert students.status_code == 200
    assert len(students.json()) == 1


def test_curriculum_write_requires_admin() -> None:
    response = client.post("/api/curriculum/subjects", json={
        "grade_level": 4, "name": "Matematik", "curriculum_version": "test"
    })
    assert response.status_code == 401
