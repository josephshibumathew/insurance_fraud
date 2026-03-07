"""Authentication request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime
    last_login: datetime | None
    permissions: dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    user: UserInfo
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="surveyor")
    is_active: bool = True


class AdminUpdateRoleRequest(BaseModel):
    role: str


class AdminRoleRequest(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    permissions: dict = Field(default_factory=dict)


class AdminUpdatePermissionsRequest(BaseModel):
    permissions: dict = Field(default_factory=dict)


class AdminActivateRequest(BaseModel):
    is_active: bool
