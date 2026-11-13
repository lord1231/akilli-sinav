"""Sınav sisteminin uçtan uca testi: üretim -> inceleme -> çözme -> teslim -> sonuç.

Gemini taklit edilir; veritabanı her test için izole bellek SQLite'tır.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

import app.api.routes.exams as exams_module
from app.core.config import settings
from app.core.security import hash_password
from app.models import Exam, LearningOutcome, StudentAnswer, Subject, Unit, User
from app.services.curriculum_seed import seed_missing_curriculum
from app.services.question_generator import GeneratedQuestion

CURRICULUM_DIR = Path(__file__).resolve().parents[2] / "data" / "curriculum"
PASSWORD = "GucluParola12345"
CORRECT = ["A", "B", "C", "D"]


def fake_questions(*_a, **_k):
    return [
        GeneratedQuestion(
            prompt=f"Bu bir deneme sorusudur numara {i}?",
            options={"A": f"a{i}", "B": f"b{i}", "C": f"c{i}", "D": f"d{i}"},
            correct_option=CORRECT[i % 4], explanation=f"Açıklama {i} metni", difficulty="easy",
        )
        for i in range(25)
    ]


def login(client, email):
    r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture()
def world(client, factory, monkeypatch):
    seed_missing_curriculum(CURRICULUM_DIR, session_factory=factory)
    monkeypatch.setattr(exams_module, "generate_questions", fake_questions)
    sent = []
    monkeypatch.setattr(exams_module, "send_exam_result_email",
                        lambda email, title, score, correct, total: sent.append((email, score, correct, total)))
    with factory() as db:
        db.add(User(email="admin@example.com", password_hash=hash_password(PASSWORD),
                    full_name="Yönetici", role="admin"))
        db.commit()
    assert client.post("/api/auth/register", json={"email": "veli@example.com", "password": PASSWORD,
                                                    "full_name": "Veli Test"}).status_code == 201
    parent = login(client, "veli@example.com")
    for email, grade in (("ogrenci@example.com", 5), ("kucuk@example.com", 4)):
        r = client.post("/api/auth/students", headers=parent, json={
            "email": email, "password": PASSWORD, "full_name": "Öğrenci " + email[:3],
            "grade_level": grade, "consent_confirmed": True})
        assert r.status_code == 201, r.text
    students = {s["email"]: s["id"] for s in client.get("/api/auth/students", headers=parent).json()}
    with factory() as db:
        outcome = db.scalars(select(LearningOutcome).join(Unit).join(Subject).where(
            Subject.grade_level == 5, Subject.name == "Türkçe")).first()
        outcome_id = str(outcome.id)
    return {"client": client, "factory": factory, "parent": parent, "admin": login(client, "admin@example.com"),
            "student": login(client, "ogrenci@example.com"), "students": students,
            "outcome_id": outcome_id, "sent": sent}


def create_and_publish(w, title="Deneme sınavı"):
    c = w["client"]
    r = c.post("/api/exams/generate", headers=w["parent"], json={
        "student_id": w["students"]["ogrenci@example.com"], "learning_outcome_id": w["outcome_id"], "title": title})
    assert r.status_code == 201, r.text
    exam_id = r.json()["id"]
    assert r.json()["status"] == "pending_review" and r.json()["question_count"] == 25
    assert c.post(f"/api/exams/{exam_id}/approve", headers=w["admin"]).status_code == 200
    return exam_id


def test_full_exam_lifecycle_scores_correctly(world):
    c, w = world["client"], world
    exam_id = create_and_publish(w)

    # Yayımlanmadan önce öğrenci göremez; incelemedeyken sınav öğrenci listesinde yoktur.
    listed = c.get("/api/exams", headers=w["student"]).json()
    assert [e["status"] for e in listed] == ["published"]

    exam = c.get(f"/api/exams/{exam_id}", headers=w["student"]).json()
    assert len(exam["questions"]) == 25 and exam["server_time"] and exam["deadline_at"]
    assert all(set(q) == {"id", "position", "prompt", "options"} for q in exam["questions"]), "cevap anahtarı sızmamalı"
    assert [q["position"] for q in exam["questions"]] == list(range(1, 26))

    # 10 doğru, 5 yanlış, 10 boş
    for i, q in enumerate(exam["questions"][:15]):
        choice = CORRECT[i % 4] if i < 10 else CORRECT[(i + 1) % 4]
        r = c.post(f"/api/exams/{exam_id}/answers/{q['id']}", headers=w["student"], json={"selected_option": choice})
        assert r.status_code == 200
    assert c.post(f"/api/exams/{exam_id}/answers/{exam['questions'][0]['id']}", headers=w["student"],
                  json={"selected_option": "E"}).status_code == 422

    done = c.post(f"/api/exams/{exam_id}/submit", headers=w["student"])
    assert done.status_code == 200
    assert done.json() == {"exam_id": exam_id, "correct": 10, "total": 25, "score": 40, "status": "completed"}
    assert c.post(f"/api/exams/{exam_id}/submit", headers=w["student"]).status_code == 409
    assert c.post(f"/api/exams/{exam_id}/answers/{exam['questions'][20]['id']}", headers=w["student"],
                  json={"selected_option": "A"}).status_code == 409
    assert w["sent"] == [("veli@example.com", 40, 10, 25)]

    for who in ("student", "parent"):
        res = c.get(f"/api/exams/{exam_id}/results", headers=w[who]).json()
        assert res["score"] == 40 and res["question_count"] == 25
        assert sum(d["is_correct"] for d in res["details"]) == 10
        assert sum(d["selected_option"] is None for d in res["details"]) == 10
        assert all(d["correct_option"] in "ABCD" and d["explanation"] for d in res["details"])
    pdf = c.get(f"/api/exams/{exam_id}/results.pdf", headers=w["parent"])
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")


def test_unreviewed_and_rejected_exams_are_not_available_to_students(world):
    c, w = world["client"], world
    r = c.post("/api/exams/generate", headers=w["parent"], json={
        "student_id": w["students"]["ogrenci@example.com"], "learning_outcome_id": w["outcome_id"], "title": "İncelemede"})
    exam_id = r.json()["id"]
    assert c.get("/api/exams", headers=w["student"]).json() == [] or \
        c.get("/api/exams", headers=w["student"]).json()[0]["status"] == "pending_review"
    assert c.get(f"/api/exams/{exam_id}", headers=w["student"]).status_code == 409
    queue = c.get("/api/exams/review-queue", headers=w["admin"]).json()
    assert len(queue) == 1 and len(queue[0]["questions"]) == 25
    assert c.post(f"/api/exams/{exam_id}/approve", headers=w["parent"]).status_code == 403
    rej = c.post(f"/api/exams/{exam_id}/reject", headers=w["admin"], json={"reason": "Soru 3 belirsiz"})
    assert rej.status_code == 200 and rej.json()["status"] == "rejected"
    assert c.get(f"/api/exams/{exam_id}", headers=w["student"]).status_code == 409


def test_generation_guards(world, monkeypatch):
    c, w = world["client"], world
    body = {"student_id": w["students"]["kucuk@example.com"], "learning_outcome_id": w["outcome_id"], "title": "Sınıf uyuşmaz"}
    assert c.post("/api/exams/generate", headers=w["parent"], json=body).status_code == 400  # 4. sınıf öğrenci, 5. sınıf kazanım
    assert c.post("/api/exams/generate", headers=w["student"], json={
        **body, "student_id": w["students"]["ogrenci@example.com"]}).status_code == 403  # öğrenci sınav üretemez

    ok = {**body, "student_id": w["students"]["ogrenci@example.com"]}
    monkeypatch.undo()  # gerçek generate_questions: anahtar yok -> 503
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    assert c.post("/api/exams/generate", headers=w["parent"], json=ok).status_code == 503

    def broken(*_a, **_k):
        raise ValueError("Gemini 24 yerine 25 soru üretti.")
    monkeypatch.setattr(exams_module, "generate_questions", broken)
    assert c.post("/api/exams/generate", headers=w["parent"], json=ok).status_code == 502
    with w["factory"]() as db:
        assert db.scalars(select(Exam)).all() == [], "başarısız üretim yarım sınav bırakmamalı"


def _age_exam(w, exam_id, minutes):
    with w["factory"]() as db:
        exam = db.get(Exam, __import__("uuid").UUID(exam_id))
        exam.started_at = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        db.commit()


def test_overdue_exam_is_finalized_by_server_even_if_student_never_submits(world):
    c, w = world["client"], world
    exam_id = create_and_publish(w)
    exam = c.get(f"/api/exams/{exam_id}", headers=w["student"]).json()  # sınav başlar
    for q in exam["questions"][:5]:  # ilk 5 sorunun hepsini doğru işaretle
        c.post(f"/api/exams/{exam_id}/answers/{q['id']}", headers=w["student"],
               json={"selected_option": CORRECT[(q["position"] - 1) % 4]})
    _age_exam(w, exam_id, 45)  # öğrenci uygulamayı kapattı; süre ve tolerans doldu

    listed = c.get("/api/exams", headers=w["parent"]).json()  # veli listeyi açınca sunucu sonuçlandırır
    assert listed[0]["status"] == "completed" and listed[0]["score"] == 20
    assert w["sent"] == [("veli@example.com", 20, 5, 25)]
    assert c.get(f"/api/exams/{exam_id}/results", headers=w["parent"]).json()["score"] == 20
    assert c.post(f"/api/exams/{exam_id}/submit", headers=w["student"]).status_code == 409
    assert c.get("/api/exams", headers=w["parent"]).json()[0]["score"] == 20 and len(w["sent"]) == 1, "tekrar işlenmemeli"


def test_overdue_exam_opened_by_student_returns_completed_status(world):
    c, w = world["client"], world
    exam_id = create_and_publish(w)
    c.get(f"/api/exams/{exam_id}", headers=w["student"])
    _age_exam(w, exam_id, 45)
    data = c.get(f"/api/exams/{exam_id}", headers=w["student"]).json()
    assert data["status"] == "completed"


def test_exam_inside_grace_period_is_left_for_client_auto_submit(world):
    c, w = world["client"], world
    exam_id = create_and_publish(w)
    c.get(f"/api/exams/{exam_id}", headers=w["student"])
    _age_exam(w, exam_id, 30.5)  # süre doldu ama 60 sn tolerans içinde
    assert c.get("/api/exams", headers=w["parent"]).json()[0]["status"] == "published"
    assert c.post(f"/api/exams/{exam_id}/submit", headers=w["student"]).status_code == 200  # istemci teslimi hâlâ kabul edilir


def test_unstarted_exam_never_expires(world):
    c, w = world["client"], world
    create_and_publish(w)
    assert c.get("/api/exams", headers=w["parent"]).json()[0]["status"] == "published"


def test_students_cannot_see_each_others_exams(world):
    c, w = world["client"], world
    exam_id = create_and_publish(w)
    other = c.post("/api/auth/register", json={"email": "baska@example.com", "password": PASSWORD, "full_name": "Başka Veli"})
    assert other.status_code == 201
    stranger = login(c, "baska@example.com")
    assert c.get(f"/api/exams/{exam_id}", headers=stranger).status_code == 404
    assert c.get("/api/exams", headers=stranger).json() == []


def test_status_endpoint_counts_question_pool(world):
    c, w = world["client"], world
    assert c.get("/api/curriculum/status").json()["questions"] == 0
    create_and_publish(w)
    st = c.get("/api/curriculum/status").json()
    assert st["questions"] == 25 and st["reviewed_questions"] == 25


# ---- Arka plan süpürücüsü ve soru havuzu -----------------------------------

def test_sweep_finalizes_overdue_exam_without_any_request(world):
    c, w = world["client"], world
    exam_id = create_and_publish(w)
    c.get(f"/api/exams/{exam_id}", headers=w["student"])  # sınav başladı
    _age_exam(w, exam_id, 45)
    assert exams_module.sweep_overdue_exams(session_factory=w["factory"]) == 1
    assert w["sent"] == [("veli@example.com", 0, 0, 25)]
    with w["factory"]() as db:
        exam = db.get(Exam, __import__("uuid").UUID(exam_id))
        assert exam.status == "completed" and exam.score == 0 and exam.completed_at is not None
    assert exams_module.sweep_overdue_exams(session_factory=w["factory"]) == 0, "ikinci tarama yeniden işlememeli"
    assert len(w["sent"]) == 1


def test_sweep_leaves_grace_period_and_unstarted_exams_alone(world):
    c, w = world["client"], world
    started = create_and_publish(w, "Başlamış")
    create_and_publish(w, "Başlamamış")
    c.get(f"/api/exams/{started}", headers=w["student"])
    _age_exam(w, started, 30.5)
    assert exams_module.sweep_overdue_exams(session_factory=w["factory"]) == 0


def test_email_failure_does_not_undo_finalization(world, monkeypatch):
    c, w = world["client"], world
    exam_id = create_and_publish(w)
    c.get(f"/api/exams/{exam_id}", headers=w["student"])
    _age_exam(w, exam_id, 45)

    def broken(*_a):
        raise OSError("SMTP kapalı")
    monkeypatch.setattr(exams_module, "send_exam_result_email", broken)
    assert exams_module.sweep_overdue_exams(session_factory=w["factory"]) == 1
    with w["factory"]() as db:
        assert db.get(Exam, __import__("uuid").UUID(exam_id)).status == "completed"


def _run_app_for(seconds, monkeypatch, interval, sweep):
    import time
    from fastapi.testclient import TestClient
    import app.main as main_module
    from app.main import app
    monkeypatch.setattr(main_module, "sweep_overdue_exams", sweep)
    monkeypatch.setattr(settings, "AUTO_IMPORT_CURRICULUM", False)
    monkeypatch.setattr(settings, "EXAM_SWEEP_INTERVAL_SECONDS", interval)
    with TestClient(app) as c:
        time.sleep(seconds)
        assert c.get("/health").status_code == 200


def test_background_sweeper_runs_periodically_and_survives_errors(monkeypatch):
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("geçici veritabanı hatası")
        return 0
    _run_app_for(0.5, monkeypatch, 0.05, flaky)
    assert len(calls) >= 3, "ilk hataya rağmen döngü sürmeli"


def test_background_sweeper_can_be_disabled(monkeypatch):
    calls = []
    _run_app_for(0.3, monkeypatch, 0, lambda: calls.append(1) or 0)
    assert calls == []


def _second_student(w):
    r = w["client"].post("/api/auth/students", headers=w["parent"], json={
        "email": "ikinci@example.com", "password": PASSWORD, "full_name": "İkinci Öğrenci",
        "grade_level": 5, "consent_confirmed": True})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _generate(w, student_id, title):
    return w["client"].post("/api/exams/generate", headers=w["parent"], json={
        "student_id": student_id, "learning_outcome_id": w["outcome_id"], "title": title})


def test_question_pool_reuse_is_off_by_default(world, monkeypatch):
    w = world
    create_and_publish(w)
    calls = []
    monkeypatch.setattr(exams_module, "generate_questions", lambda *a, **k: calls.append(1) or fake_questions())
    r = _generate(w, _second_student(w), "Havuz kapalı")
    assert r.status_code == 201 and r.json()["source"] == "gemini" and len(calls) == 1


def test_question_pool_reuse_serves_unseen_reviewed_questions_without_gemini(world, monkeypatch):
    c, w = world["client"], world
    monkeypatch.setattr(settings, "REUSE_REVIEWED_QUESTIONS", True)
    first = create_and_publish(w)  # 1. öğrenci: havuz boş -> Gemini
    calls = []
    monkeypatch.setattr(exams_module, "generate_questions", lambda *a, **k: calls.append(1) or fake_questions())

    second_student = _second_student(w)
    r = _generate(w, second_student, "Havuzdan sınav")
    assert r.status_code == 201 and r.json()["source"] == "pool" and r.json()["status"] == "pending_review"
    assert calls == [], "havuzdan sınavda Gemini çağrılmamalı"
    assert c.get("/api/curriculum/status").json()["questions"] == 25, "yeni soru kaydı oluşmamalı"

    pooled = r.json()["id"]
    assert c.post(f"/api/exams/{pooled}/approve", headers=w["admin"]).status_code == 200
    ikinci = login(c, "ikinci@example.com")
    qs = c.get(f"/api/exams/{pooled}", headers=ikinci).json()["questions"]
    assert len(qs) == 25 and [q["position"] for q in qs] == list(range(1, 26))

    # Aynı öğrenci tüm havuz sorularını gördü -> yeni sınav için Gemini'ye dönülür.
    again = _generate(w, w["students"]["ogrenci@example.com"], "Tekrar")
    assert again.json()["source"] == "gemini" and len(calls) == 1
    assert first != pooled


def test_admin_can_correct_an_existing_outcome_via_import_and_seed_does_not_revert_it(world):
    import json
    c, w = world["client"], world
    data = json.loads((CURRICULUM_DIR / "5-turkce-tymm-2024.json").read_text(encoding="utf-8"))
    unit = data["units"][0]
    outcome = unit["outcomes"][0]
    fix = {k: data[k] for k in ("grade_level", "subject_name", "curriculum_version", "source_url")}
    fix["units"] = [{"name": unit["name"], "order_no": unit["order_no"],
                     "outcomes": [{"code": outcome["code"], "description": "Düzeltilmiş kazanım açıklaması metni."}]}]
    r = c.post("/api/curriculum/import", headers=w["admin"], json=fix)
    assert r.status_code == 201 and r.json()["outcomes_added"] == 0 and r.json()["units_added"] == 0
    assert c.post("/api/curriculum/import", headers=w["parent"], json=fix).status_code == 403

    with w["factory"]() as db:
        row = db.scalars(select(LearningOutcome).join(Unit).where(
            Unit.name == unit["name"], LearningOutcome.code == outcome["code"])).first()
        assert row.description == "Düzeltilmiş kazanım açıklaması metni."
    assert seed_missing_curriculum(CURRICULUM_DIR, session_factory=w["factory"]).imported == 0
    with w["factory"]() as db:
        assert db.get(LearningOutcome, row.id).description == "Düzeltilmiş kazanım açıklaması metni."
