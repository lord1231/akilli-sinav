from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Akilli Sinav API"
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    SECRET_KEY: str = "development-only-change-this-secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = "postgresql+psycopg://sinav_user:change_me@localhost:5432/akilli_sinav"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    APP_BASE_URL: str = "http://localhost:8000"
    SMTP_HOST: str = ""
    SMTP_PORT: int = Field(default=587, ge=1, le=65535)
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.APP_ENV.lower() != "production":
            return self

        known_weak_keys = {
            "development-only-change-this-secret",
            "change-this-secret",
            "secret",
            "changeme",
        }
        if (
            len(self.SECRET_KEY) < 32
            or self.SECRET_KEY.lower() in known_weak_keys
            or "replace-with" in self.SECRET_KEY.lower()
        ):
            raise ValueError("Production ortamında varsayılan olmayan, en az 32 karakterli SECRET_KEY tanımlanmalı.")
        if self.APP_DEBUG:
            raise ValueError("Production ortamında APP_DEBUG=false olmalı.")

        database = urlsplit(self.DATABASE_URL)
        if (
            database.scheme != "postgresql+psycopg"
            or not database.hostname
            or database.hostname.lower() in {"localhost", "127.0.0.1", "::1"}
            or any(marker in self.DATABASE_URL.lower() for marker in ("change_me", "replace-with"))
        ):
            raise ValueError("Production ortamında yerel olmayan, gerçek PostgreSQL DATABASE_URL tanımlanmalı.")

        if not self.GEMINI_API_KEY.strip() or "replace-with" in self.GEMINI_API_KEY.lower():
            raise ValueError("Production ortamında GEMINI_API_KEY tanımlanmalı.")

        app_url = urlsplit(self.APP_BASE_URL)
        if (
            app_url.scheme != "https"
            or not app_url.hostname
            or app_url.hostname.lower() in {"localhost", "127.0.0.1", "::1"}
            or app_url.username
            or app_url.password
        ):
            raise ValueError("Production ortamında gerçek alan adına ait HTTPS APP_BASE_URL tanımlanmalı.")

        if not self.SMTP_HOST.strip() or not self.SMTP_FROM_EMAIL.strip():
            raise ValueError("Production ortamında parola kurtarma ve veli bildirimleri için SMTP_HOST ve SMTP_FROM_EMAIL tanımlanmalı.")
        if self.SMTP_USERNAME and not self.SMTP_PASSWORD:
            raise ValueError("SMTP_USERNAME tanımlandıysa SMTP_PASSWORD da tanımlanmalı.")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
