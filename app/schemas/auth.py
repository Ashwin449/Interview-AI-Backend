import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str
    last_name: str
    phone: str | None = None
    role: str = Field(default="USER", description="ADMIN | INTERVIEWER | USER")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    is_active: bool
    is_verified: bool
    roles: list[str] = []


class CurrentUserResponse(BaseModel):
    id: int
    full_name: str
    first_name: str
    last_name: str
    email: str
    role: str
    initials: str

    class Config:
        from_attributes = True