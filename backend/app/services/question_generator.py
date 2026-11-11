import json
from typing import Any

from google import genai
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings


class GeneratedQuestion(BaseModel):
    prompt: str = Field(min_length=10)
    options: dict[str, str]
    correct_option: str
    explanation: str = Field(min_length=5)
    difficulty: str = "medium"


class GeneratedExam(BaseModel):
    questions: list[GeneratedQuestion]


def generate_questions(outcome_code: str, outcome_description: str, grade: int,
                       subject: str, count: int = 25) -> list[GeneratedQuestion]:
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("Gemini API anahtarı sunucu ortamında tanımlanmamış.")
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = f"""
Türkçe eğitim ölçme-değerlendirme uzmanısın. {grade}. sınıf {subject} dersi için
yalnızca aşağıdaki kazanımı ölçen, özgün ve yaşa uygun {count} adet çoktan seçmeli soru üret.
Kazanım kodu: {outcome_code}
Kazanım: {outcome_description}
Her soruda A, B, C, D anahtarlarıyla tam dört seçenek, tek doğru cevap ve kısa açıklama bulunmalı.
Sorular birbirinden farklı, açık, anlaşılır ve kazanımla doğrudan ilişkili olmalı.
Telifli kitaplardan veya yayımlanmış soru bankalarından soru kopyalama.
Yalnızca JSON döndür: {{"questions":[{{"prompt":"...","options":{{"A":"...","B":"...","C":"...","D":"..."}},"correct_option":"A","explanation":"...","difficulty":"easy|medium|hard"}}]}}
"""
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    try:
        parsed: Any = json.loads(response.text or "{}")
        exam = GeneratedExam.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise ValueError("Gemini yanıtı beklenen soru biçimine uymuyor.") from exc
    if len(exam.questions) != count:
        raise ValueError(f"Gemini {count} yerine {len(exam.questions)} soru üretti.")
    for q in exam.questions:
        if set(q.options) != {"A", "B", "C", "D"} or q.correct_option not in {"A", "B", "C", "D"}:
            raise ValueError("Bir sorunun dört seçeneği veya doğru cevap anahtarı hatalı.")
        if len({v.strip() for v in q.options.values()}) != 4:
            raise ValueError("Bir soruda tekrar eden seçenekler bulundu.")
        if q.difficulty not in {"easy", "medium", "hard"}:
            q.difficulty = "medium"
    return exam.questions
