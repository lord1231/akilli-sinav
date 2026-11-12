from uuid import UUID
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.db.session import get_db
from app.models import (Exam, ExamQuestion, LearningOutcome, ParentStudentLink,
                        PasswordResetToken, Question, StudentAnswer, User)
from app.services.email import send_password_reset_email
from app.core.rate_limit import limiter
from app.schemas import (CreateStudent, ForgotPasswordRequest, LoginRequest,
                          RegisterParent, ResetPasswordRequest, TokenResponse, UserResponse)

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




def _password_reset_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/password/forgot")
@limiter.limit("3/hour")
def request_password_reset(request: Request, payload: ForgotPasswordRequest,
                           background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Identical response for existing and unknown addresses prevents account enumeration.
    generic_response = {"message": "E-posta adresi kayıtlıysa parola yenileme bağlantısı gönderildi."}
    user = db.scalar(select(User).where(User.email == payload.email.lower(), User.is_active.is_(True)))
    if not user:
        return generic_response

    now = datetime.now(timezone.utc)
    active_tokens = db.scalars(select(PasswordResetToken).where(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None)
    )).all()
    for old_token in active_tokens:
        old_token.used_at = now

    raw_token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        user_id=user.id,
        token_hash=_password_reset_hash(raw_token),
        expires_at=now + timedelta(minutes=30),
    ))
    db.commit()
    reset_url = f"{settings.APP_BASE_URL.rstrip('/')}/app/?reset_token={raw_token}"
    background_tasks.add_task(send_password_reset_email, user.email, reset_url)
    return generic_response


@router.post("/password/reset")
@limiter.limit("5/minute")
def reset_password(request: Request, payload: ResetPasswordRequest,
                   db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    reset_record = db.scalar(select(PasswordResetToken).where(
        PasswordResetToken.token_hash == _password_reset_hash(payload.token),
        PasswordResetToken.used_at.is_(None),
    ))
    if not reset_record:
        raise HTTPException(status_code=400, detail="Bağlantı geçersiz veya süresi dolmuş.")
    expires_at = reset_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        reset_record.used_at = now
        db.commit()
        raise HTTPException(status_code=400, detail="Bağlantı geçersiz veya süresi dolmuş.")

    user = db.get(User, reset_record.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Bağlantı geçersiz veya süresi dolmuş.")
    user.password_hash = hash_password(payload.new_password)
    reset_record.used_at = now
    other_tokens = db.scalars(select(PasswordResetToken).where(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.id != reset_record.id,
    )).all()
    for other in other_tokens:
        other.used_at = now
    db.commit()
    return {"message": "Parolanız yenilendi. Yeni parolanızla giriş yapabilirsiniz."}


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
        select(LearningOutcome.code, LearningOutcome.description, StudentAnswer.is_correct,
               Subject.name, Unit.name)
        .join(Unit, Unit.id == LearningOutcome.unit_id)
        .join(Subject, Subject.id == Unit.subject_id)
        .join(Question, Question.learning_outcome_id == LearningOutcome.id)
        .join(ExamQuestion, ExamQuestion.question_id == Question.id)
        .join(Exam, Exam.id == ExamQuestion.exam_id)
        .outerjoin(StudentAnswer, StudentAnswer.exam_question_id == ExamQuestion.id)
        .where(Exam.student_id == student_id, Exam.status == "completed")
    ).all()
    outcome_stats = {}
    for code, description, is_correct, subject_name, unit_name in rows:
        stat = outcome_stats.setdefault(code, {
            "code": code, "description": description, "subject": subject_name,
            "unit": unit_name, "total": 0, "answered": 0, "correct": 0,
        })
        stat["total"] += 1
        if is_correct is not None:
            stat["answered"] += 1
            stat["correct"] += int(is_correct)
    outcomes = []
    for stat in outcome_stats.values():
        stat["unanswered"] = stat["total"] - stat["answered"]
        stat["success_rate"] = round(100 * stat["correct"] / stat["answered"]) if stat["answered"] else 0
        outcomes.append(stat)
    outcomes.sort(key=lambda x: (x["success_rate"], x["subject"], x["code"]))
    total_questions = sum(item["total"] for item in outcome_stats.values())
    total_answered = sum(item["answered"] for item in outcome_stats.values())
    total_correct = sum(item["correct"] for item in outcome_stats.values())
    return {
        "student_id": str(student_id),
        "completed_exam_count": len(exams),
        "average_score": round(sum(scores) / len(scores)) if scores else None,
        "total_questions": total_questions,
        "answered_questions": total_answered,
        "correct_answers": total_correct,
        "unanswered_questions": total_questions - total_answered,
        "recent_exams": [{"title": e.title, "score": e.score,
                          "completed_at": e.completed_at.isoformat() if e.completed_at else None}
                         for e in exams[:10]],
        "learning_outcomes": outcomes,
    }


@router.get("/students/{student_id}/progress.pdf")
def download_student_progress_pdf(student_id: UUID, parent: User = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    from fastapi.responses import Response
    from app.services.pdf_reports import build_parent_progress_pdf

    if parent.role != "parent":
        raise HTTPException(status_code=403, detail="Yalnızca veliler erişebilir.")
    progress = student_progress(student_id, parent, db)
    student = db.get(User, student_id)
    pdf = build_parent_progress_pdf(student_name=student.full_name, progress=progress)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ogrenci-gelisim-{student_id}.pdf"'},
    )
