from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import LearningOutcome, Question, Subject, Unit, User
from app.services.audit import record_admin_action

router = APIRouter(prefix="/api/curriculum", tags=["MEB Müfredatı"])
OFFICIAL_MEB_HOSTS = {"tymm.meb.gov.tr", "mufredat.meb.gov.tr", "dogm.meb.gov.tr"}


def validate_meb_source(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in OFFICIAL_MEB_HOSTS
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        raise ValueError("Kaynak yalnızca HTTPS kullanan resmî TYMM, MEB müfredat veya Din Öğretimi Genel Müdürlüğü alan adlarından biri olabilir.")
    return value

class SubjectInput(BaseModel):
    grade_level: int = Field(ge=4, le=5)
    name: str = Field(min_length=2, max_length=120)
    curriculum_version: str = Field(min_length=2, max_length=80)


class UnitInput(BaseModel):
    subject_id: UUID
    name: str = Field(min_length=2, max_length=160)
    order_no: int = Field(ge=1)


class OutcomeInput(BaseModel):
    unit_id: UUID
    code: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=10)
    source_url: str
    source_version: str = Field(min_length=2, max_length=100)

    @field_validator("source_url")
    @classmethod
    def official_source_only(cls, value: str) -> str:
        return validate_meb_source(value)


class ImportedOutcome(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=10, max_length=3000)


class ImportedUnit(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    order_no: int = Field(ge=1)
    outcomes: list[ImportedOutcome] = Field(min_length=1)


class CurriculumImport(BaseModel):
    grade_level: int = Field(ge=4, le=5)
    subject_name: str = Field(min_length=2, max_length=120)
    curriculum_version: str = Field(min_length=2, max_length=80)
    source_url: str
    units: list[ImportedUnit] = Field(min_length=1)

    @field_validator("source_url")
    @classmethod
    def official_source_only(cls, value: str) -> str:
        return validate_meb_source(value)


def require_admin(user: User):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Yalnızca yönetici müfredatı değiştirebilir.")


@router.get("/subjects")
def list_subjects(grade: int | None = None, db: Session = Depends(get_db)):
    query = select(Subject).where(Subject.is_active.is_(True))
    if grade is not None:
        query = query.where(Subject.grade_level == grade)
    return [{"id": str(x.id), "grade_level": x.grade_level, "name": x.name,
             "curriculum_version": x.curriculum_version}
            for x in db.scalars(query.order_by(Subject.grade_level, Subject.name, Subject.curriculum_version)).all()]


@router.get("/status")
def curriculum_status(db: Session = Depends(get_db)):
    subjects = db.scalar(select(func.count(Subject.id)).where(Subject.is_active.is_(True))) or 0
    units = db.scalar(select(func.count(Unit.id))) or 0
    outcomes = db.scalar(select(func.count(LearningOutcome.id))) or 0
    questions = db.scalar(select(func.count(Question.id))) or 0
    reviewed = db.scalar(select(func.count(Question.id)).where(Question.is_reviewed.is_(True))) or 0
    by_grade = {str(g): n for g, n in db.execute(
        select(Subject.grade_level, func.count(Subject.id)).where(Subject.is_active.is_(True))
        .group_by(Subject.grade_level).order_by(Subject.grade_level))}
    return {"subjects": subjects, "units": units, "outcomes": outcomes,
            "subjects_by_grade": by_grade, "questions": questions, "reviewed_questions": reviewed,
            "empty": subjects == 0 or outcomes == 0}


@router.get("/subjects/{subject_id}/units")
def list_units(subject_id: UUID, db: Session = Depends(get_db)):
    rows = db.scalars(select(Unit).where(Unit.subject_id == subject_id).order_by(Unit.order_no)).all()
    return [{"id": str(x.id), "name": x.name, "order_no": x.order_no} for x in rows]


@router.get("/units/{unit_id}/outcomes")
def list_outcomes(unit_id: UUID, db: Session = Depends(get_db)):
    rows = db.scalars(select(LearningOutcome).where(LearningOutcome.unit_id == unit_id)).all()
    return [{"id": str(x.id), "code": x.code, "description": x.description,
             "source_url": x.source_url, "source_version": x.source_version} for x in rows]


@router.post("/import", status_code=201)
def import_curriculum(payload: CurriculumImport, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    require_admin(user)
    subject = db.scalar(select(Subject).where(
        Subject.grade_level == payload.grade_level,
        Subject.name == payload.subject_name,
        Subject.curriculum_version == payload.curriculum_version,
    ))
    if subject is None:
        subject = Subject(grade_level=payload.grade_level, name=payload.subject_name,
                          curriculum_version=payload.curriculum_version)
        db.add(subject)
        db.flush()
    unit_count = 0
    outcome_count = 0
    try:
        for unit_data in payload.units:
            unit = db.scalar(select(Unit).where(
                Unit.subject_id == subject.id, Unit.name == unit_data.name
            ))
            if unit is None:
                unit = Unit(subject_id=subject.id, name=unit_data.name, order_no=unit_data.order_no)
                db.add(unit)
                db.flush()
                unit_count += 1
            else:
                unit.order_no = unit_data.order_no
            for outcome_data in unit_data.outcomes:
                outcome = db.scalar(select(LearningOutcome).where(
                    LearningOutcome.unit_id == unit.id, LearningOutcome.code == outcome_data.code
                ))
                if outcome is None:
                    outcome = LearningOutcome(
                        unit_id=unit.id, code=outcome_data.code,
                        description=outcome_data.description,
                        source_url=payload.source_url, source_version=payload.curriculum_version,
                    )
                    db.add(outcome)
                    outcome_count += 1
                else:
                    outcome.description = outcome_data.description
                    outcome.source_url = payload.source_url
                    outcome.source_version = payload.curriculum_version
        record_admin_action(db, user, "curriculum.import", "subject", subject.id,
                             f"Müfredat içe aktarıldı: {unit_count} ünite, {outcome_count} yeni kazanım.")
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"subject_id": str(subject.id), "units_added": unit_count,
            "outcomes_added": outcome_count, "source_url": payload.source_url,
            "curriculum_version": payload.curriculum_version}


@router.post("/subjects", status_code=201)
def create_subject(payload: SubjectInput, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    require_admin(user)
    item = Subject(**payload.model_dump())
    db.add(item)
    db.flush()
    record_admin_action(db, user, "curriculum.subject.create", "subject", item.id, "Ders oluşturuldu.")
    db.commit()
    db.refresh(item)
    return {"id": str(item.id)}


@router.post("/units", status_code=201)
def create_unit(payload: UnitInput, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    require_admin(user)
    if not db.get(Subject, payload.subject_id):
        raise HTTPException(status_code=404, detail="Ders bulunamadı.")
    item = Unit(**payload.model_dump())
    db.add(item)
    db.flush()
    record_admin_action(db, user, "curriculum.unit.create", "unit", item.id, "Ünite oluşturuldu.")
    db.commit()
    db.refresh(item)
    return {"id": str(item.id)}


@router.post("/outcomes", status_code=201)
def create_outcome(payload: OutcomeInput, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    require_admin(user)
    if not db.get(Unit, payload.unit_id):
        raise HTTPException(status_code=404, detail="Ünite bulunamadı.")
    item = LearningOutcome(**payload.model_dump())
    db.add(item)
    db.flush()
    record_admin_action(db, user, "curriculum.outcome.create", "learning_outcome", item.id, "Kazanım oluşturuldu.")
    db.commit()
    db.refresh(item)
    return {"id": str(item.id)}
