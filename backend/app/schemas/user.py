from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import Region, Role, UserStatus


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    region: str | None
    status: str


class UpdateOwnProfileRequest(BaseModel):
    """Employees may change their name only. Extra fields such as role are rejected."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None


class AdminUpdateUserRequest(BaseModel):
    name: str | None = None
    role: Role | None = None
    region: Region | None = None
    status: UserStatus | None = None


class ApprovalDecisionRequest(BaseModel):
    role: Role
    region: Region | None = None


class AdminCreateUserRequest(BaseModel):
    """Admin-created accounts skip PENDING and become ACTIVE immediately."""

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Role
    region: Region | None = None
