# ─────────────────────────────────────────────────────────────
#  app/schemas/auth.py  —  Auth request/response schemas
# ─────────────────────────────────────────────────────────────
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator
import re


# ── Register ──────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    confirm_password: str

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Full name cannot be empty")
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    is_admin: bool

    model_config = {"from_attributes": True}


class RegisterResponse(BaseModel):
    user: UserResponse
    message: str = "Account created successfully"


# ── Login ─────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int           # seconds until access token expires


# ── Refresh ───────────────────────────────────────────────────
class RefreshRequest(BaseModel):
    refresh_token: str


# ── Password change ───────────────────────────────────────────
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("New passwords do not match")
        return self


# ── Token payload (internal) ──────────────────────────────────
class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    token_type: str = "access"   # "access" | "refresh"
