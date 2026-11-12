from app.services.pdf_reports import build_exam_result_pdf, build_parent_progress_pdf


def test_exam_result_pdf_is_generated_with_turkish_text():
    pdf = build_exam_result_pdf(
        exam_title="Türkçe değerlendirme",
        student_name="Çağrı Şahin",
        score=80,
        completed_at="2026-11-12T12:00:00+00:00",
        details=[{
            "position": 1,
            "prompt": "Aşağıdakilerden hangisi doğru?",
            "options": [
                {"key": "A", "text": "Çilek"},
                {"key": "B", "text": "Şeftali"},
                {"key": "C", "text": "Üzüm"},
                {"key": "D", "text": "Kiraz"},
            ],
            "selected_option": "B",
            "correct_option": "B",
            "is_correct": True,
            "explanation": "Şeftali doğru cevaptır.",
        }],
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_parent_progress_pdf_is_generated_when_no_exams_exist():
    pdf = build_parent_progress_pdf(
        student_name="Öğrenci",
        progress={
            "completed_exam_count": 0,
            "average_score": None,
            "recent_exams": [],
            "learning_outcomes": [],
        },
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500
