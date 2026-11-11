from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import LearningOutcome, Subject, Unit, User

router = APIRouter(prefix="/api/curriculum", tags=["MEB Müfredatı"])


class SubjectInput(BaseModel):
    grade_level: int = Field(ge=4, le=5)
    name: str = Field(min_length=2, max_length=120)
    curriculum_version: str = Field(min_length=2, max_length=80)


class UnitInput(BaseModel):
    subject_id: str
    name: str = Field(min_length=2, max_length=160)
    order_no: int = Field(ge=1)


class OutcomeInput(BaseModel):
    unit_id: str
    code: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=10)
    source_url: str | None = None
    source_version: str | None = None


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
            for x in db.scalars(query.order_by(Subject.grade_level, Subject.name)).all()]


@router.get("/subjects/{subject_id}/units")
def list_units(subject_id: str, db: Session = Depends(get_db)):
    rows = db.scalars(select(Unit).where(Unit.subject_id == subject_id).order_by(Unit.order_no)).all()
    return [{"id": str(x.id), "name": x.name, "order_no": x.order_no} for x in rows]


@router.get("/units/{unit_id}/outcomes")
def list_outcomes(unit_id: str, db: Session = Depends(get_db)):
    rows = db.scalars(select(LearningOutcome).where(LearningOutcome.unit_id == unit_id)).all()
    return [{"id": str(x.id), "code": x.code, "description": x.description,
             "source_url": x.source_url, "source_version": x.source_version} for x in rows]


@router.post("/subjects", status_code=201)
def create_subject(payload: SubjectInput, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    require_admin(user)
    item = Subject(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id)}


@router.post("/units", status_code=201)
def create_unit(payload: UnitInput, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    require_admin(user)
    item = Unit(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id)}


@router.post("/outcomes", status_code=201)
def create_outcome(payload: OutcomeInput, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    require_admin(user)
    item = LearningOutcome(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": str(item.id)}
