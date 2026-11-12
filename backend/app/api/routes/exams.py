from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import (Exam, ExamQuestion, LearningOutcome, ParentStudentLink,
                        Question, StudentAnswer, User, Unit, Subject)
from app.schemas import AnswerRequest, ExamGenerateRequest, ExamRejectRequest
from app.services.question_generator import generate_questions
from app.services.email import send_exam_result_email

router = APIRouter(prefix="/api/exams", tags=["Sınavlar"])


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
def create_exam(payload: ExamGenerateRequest, user: User = Depends(get_current_user),
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
    return {"id": str(exam.id), "title": exam.title, "question_count": 25, "status": exam.status}


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
    db.commit()
    return {"id": str(exam.id), "status": exam.status, "review_note": exam.review_note}


@router.get("")
def list_exams(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
    return [{"id": str(e.id), "title": e.title, "status": e.status,
             "question_count": e.question_count, "score": e.score, "review_note": e.review_note}
            for e in db.scalars(query.order_by(Exam.id.desc())).all()]


@router.get("/{exam_id}")
def get_exam(exam_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    exam = db.get(Exam, exam_id)
    if not exam or not can_access_student(user, exam.student_id, db):
        raise HTTPException(status_code=404, detail="Sınav bulunamadı.")
    if exam.status not in {"published", "completed"} and user.role != "admin":
        raise HTTPException(status_code=409, detail="Sınav henüz yayımlanmadı veya erişime kapatıldı.")
    rows = db.execute(select(ExamQuestion, Question).join(
        Question, Question.id == ExamQuestion.question_id
    ).where(ExamQuestion.exam_id == exam.id).order_by(ExamQuestion.position)).all()
    return {"id": str(exam.id), "title": exam.title, "status": exam.status,
            "questions": [{"id": str(eq.id), "position": eq.position,
                           "prompt": q.prompt, "options": q.options} for eq, q in rows]}


@router.post("/{exam_id}/answers/{exam_question_id}")
def save_answer(exam_id: UUID, exam_question_id: UUID, payload: AnswerRequest,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    exam = db.get(Exam, exam_id)
    if not exam or exam.student_id != user.id or user.role != "student":
        raise HTTPException(status_code=404, detail="Sınav bulunamadı.")
    if exam.status != "published":
        raise HTTPException(status_code=409, detail="Sınav cevap kabul etmiyor.")
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
