"""Müfredat otomatik yüklemesi: boş ders listesi ve 0 kazanım sorununun regresyon testleri.

Tüm testler paylaşılan test veritabanından bağımsız, bellekte izole bir SQLite kullanır.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.main as main_module
from app.core.config import settings
from app.main import app
from app.models import LearningOutcome, Subject, Unit
from app.services.curriculum_seed import seed_missing_curriculum

CURRICULUM_DIR = Path(__file__).resolve().parents[2] / "data" / "curriculum"
FILES = sorted(CURRICULUM_DIR.glob("*.json"))


def expected(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "grade": data["grade_level"], "name": data["subject_name"],
        "version": data["curriculum_version"], "units": len(data["units"]),
        "outcomes": sum(len(u["outcomes"]) for u in data["units"]),
    }


def test_curriculum_files_exist():
    assert len(FILES) >= 21


def test_seed_populates_empty_database_for_every_file(factory):
    result = seed_missing_curriculum(CURRICULUM_DIR, session_factory=factory)
    assert result.errors == []
    assert result.files == len(FILES) and result.imported == len(FILES)
    with factory() as db:
        for path in FILES:
            exp = expected(path)
            subject = db.scalar(select(Subject).where(
                Subject.grade_level == exp["grade"], Subject.name == exp["name"],
                Subject.curriculum_version == exp["version"]))
            assert subject is not None, path.name
            units = db.scalar(select(func.count(Unit.id)).where(Unit.subject_id == subject.id))
            outcomes = db.scalar(select(func.count(LearningOutcome.id)).join(Unit).where(Unit.subject_id == subject.id))
            assert units == exp["units"], path.name
            assert outcomes == exp["outcomes"], path.name
            assert outcomes > 0, f"{path.name} boş kazanım listesi üretmemeli"


def test_seed_is_idempotent(factory):
    seed_missing_curriculum(CURRICULUM_DIR, session_factory=factory)
    with factory() as db:
        before = db.scalar(select(func.count(LearningOutcome.id)))
    second = seed_missing_curriculum(CURRICULUM_DIR, session_factory=factory)
    assert second.imported == 0 and second.skipped == len(FILES) and second.errors == []
    with factory() as db:
        assert db.scalar(select(func.count(LearningOutcome.id))) == before


def test_seed_does_not_overwrite_admin_edits(factory):
    seed_missing_curriculum(CURRICULUM_DIR, session_factory=factory)
    with factory() as db:
        outcome = db.scalars(select(LearningOutcome)).first()
        outcome.description = "Yönetici tarafından düzenlenmiş açıklama metni."
        db.commit()
        outcome_id = outcome.id
    seed_missing_curriculum(CURRICULUM_DIR, session_factory=factory)
    with factory() as db:
        assert db.get(LearningOutcome, outcome_id).description == "Yönetici tarafından düzenlenmiş açıklama metni."


def test_seed_repairs_subject_that_has_no_units(factory):
    exp = expected(CURRICULUM_DIR / "5-turkce-tymm-2024.json")
    with factory() as db:
        db.add(Subject(grade_level=exp["grade"], name=exp["name"], curriculum_version=exp["version"]))
        db.commit()
    result = seed_missing_curriculum(CURRICULUM_DIR, session_factory=factory)
    assert result.errors == []
    with factory() as db:
        subject = db.scalar(select(Subject).where(Subject.name == exp["name"], Subject.grade_level == 5))
        assert db.scalar(select(func.count(Unit.id)).where(Unit.subject_id == subject.id)) == exp["units"]

def test_seed_repairs_partial_subject_without_overwriting_existing_outcomes(factory):
    path = CURRICULUM_DIR / "5-turkce-tymm-2024.json"
    exp = expected(path)
    with factory() as db:
        subject = db.scalar(select(Subject).where(
            Subject.grade_level == exp["grade"], Subject.name == exp["name"],
            Subject.curriculum_version == exp["version"]))
    seed_missing_curriculum(CURRICULUM_DIR, session_factory=factory)
    with factory() as db:
        subject = db.scalar(select(Subject).where(
            Subject.grade_level == exp["grade"], Subject.name == exp["name"],
            Subject.curriculum_version == exp["version"]))
        first_unit = db.scalar(select(Unit).where(Unit.subject_id == subject.id).order_by(Unit.order_no))
        deleted = db.scalar(select(LearningOutcome).where(LearningOutcome.unit_id == first_unit.id))
        missing_code = deleted.code
        db.delete(deleted)
        preserved = db.scalars(select(LearningOutcome).where(LearningOutcome.unit_id == first_unit.id)).first()
        preserved.description = "Yönetici tarafından korunması gereken özel açıklama."
        preserved_id = preserved.id
        db.commit()

    result = seed_missing_curriculum(CURRICULUM_DIR, session_factory=factory)
    assert result.errors == []
    assert result.outcomes_added >= 1
    with factory() as db:
        subject = db.scalar(select(Subject).where(
            Subject.grade_level == exp["grade"], Subject.name == exp["name"],
            Subject.curriculum_version == exp["version"]))
        total = db.scalar(select(func.count(LearningOutcome.id)).join(Unit).where(Unit.subject_id == subject.id))
        assert total == exp["outcomes"]
        restored = db.scalar(select(LearningOutcome).where(LearningOutcome.code == missing_code))
        assert restored is not None
        assert db.get(LearningOutcome, preserved_id).description == "Yönetici tarafından korunması gereken özel açıklama."


def test_seed_reports_invalid_file_but_imports_the_rest(tmp_path, factory):
    (tmp_path / "bozuk.json").write_text("{ bu json degil", encoding="utf-8")
    good = tmp_path / "5-turkce-tymm-2024.json"
    good.write_text((CURRICULUM_DIR / "5-turkce-tymm-2024.json").read_text(encoding="utf-8"), encoding="utf-8")
    result = seed_missing_curriculum(tmp_path, session_factory=factory)
    assert result.imported == 1 and len(result.errors) == 1 and "bozuk.json" in result.errors[0]


def test_every_lesson_is_visible_through_the_api(client, factory):
    seed_missing_curriculum(CURRICULUM_DIR, session_factory=factory)
    for path in FILES:
        exp = expected(path)
        rows = client.get(f"/api/curriculum/subjects?grade={exp['grade']}").json()
        match = [r for r in rows if r["name"] == exp["name"] and r["curriculum_version"] == exp["version"]]
        assert len(match) == 1, f"{path.name}: ders listede görünmüyor"
        units = client.get(f"/api/curriculum/subjects/{match[0]['id']}/units").json()
        assert len(units) == exp["units"], path.name
        total = 0
        for unit in units:
            outcomes = client.get(f"/api/curriculum/units/{unit['id']}/outcomes").json()
            assert outcomes, f"{path.name}: '{unit['name']}' ünitesinde kazanım yok"
            total += len(outcomes)
        assert total == exp["outcomes"], path.name


def test_status_endpoint_reports_empty_then_populated(client, factory):
    empty = client.get("/api/curriculum/status").json()
    assert empty["empty"] is True and empty["subjects"] == 0
    seed_missing_curriculum(CURRICULUM_DIR, session_factory=factory)
    full = client.get("/api/curriculum/status").json()
    assert full["empty"] is False
    assert full["subjects"] == len(FILES)
    assert full["outcomes"] == sum(expected(p)["outcomes"] for p in FILES)
    assert set(full["subjects_by_grade"]) == {"4", "5"}


def test_application_startup_seeds_curriculum(monkeypatch, factory):
    monkeypatch.setattr(main_module, "seed_missing_curriculum",
                        lambda: seed_missing_curriculum(CURRICULUM_DIR, session_factory=factory))
    monkeypatch.setattr(settings, "AUTO_IMPORT_CURRICULUM", True)
    with TestClient(app):
        pass
    with factory() as db:
        assert db.scalar(select(func.count(Subject.id))) == len(FILES)


def test_startup_fails_when_seed_fails(monkeypatch):
    def boom():
        raise RuntimeError("veritabanı hazır değil")
    monkeypatch.setattr(main_module, "seed_missing_curriculum", boom)
    monkeypatch.setattr(settings, "AUTO_IMPORT_CURRICULUM", True)
    with pytest.raises(RuntimeError, match="veritabanı hazır değil"):
        with TestClient(app):
            pass


def test_startup_seed_can_be_disabled(monkeypatch):
    called = []
    monkeypatch.setattr(main_module, "seed_missing_curriculum", lambda: called.append(1))
    monkeypatch.setattr(settings, "AUTO_IMPORT_CURRICULUM", False)
    with TestClient(app):
        pass
    assert called == []
