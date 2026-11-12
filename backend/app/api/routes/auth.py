from uuid import UUID\nfrom datetime import datetime, timedelta, timezone\nimport hashlib\nimport secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password\nfrom app.core.config import settings
from app.db.session import get_db
from app.models import (Exam, ExamQuestion, LearningOutcome, ParentStudentLink,
                        Question, StudentAnswer, User)
from app.core.rate_limit import limiter
from app.schemas import (CreateStudent, ForgotPasswordRequest, LoginRequest,\n                          RegisterParent, ResetPasswordRequest, TokenResponse, UserResponse)

router = APIRouter(prefix="/api/auth", tags=["Kimlik doğrulama"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_parent(payload: RegisterParent, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı.")
    user = User(email=email, password_hash=hash_password(payload.password),
                full_name=payload.full_name.strip(), role="parent")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-posta veya parola hatalı.")
    return TokenResponse(access_token=create_access_token(user.id, user.role))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/students", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_student(payload: CreateStudent, parent: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if parent.role != "parent":
        raise HTTPException(status_code=403, detail="Öğrenci hesabını yalnızca veli oluşturabilir.")
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı.")
    student = User(email=email, password_hash=hash_password(payload.password),
                   full_name=payload.full_name.strip(), role="student",
                   grade_level=payload.grade_level)
    db.add(student)
    db.flush()
    db.add(ParentStudentLink(parent_id=parent.id, student_id=student.id, consent_confirmed=True))
    db.commit()
    db.refresh(student)
    return student


@router.get("/students", response_model=list[UserResponse])
def list_my_students(parent: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if parent.role != "parent":
        raise HTTPException(status_code=403, detail="Yalnızca veliler erişebilir.")
    return list(db.scalars(select(User).join(
        ParentStudentLink, ParentStudentLink.student_id == User.id
    ).where(ParentStudentLink.parent_id == parent.id,
            ParentStudentLink.consent_confirmed.is_(True))).all())


@router.get("/students/{student_id}/progress")
def student_progress(student_id: UUID, parent: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    if parent.role != "parent":
        raise HTTPException(status_code=403, detail="Yalnızca veliler erişebilir.")
    linked = db.scalar(select(ParentStudentLink.id).where(
        ParentStudentLink.parent_id == parent.id,
        ParentStudentLink.student_id == student_id,
        ParentStudentLink.consent_confirmed.is_(True)))
    if not linked:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı.")
    exams = db.scalars(select(Exam).where(
        Exam.student_id == student_id, Exam.status == "completed"
    ).order_by(Exam.completed_at.desc())).all()
    scores = [exam.score for exam in exams if exam.score is not None]
    rows = db.execute(
        select(LearningOutcome.code, LearningOutcome.description, StudentAnswer.is_correct)
        .join(Question, Question.learning_outcome_id == LearningOutcome.id)
        .join(ExamQuestion, ExamQuestion.question_id == Question.id)
        .join(Exam, Exam.id == ExamQuestion.exam_id)
        .outerjoin(StudentAnswer, StudentAnswer.exam_question_id == ExamQuestion.id)
        .where(Exam.student_id == student_id, Exam.status == "completed")
    ).all()
    outcome_stats = {}
    for code, description, is_correct in rows:
        stat = outcome_stats.setdefault(code, {"code": code, "description": description,
                                               "answered": 0, "correct": 0})
        if is_correct is not None:
            stat["answered"] += 1
            stat["correct"] += int(is_correct)
    outcomes = []
    for stat in outcome_stats.values():
        stat["success_rate"] = round(100 * stat["correct"] / stat["answered"]) if stat["answered"] else 0
        outcomes.append(stat)
    outcomes.sort(key=lambda x: x["success_rate"])
    return {
        "student_id": str(student_id),
        "completed_exam_count": len(exams),
        "average_score": round(sum(scores) / len(scores)) if scores else None,
        "recent_exams": [{"title": e.title, "score": e.score,
                          "completed_at": e.completed_at.isoformat() if e.completed_at else None}
                         for e in exams[:10]],
        "learning_outcomes": outcomes,
    }
