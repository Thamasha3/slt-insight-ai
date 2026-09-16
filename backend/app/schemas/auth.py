from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import Region


class RegisterRequest(BaseModel):
    """Public registration. There is no `role` field — callers cannot request ADMIN."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    requested_region: Region | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(character.isdigit() for character in value):
            raise ValueError("Password must contain at least one digit")
        if not any(character.isalpha() for character in value):
            raise ValueError("Password must contain at least one letter")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    status: str


class CurrentUserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    region: str | None
    status: str
