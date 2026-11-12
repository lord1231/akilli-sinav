from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.routes.curriculum import validate_meb_source

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


def test_frontend_is_served() -> None:
    response = client.get("/app/")
    assert response.status_code == 200
    assert "Akıllı Sınav" in response.text


def test_auth_routes_are_registered() -> None:
    response = client.post("/api/auth/login", json={"email": "bad@example.com", "password": "wrong"})
    assert response.status_code == 401


def test_protected_profile_requires_token() -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_pdf_routes_require_authentication() -> None:
    exam_response = client.get("/api/exams/" + str(uuid4()) + "/results.pdf")
    parent_response = client.get("/api/auth/students/" + str(uuid4()) + "/progress.pdf")
    assert exam_response.status_code == 401
    assert parent_response.status_code == 401


def test_exam_routes_are_registered() -> None:
    response = client.get("/api/exams")
    assert response.status_code == 401
    rejected = client.post("/api/exams/" + str(uuid4()) + "/reject", json={"reason": "Kalite kontrolü başarısız."})
    assert rejected.status_code == 401


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



def test_parent_registration_is_rate_limited():
    responses = []
    for index in range(6):
        responses.append(client.post("/api/auth/register", json={
            "email": f"rate-parent-{uuid4()}@example.com",
            "password": "Long-Test-Password-2026",
            "full_name": f"Rate Test {index}",
        }))
    assert [response.status_code for response in responses[:5]] == [201] * 5
    assert responses[5].status_code == 429


def test_security_headers_are_present():
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    api_response = client.get("/api/auth/me")
    assert api_response.headers["cache-control"] == "no-store"


def test_exam_generation_is_rate_limited(monkeypatch):
    from app.db.session import SessionLocal
    from app.models import LearningOutcome, Subject, Unit
    from app.api.routes import exams as exam_routes

    parent_email = f"exam-limit-parent-{uuid4()}@example.com"
    client.post("/api/auth/register", json={
        "email": parent_email, "password": "Long-Test-Password-2026", "full_name": "Sınav Veli"
    })
    parent_token = client.post("/api/auth/login", json={
        "email": parent_email, "password": "Long-Test-Password-2026"
    }).json()["access_token"]
    headers = {"Authorization": f"Bearer {parent_token}"}
    student = client.post("/api/auth/students", headers=headers, json={
        "email": f"exam-limit-student-{uuid4()}@example.com",
        "password": "Long-Child-Password-2026", "full_name": "Sınav Öğrenci",
        "grade_level": 4, "consent_confirmed": True,
    })
    assert student.status_code == 201

    with SessionLocal() as db:
        subject = Subject(grade_level=4, name=f"Test Matematik {uuid4()}",
                          curriculum_version="test")
        db.add(subject)
        db.flush()
        unit = Unit(subject_id=subject.id, name="Test Ünitesi", order_no=1)
        db.add(unit)
        db.flush()
        outcome = LearningOutcome(unit_id=unit.id, code="TEST.4.1",
                                  description="Test kazanımı")
        db.add(outcome)
        db.commit()
        outcome_id = str(outcome.id)

    def reject_generation(*args, **kwargs):
        raise ValueError("mock generation")

    monkeypatch.setattr(exam_routes, "generate_questions", reject_generation)
    payload = {"student_id": student.json()["id"], "learning_outcome_id": outcome_id,
               "title": "Limit testi"}
    responses = [client.post("/api/exams/generate", headers=headers, json=payload)
                 for _ in range(11)]
    assert all(response.status_code == 502 for response in responses[:10])
    assert responses[10].status_code == 429

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
    student_id = created.json()["id"]
    progress = client.get("/api/auth/students/" + student_id + "/progress", headers=headers)
    assert progress.status_code == 200
    assert progress.json()["completed_exam_count"] == 0
    assert progress.json()["total_questions"] == 0
    assert progress.json()["unanswered_questions"] == 0
    report = client.get("/api/auth/students/" + student_id + "/progress.pdf", headers=headers)
    assert report.status_code == 200
    assert report.headers["content-type"] == "application/pdf"
    assert report.content.startswith(b"%PDF")

    unrelated_email = f"unrelated-{uuid4()}@example.com"
    client.post("/api/auth/register", json={
        "email": unrelated_email, "password": "Long-Test-Password-2026", "full_name": "Diğer Veli"
    })
    unrelated_token = client.post("/api/auth/login", json={
        "email": unrelated_email, "password": "Long-Test-Password-2026"
    }).json()["access_token"]
    unrelated_headers = {"Authorization": f"Bearer {unrelated_token}"}
    hidden_report = client.get(
        "/api/auth/students/" + student_id + "/progress.pdf", headers=unrelated_headers
    )
    assert hidden_report.status_code == 404

    student_token = client.post("/api/auth/login", json={
        "email": created.json()["email"], "password": "Long-Child-Password-2026"
    }).json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}
    forbidden_report = client.get(
        "/api/auth/students/" + student_id + "/progress.pdf", headers=student_headers
    )
    assert forbidden_report.status_code == 403


def test_curriculum_write_requires_admin() -> None:
    response = client.post("/api/curriculum/subjects", json={
        "grade_level": 4, "name": "Matematik", "curriculum_version": "test"
    })
    assert response.status_code == 401


def test_curriculum_import_rejects_non_meb_source() -> None:
    with pytest.raises(ValueError):
        validate_meb_source("https://example.com/fake-curriculum.pdf")



@pytest.mark.parametrize("url", [
    "https://tymm.meb.gov.tr/Programlar",
    "https://mufredat.meb.gov.tr/Dosyalar/program.pdf",
    "https://dogm.meb.gov.tr/Programlar/Ortaokul/2026004-Dkab-orta.pdf",
])
def test_official_meb_sources_are_accepted(url: str) -> None:
    assert validate_meb_source(url) == url


@pytest.mark.parametrize("url", [
    "http://tymm.meb.gov.tr/program.pdf",
    "https://example.com/fake-curriculum.pdf",
    "https://tymm.meb.gov.tr.example.com/program.pdf",
    "https://user:password@tymm.meb.gov.tr/program.pdf",
    "https://tymm.meb.gov.tr:8443/program.pdf",
])
def test_unsafe_or_non_official_sources_are_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        validate_meb_source(url)


def test_exam_rejection_reason_validation() -> None:
    from app.schemas import ExamRejectRequest

    assert ExamRejectRequest(reason="  Eksik kazanım  ").reason == "Eksik kazanım"
    with pytest.raises(Exception):
        ExamRejectRequest(reason="   ")


def test_students_can_open_only_published_or_completed_exams() -> None:
    from app.api.routes.exams import student_can_open_exam

    assert student_can_open_exam("published") is True
    assert student_can_open_exam("completed") is True
    assert student_can_open_exam("pending_review") is False
    assert student_can_open_exam("rejected") is False



def test_student_exam_question_payload_never_exposes_answer_key() -> None:
    from app.api.routes.exams import student_question_payload

    exam_question = SimpleNamespace(id=uuid4(), position=1)
    question = SimpleNamespace(
        prompt="2 + 2 kaçtır?",
        options=[{"key": "A", "text": "3"}, {"key": "B", "text": "4"}],
        correct_option="B",
        explanation="Toplama işleminin sonucu 4'tür.",
        is_reviewed=True,
    )

    payload = student_question_payload(exam_question, question)

    assert payload["prompt"] == "2 + 2 kaçtır?"
    assert payload["options"] == question.options
    assert set(payload) == {"id", "position", "prompt", "options"}
    assert "correct_option" not in payload
    assert "explanation" not in payload
    assert "is_reviewed" not in payload


def test_password_reset_token_hash_is_one_way_and_stable() -> None:
    from app.api.routes.auth import _password_reset_hash

    token = "a-long-random-reset-token-value"
    digest = _password_reset_hash(token)
    assert digest == _password_reset_hash(token)
    assert digest != token
    assert len(digest) == 64


def test_password_recovery_routes_are_registered() -> None:
    routes = set(app.openapi()["paths"])
    assert "/api/auth/password/forgot" in routes
    assert "/api/auth/password/reset" in routes


def test_password_reset_flow_sends_single_use_link_and_changes_password(monkeypatch) -> None:
    from urllib.parse import parse_qs, urlparse
    from app.api.routes import auth as auth_routes

    email = f"recovery-{uuid4()}@example.com"
    old_password = "Old-Long-Password-2026"
    new_password = "New-Long-Password-2026"
    registered = client.post("/api/auth/register", json={
        "email": email, "password": old_password, "full_name": "Recovery Test"
    })
    assert registered.status_code == 201

    sent = []
    monkeypatch.setattr(
        auth_routes, "send_password_reset_email",
        lambda to_email, reset_url: sent.append((to_email, reset_url)),
    )
    requested = client.post("/api/auth/password/forgot", json={"email": email})
    assert requested.status_code == 200
    assert requested.json()["message"] == "E-posta adresi kayıtlıysa parola yenileme bağlantısı gönderildi."
    assert len(sent) == 1 and sent[0][0] == email

    parsed_reset_url = urlparse(sent[0][1])
    assert parsed_reset_url.query == ""
    token = parse_qs(parsed_reset_url.fragment)["reset_token"][0]
    reset = client.post("/api/auth/password/reset", json={
        "token": token, "new_password": new_password
    })
    assert reset.status_code == 200
    assert client.post("/api/auth/password/reset", json={
        "token": token, "new_password": "Another-Long-Password-2026"
    }).status_code == 400

    assert client.post("/api/auth/login", json={
        "email": email, "password": old_password
    }).status_code == 401
    assert client.post("/api/auth/login", json={
        "email": email, "password": new_password
    }).status_code == 200

def test_exam_deadline_uses_server_start_time_and_duration():
    from datetime import datetime, timedelta, timezone
    from app.api.routes.exams import exam_deadline

    started = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)
    exam = SimpleNamespace(started_at=started, duration_minutes=30)
    assert exam_deadline(exam) == started + timedelta(minutes=30)


def test_exam_deadline_is_missing_before_student_starts_exam():
    from app.api.routes.exams import exam_deadline

    assert exam_deadline(SimpleNamespace(started_at=None, duration_minutes=30)) is None
