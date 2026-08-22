from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.users import UserPublic


def clean_required(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("must not be empty")
    return cleaned


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str = Field(min_length=8)

    @field_validator("name", "phone")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return clean_required(value)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(UserPublic):
    pass
