import json

import pytest

from app.core.config import settings
from app.services import question_generator


def make_questions(count=25):
    return [
        {
            "prompt": f"Soru metni numara {index} nedir?",
            "options": {
                "A": f"Seçenek A {index}",
                "B": f"Seçenek B {index}",
                "C": f"Seçenek C {index}",
                "D": f"Seçenek D {index}",
            },
            "correct_option": "A",
            "explanation": f"Bu sorunun açıklaması {index}.",
            "difficulty": "medium",
        }
        for index in range(1, count + 1)
    ]


class FakeModels:
    def __init__(self, response_text):
        self.response_text = response_text
        self.last_request = None

    def generate_content(self, **kwargs):
        self.last_request = kwargs
        return type("Response", (), {"text": self.response_text})()


class FakeClient:
    def __init__(self, response_text):
        self.models = FakeModels(response_text)


def install_fake_client(monkeypatch, payload):
    fake = FakeClient(json.dumps(payload, ensure_ascii=False))
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-test")
    monkeypatch.setattr(
        question_generator.genai,
        "Client",
        lambda api_key: fake,
    )
    return fake


def test_generate_questions_returns_exactly_25_valid_questions(monkeypatch):
    fake = install_fake_client(monkeypatch, {"questions": make_questions()})

    result = question_generator.generate_questions(
        "MAT.5.1.1", "Doğal sayılarla işlem yapar.", 5, "Matematik"
    )

    assert len(result) == 25
    assert result[0].correct_option == "A"
    assert set(result[0].options) == {"A", "B", "C", "D"}
    assert fake.models.last_request["model"] == "gemini-test"
    assert fake.models.last_request["config"]["response_mime_type"] == "application/json"
    assert fake.models.last_request["config"]["response_schema"] is question_generator.GeneratedExam


def test_generate_questions_requires_gemini_key(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    with pytest.raises(RuntimeError, match="API anahtarı"):
        question_generator.generate_questions("K1", "Kazanım açıklaması.", 5, "Matematik")


def test_generate_questions_rejects_wrong_question_count(monkeypatch):
    install_fake_client(monkeypatch, {"questions": make_questions(24)})

    with pytest.raises(ValueError, match="25 yerine 24"):
        question_generator.generate_questions("K1", "Kazanım açıklaması.", 5, "Matematik")


def test_generate_questions_rejects_invalid_options(monkeypatch):
    questions = make_questions()
    questions[0]["options"]["D"] = questions[0]["options"]["C"]
    install_fake_client(monkeypatch, {"questions": questions})

    with pytest.raises(ValueError, match="beklenen soru biçimine"):
        question_generator.generate_questions("K1", "Kazanım açıklaması.", 5, "Matematik")


def test_generate_questions_rejects_duplicate_prompts(monkeypatch):
    questions = make_questions()
    questions[1]["prompt"] = questions[0]["prompt"]
    install_fake_client(monkeypatch, {"questions": questions})

    with pytest.raises(ValueError, match="aynı veya çok benzer"):
        question_generator.generate_questions("K1", "Kazanım açıklaması.", 5, "Matematik")


def test_generate_questions_only_allows_25_question_exam(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-api-key")

    with pytest.raises(ValueError, match="tam 25"):
        question_generator.generate_questions(
            "K1", "Kazanım açıklaması.", 5, "Matematik", count=10
        )
