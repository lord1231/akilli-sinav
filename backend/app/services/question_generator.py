import json
import re
from typing import Any, Literal

from google import genai
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.core.config import settings


class GeneratedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=10, max_length=1200)
    options: dict[str, str]
    correct_option: Literal["A", "B", "C", "D"]
    explanation: str = Field(min_length=5, max_length=1200)
    difficulty: Literal["easy", "medium", "hard"] = "medium"

    @field_validator("prompt", "explanation")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Soru ve açıklama boş olamaz.")
        return value.strip()

    @model_validator(mode="after")
    def validate_options(self):
        if set(self.options) != {"A", "B", "C", "D"}:
            raise ValueError("Her soruda A, B, C ve D seçenekleri bulunmalı.")
        cleaned = [value.strip() for value in self.options.values()]
        if any(not value for value in cleaned):
            raise ValueError("Seçenekler boş olamaz.")
        if len({value.casefold() for value in cleaned}) != 4:
            raise ValueError("Bir soruda tekrar eden seçenekler bulundu.")
        self.options = {key: value.strip() for key, value in self.options.items()}
        return self


class GeneratedExam(BaseModel):
    model_config = ConfigDict(extra="forbid")
    questions: list[GeneratedQuestion] = Field(min_length=1)


def _normalize_prompt(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def generate_questions(
    outcome_code: str,
    outcome_description: str,
    grade: int,
    subject: str,
    count: int = 25,
) -> list[GeneratedQuestion]:
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("Gemini API anahtarı sunucu ortamında tanımlanmamış.")
    if count != 25:
        raise ValueError("Akıllı Sınav standardında her sınav tam 25 sorudan oluşmalıdır.")
    if not outcome_code.strip() or not outcome_description.strip() or not subject.strip():
        raise ValueError("Ders ve kazanım bilgileri boş olamaz.")

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = f"""
Türkçe eğitim ölçme-değerlendirme uzmanısın. {grade}. sınıf {subject} dersi için
yalnızca aşağıdaki kazanımı ölçen, özgün ve yaşa uygun TAM 25 adet çoktan seçmeli soru üret.
Kazanım kodu: {outcome_code}
Kazanım: {outcome_description}

ZORUNLU KURALLAR:
- Her soru açık, tek anlamlı ve öğrencinin sınıf düzeyine uygun olmalı.
- Her soruda A, B, C, D olmak üzere tam dört farklı seçenek bulunmalı.
- Her sorunun yalnızca bir doğru cevabı olmalı.
- Doğru cevap seçeneklerden biriyle birebir eşleşmeli.
- Sorular aynı bilgiyi farklı kelimelerle tekrar etmemeli.
- Her soruya kısa, öğretici bir açıklama ekle.
- Zorluk düzeyini easy, medium veya hard olarak belirt.
- Telifli kitaplardan veya yayımlanmış soru bankalarından soru kopyalama.
- Kazanım dışına çıkma, bilgi uydurma ve cevabı belirsiz soru yazma.
Yalnızca istenen JSON şemasına uygun çıktı üret.
"""

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": GeneratedExam,
            },
        )
        parsed: Any = json.loads(response.text or "{}")
        exam = GeneratedExam.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise ValueError("Gemini yanıtı beklenen soru biçimine uymuyor.") from exc
    except Exception as exc:
        raise RuntimeError("Gemini servisine ulaşılamadı veya yanıt alınamadı.") from exc

    if len(exam.questions) != count:
        raise ValueError(f"Gemini {count} yerine {len(exam.questions)} soru üretti.")

    normalized = [_normalize_prompt(question.prompt) for question in exam.questions]
    if len(set(normalized)) != count:
        raise ValueError("Gemini aynı veya çok benzer soru metinleri üretti.")

    return exam.questions
