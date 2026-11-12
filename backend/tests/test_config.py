import pytest
from pydantic import ValidationError

from app.core.config import Settings


def valid_production_settings(**overrides):
    values = {
        "APP_ENV": "production",
        "APP_DEBUG": False,
        "SECRET_KEY": "random-production-secret-" + "x" * 48,
        "DATABASE_URL": "postgresql+psycopg://sinav:strong-db-pass@postgres.internal:5432/akilli_sinav",
        "GEMINI_API_KEY": "real-gemini-api-key",
        "APP_BASE_URL": "https://sinav.example.net",
        "SMTP_HOST": "smtp.example.net",
        "SMTP_PORT": 587,
        "SMTP_USERNAME": "mailer",
        "SMTP_PASSWORD": "mail-password",
        "SMTP_FROM_EMAIL": "noreply@example.net",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_valid_production_settings_are_accepted():
    settings = valid_production_settings()
    assert settings.APP_ENV == "production"
    assert settings.APP_DEBUG is False


@pytest.mark.parametrize("secret", [
    "development-only-change-this-secret",
    "replace-with-at-least-32-random-characters",
    "short",
])
def test_production_rejects_default_or_weak_secret(secret):
    with pytest.raises(ValidationError):
        valid_production_settings(SECRET_KEY=secret)


def test_production_rejects_local_database_url():
    with pytest.raises(ValidationError):
        valid_production_settings(
            DATABASE_URL="postgresql+psycopg://sinav:password@localhost:5432/akilli_sinav"
        )


def test_production_requires_gemini_key():
    with pytest.raises(ValidationError):
        valid_production_settings(GEMINI_API_KEY="")


@pytest.mark.parametrize("url", [
    "http://sinav.example.net",
    "https://localhost",
    "https://your-domain.example",
])
def test_production_requires_real_https_app_url(url):
    with pytest.raises(ValidationError):
        valid_production_settings(APP_BASE_URL=url)


def test_production_requires_smtp_for_recovery_and_notifications():
    with pytest.raises(ValidationError):
        valid_production_settings(SMTP_HOST="", SMTP_FROM_EMAIL="")
