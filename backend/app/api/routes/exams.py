import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models import (Exam, ExamQuestion, LearningOutcome, ParentStudentLink,
                        Question, StudentAnswer, User, Unit, Subject)
from app.schemas import AnswerRequest, ExamGenerateRequest, ExamRejectRequest
from app.services.question_generator import generate_questions
from app.services.email import send_exam_result_email
from app.services.audit import record_admin_action
from app.core.rate_limit import limiter

router = APIRouter(prefix="/api/exams", tags=["Sınavlar"])
logger = logging.getLogger(__name__)


def student_can_open_exam(status: str) -> bool:
    return status in {"published", "completed"}


def exam_deadline(exam: Exam) -> datetime | None:
    if exam.started_at is None:
        return None
    started = exam.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return started + timedelta(minutes=exam.duration_minutes or 30)


OVERDUE_GRACE = timedelta(seconds=60)  # istemcinin otomatik teslimi için süre tanınır


def finalize_exam(db: Session, exam: Exam) -> tuple[int, list[str]]:
    """Puanı hesaplar ve sınavı tamamlar. Commit çağıranın sorumluluğundadır.

    Döndürür: (doğru sayısı, bildirim gidecek veli e-postaları).
    """
    rows = db.execute(select(ExamQuestion, Question).join(
        Question, Question.id == ExamQuestion.question_id
    ).where(ExamQuestion.exam_id == exam.id)).all()
    if len(rows) != 25:
        raise HTTPException(status_code=409, detail="Sınav 25 sorudan oluşmuyor.")
    correct = 0
    for eq, question in rows:
        answer = db.scalar(select(StudentAnswer).where(StudentAnswer.exam_question_id == eq.id))
        if answer and answer.selected_option:
            answer.is_correct = answer.selected_option == question.correct_option
            correct += int(answer.is_correct)
        elif answer:
            answer.is_correct = False
    exam.score = round(correct * 100 / 25)
    exam.status = "completed"
    exam.completed_at = datetime.now(timezone.utc)
    parent_emails = db.scalars(select(User.email).join(
        ParentStudentLink, ParentStudentLink.parent_id == User.id
    ).where(ParentStudentLink.student_id == exam.student_id,
            ParentStudentLink.consent_confirmed.is_(True))).all()
    return correct, list(parent_emails)


def expire_overdue_exams(db: Session, exams: list[Exam], background_tasks: BackgroundTasks) -> int:
    """Süresi (ve tolerans süresi) dolmuş yayımlanmış sınavları sunucuda sonuçlandırır.

    Öğrenci uygulamayı kapatsa bile sınav "yayında" kalmaz; puan ve veli bildirimi oluşur.
    """
    now = datetime.now(timezone.utc)
    finished = 0
    pending_notifications: list[tuple[str, str, int, int]] = []
    for exam in exams:
        if exam.status != "published":
            continue
        deadline = exam_deadline(exam)
        if deadline is None or now < deadline + OVERDUE_GRACE:
            continue
        try:
            correct, parent_emails = finalize_exam(db, exam)
        except HTTPException:
            continue
        finished += 1
        pending_notifications.extend(
            (email, exam.title, exam.score, correct) for email in parent_emails
        )
    if finished:
        # Bildirimler yalnızca sonuçlar kalıcı olarak kaydedildikten sonra kuyruğa alınır.
        # Commit başarısızsa e-posta gönderilmez ve sonraki tarama tekrar deneyebilir.
        db.commit()
        for email, title, score, correct in pending_notifications:
            background_tasks.add_task(send_exam_result_email, email, title, score, correct, 25)
    return finished



class _ImmediateTasks:
    """BackgroundTasks yerine, istek bağlamı olmayan süpürücü için e-postaları hemen gönderir."""

    def add_task(self, func, *args, **kwargs) -> None:
        try:
            func(*args, **kwargs)
        except Exception:  # e-posta hatası sonuçlandırmayı geri almamalı
            logger.exception("Arka plan görevi başarısız oldu.")


def sweep_overdue_exams(session_factory=None) -> int:
    """Tüm süresi dolmuş yayımlanmış sınavları sonuçlandırır; zamanlanmış görev olarak çalışır."""
    with (session_factory or SessionLocal)() as db:
        exams = db.scalars(select(Exam).where(Exam.status == "published", Exam.started_at.is_not(None))).all()
        return expire_overdue_exams(db, list(exams), _ImmediateTasks())


def pick_reviewed_questions(db: Session, outcome_id: UUID, student_id: UUID) -> list[Question] | None:
    """Onaylı havuzdan öğrencinin daha önce görmediği 25 soruyu seçer; yetmezse None döner."""
    seen = select(ExamQuestion.question_id).join(Exam, Exam.id == ExamQuestion.exam_id).where(
        Exam.student_id == student_id)
    picked = db.scalars(select(Question).where(
        Question.learning_outcome_id == outcome_id, Question.is_reviewed.is_(True),
        Question.id.not_in(seen)).order_by(func.random()).limit(25)).all()
    return list(picked) if len(picked) == 25 else None


def student_question_payload(exam_question: ExamQuestion, question: Question) -> dict:
    """Return only exam content; never expose the answer key before submission."""
    return {
        "id": str(exam_question.id),
        "position": exam_question.position,
        "prompt": question.prompt,
        "options": question.options,
    }


def can_access_student(user: User, student_id: UUID, db: Session) -> bool:
    if user.role == "admin":
        return True
    if user.role == "student":
        return user.id == student_id
    if user.role != "parent":
        return False
    return db.scalar(select(ParentStudentLink.id).where(
        ParentStudentLink.parent_id == user.id,
        ParentStudentLink.student_id == student_id,
        ParentStudentLink.consent_confirmed.is_(True))) is not None


def require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Yalnızca yönetici bu işlemi yapabilir.")


@router.post("/generate", status_code=201)
@limiter.limit("10/hour")
def create_exam(request: Request, payload: ExamGenerateRequest, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    student = db.get(User, payload.student_id)
    outcome = db.get(LearningOutcome, payload.learning_outcome_id)
    if not student or student.role != "student":
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı.")
    if user.role == "student" or not can_access_student(user, student.id, db):
        raise HTTPException(status_code=403, detail="Bu öğrenci için sınav oluşturamazsınız.")
    if not outcome:
        raise HTTPException(status_code=404, detail="Kazanım bulunamadı.")
    unit = db.get(Unit, outcome.unit_id)
    subject = db.get(Subject, unit.subject_id) if unit else None
    if not subject or subject.grade_level != student.grade_level:
        raise HTTPException(status_code=400, detail="Kazanım öğrencinin sınıf düzeyiyle eşleşmiyor.")
    reused = pick_reviewed_questions(db, outcome.id, student.id) if settings.REUSE_REVIEWED_QUESTIONS else None
    generated = []
    if reused is None:
        try:
            generated = generate_questions(outcome.code, outcome.description, subject.grade_level,
                                           subject.name, count=25)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Gemini soru üretimi sırasında hata oluştu.") from exc
    exam = Exam(student_id=student.id, title=payload.title, status="pending_review", question_count=25)
    db.add(exam)
    try:
        db.flush()
        for position, existing in enumerate(reused or [], start=1):
            db.add(ExamQuestion(exam_id=exam.id, question_id=existing.id, position=position))
        for position, item in enumerate(generated, start=1):
            question = Question(
                learning_outcome_id=outcome.id, prompt=item.prompt,
                options=[{"key": key, "text": value} for key, value in item.options.items()],
                correct_option=item.correct_option, explanation=item.explanation,
                difficulty=item.difficulty, is_reviewed=False,
            )
            db.add(question)
            db.flush()
            db.add(ExamQuestion(exam_id=exam.id, question_id=question.id, position=position))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"id": str(exam.id), "title": exam.title, "question_count": 25, "status": exam.status,
            "source": "pool" if reused is not None else "gemini"}


@router.get("/review-queue")
def review_queue(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(user)
    exams = db.scalars(select(Exam).where(Exam.status == "pending_review").order_by(Exam.id)).all()
    output = []
    for exam in exams:
        rows = db.execute(select(ExamQuestion, Question).join(
            Question, Question.id == ExamQuestion.question_id
        ).where(ExamQuestion.exam_id == exam.id).order_by(ExamQuestion.position)).all()
        output.append({"id": str(exam.id), "title": exam.title, "student_id": str(exam.student_id),
                       "questions": [{"id": str(eq.id), "position": eq.position, "prompt": q.prompt,
                                      "options": q.options, "correct_option": q.correct_option,
                                      "explanation": q.explanation} for eq, q in rows]})
    return output


@router.post("/{exam_id}/approve")
def approve_exam(exam_id: UUID, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    require_admin(user)
    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Sınav bulunamadı.")
    if exam.status != "pending_review":
        raise HTTPException(status_code=409, detail="Sınav yönetici incelemesinde değil.")
    rows = db.scalars(select(ExamQuestion).where(ExamQuestion.exam_id == exam.id)).all()
    if len(rows) != 25:
        raise HTTPException(status_code=409, detail="Sınavda tam 25 soru bulunmuyor.")
    question_ids = [row.question_id for row in rows]
    questions = db.scalars(select(Question).where(Question.id.in_(question_ids))).all()
    if len(questions) != 25:
        raise HTTPException(status_code=409, detail="Sınav soruları eksik.")
    for question in questions:
        question.is_reviewed = True
    exam.status = "published"
    record_admin_action(db, user, "exam.approve", "exam", exam.id, "Sınav yönetici incelemesinden geçerek yayımlandı.")
    db.commit()
    return {"id": str(exam.id), "status": exam.status, "question_count": 25}


@router.post("/{exam_id}/reject")
def reject_exam(exam_id: UUID, payload: ExamRejectRequest,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(user)
    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Sınav bulunamadı.")
    if exam.status != "pending_review":
        raise HTTPException(status_code=409, detail="Yalnızca incelemedeki sınav reddedilebilir.")
    exam.status = "rejected"
    exam.review_note = payload.reason
    record_admin_action(db, user, "exam.reject", "exam", exam.id, "Sınav reddedildi; gerekçe sınav kaydında saklanır.")
    db.commit()
    return {"id": str(exam.id), "status": exam.status, "review_note": exam.review_note}


@router.get("")
def list_exams(background_tasks: BackgroundTasks, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    query = select(Exam)
    if user.role == "student":
        query = query.where(Exam.student_id == user.id)
    elif user.role == "parent":
        student_ids = select(ParentStudentLink.student_id).where(
            ParentStudentLink.parent_id == user.id,
            ParentStudentLink.consent_confirmed.is_(True))
        query = query.where(Exam.student_id.in_(student_ids))
    elif user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok.")
    exams = db.scalars(query.order_by(Exam.id.desc())).all()
    expire_overdue_exams(db, list(exams), background_tasks)
    return [{"id": str(e.id), "title": e.title, "status": e.status,
             "question_count": e.question_count, "score": e.score, "review_note": e.review_note}
            for e in exams]


@router.get("/{exam_id}")
def get_exam(exam_id: UUID, background_tasks: BackgroundTasks, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    exam = db.get(Exam, exam_id)
    if not exam or not can_access_student(user, exam.student_id, db):
        raise HTTPException(status_code=404, detail="Sınav bulunamadı.")
    expire_overdue_exams(db, [exam], background_tasks)
    if not student_can_open_exam(exam.status) and user.role != "admin":
        raise HTTPException(status_code=409, detail="Sınav henüz yayımlanmadı veya erişime kapatıldı.")
    if user.role == "student" and exam.status == "published" and exam.started_at is None:
        exam.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(exam)
    rows = db.execute(select(ExamQuestion, Question).join(
        Question, Question.id == ExamQuestion.question_id
    ).where(ExamQuestion.exam_id == exam.id).order_by(ExamQuestion.position)).all()
    saved = {}
    if user.role == "student":
        for eq, _question in rows:
            answer = db.scalar(select(StudentAnswer).where(StudentAnswer.exam_question_id == eq.id))
            if answer and answer.selected_option:
                saved[str(eq.id)] = answer.selected_option
    deadline = exam_deadline(exam)
    return {"id": str(exam.id), "title": exam.title, "status": exam.status,
            "duration_minutes": exam.duration_minutes,
            "server_time": datetime.now(timezone.utc).isoformat(),
            "started_at": exam.started_at.isoformat() if exam.started_at else None,
            "deadline_at": deadline.isoformat() if deadline else None,
            "saved_answers": saved,
            "questions": [student_question_payload(eq, q) for eq, q in rows]}


@router.post("/{exam_id}/answers/{exam_question_id}")
def save_answer(exam_id: UUID, exam_question_id: UUID, payload: AnswerRequest,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    exam = db.get(Exam, exam_id)
    if not exam or exam.student_id != user.id or user.role != "student":
        raise HTTPException(status_code=404, detail="Sınav bulunamadı.")
    if exam.status != "published":
        raise HTTPException(status_code=409, detail="Sınav cevap kabul etmiyor.")
    deadline = exam_deadline(exam)
    if deadline and datetime.now(timezone.utc) >= deadline:
        raise HTTPException(status_code=409, detail="Sınav süresi doldu. Cevaplarınız teslim ediliyor.")
    eq = db.get(ExamQuestion, exam_question_id)
    if not eq or eq.exam_id != exam.id:
        raise HTTPException(status_code=404, detail="Soru bulunamadı.")
    answer = db.scalar(select(StudentAnswer).where(StudentAnswer.exam_question_id == eq.id))
    if answer is None:
        answer = StudentAnswer(exam_question_id=eq.id)
        db.add(answer)
    answer.selected_option = payload.selected_option
    answer.answered_at = datetime.now(timezone.utc)
    db.commit()
    return {"saved": True}


@router.post("/{exam_id}/submit")
def submit_exam(exam_id: UUID, background_tasks: BackgroundTasks, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    exam = db.get(Exam, exam_id)
    if not exam or exam.student_id != user.id or user.role != "student":
        raise HTTPException(status_code=404, detail="Sınav bulunamadı.")
    if exam.status != "published":
        raise HTTPException(status_code=409, detail="Sınav daha önce tamamlanmış veya kapalı.")
    correct, parent_emails = finalize_exam(db, exam)
    db.commit()
    for email in parent_emails:
        background_tasks.add_task(send_exam_result_email, email, exam.title, exam.score, correct, 25)
    return {"exam_id": str(exam.id), "correct": correct, "total": 25,
            "score": exam.score, "status": exam.status}


@router.get("/{exam_id}/results")
def exam_results(exam_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    exam = db.get(Exam, exam_id)
    if not exam or not can_access_student(user, exam.student_id, db):
        raise HTTPException(status_code=404, detail="Sınav bulunamadı.")
    if exam.status != "completed":
        raise HTTPException(status_code=409, detail="Sonuç henüz hazır değil.")
    rows = db.execute(select(ExamQuestion, Question).join(
        Question, Question.id == ExamQuestion.question_id
    ).where(ExamQuestion.exam_id == exam.id).order_by(ExamQuestion.position)).all()
    details = []
    for eq, q in rows:
        answer = db.scalar(select(StudentAnswer).where(StudentAnswer.exam_question_id == eq.id))
        details.append({"position": eq.position, "prompt": q.prompt, "options": q.options,
                        "selected_option": answer.selected_option if answer else None,
                        "correct_option": q.correct_option, "is_correct": answer.is_correct if answer else False,
                        "explanation": q.explanation})
    return {"score": exam.score, "question_count": len(rows), "details": details}


@router.get("/{exam_id}/results.pdf")
def download_exam_result_pdf(exam_id: UUID, user: User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    from fastapi.responses import Response
    from app.services.pdf_reports import build_exam_result_pdf

    exam = db.get(Exam, exam_id)
    if not exam or not can_access_student(user, exam.student_id, db):
        raise HTTPException(status_code=404, detail="Sınav bulunamadı.")
    if exam.status != "completed":
        raise HTTPException(status_code=409, detail="PDF sonuç raporu yalnızca tamamlanan sınavlar için hazırlanır.")
    student = db.get(User, exam.student_id)
    rows = db.execute(select(ExamQuestion, Question).join(
        Question, Question.id == ExamQuestion.question_id
    ).where(ExamQuestion.exam_id == exam.id).order_by(ExamQuestion.position)).all()
    details = []
    for eq, question in rows:
        answer = db.scalar(select(StudentAnswer).where(StudentAnswer.exam_question_id == eq.id))
        details.append({
            "position": eq.position,
            "prompt": question.prompt,
            "options": question.options,
            "selected_option": answer.selected_option if answer else None,
            "correct_option": question.correct_option,
            "is_correct": answer.is_correct if answer else False,
            "explanation": question.explanation,
        })
    pdf = build_exam_result_pdf(
        exam_title=exam.title,
        student_name=student.full_name if student else "Öğrenci",
        score=exam.score,
        details=details,
        completed_at=exam.completed_at.isoformat() if exam.completed_at else None,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="sinav-sonucu-{exam.id}.pdf"'},
    )
