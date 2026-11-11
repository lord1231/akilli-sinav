from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterParent(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=160)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: str
    grade_level: int | None = None
    model_config = ConfigDict(from_attributes=True)


class CreateStudent(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=160)
    grade_level: int = Field(ge=4, le=5)
    consent_confirmed: bool

    @field_validator("consent_confirmed")
    @classmethod
    def require_parent_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Öğrenci hesabı için veli onayı gereklidir.")
        return value


class ExamGenerateRequest(BaseModel):
    student_id: UUID
    learning_outcome_id: UUID
    title: str = Field(min_length=3, max_length=200)


class AnswerRequest(BaseModel):
    selected_option: str = Field(pattern="^[ABCD]$")
