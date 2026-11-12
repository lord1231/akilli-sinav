from pydantic import model_validator
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
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.APP_ENV.lower() == "production":
            if len(self.SECRET_KEY) < 32 or "replace-with" in self.SECRET_KEY.lower():
                raise ValueError("Production ortamında en az 32 karakterli gerçek SECRET_KEY tanımlanmalı.")
            if self.APP_DEBUG:
                raise ValueError("Production ortamında APP_DEBUG=false olmalı.")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
