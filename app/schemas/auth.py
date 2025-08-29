"""
Authentication schemas.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class UserInfo(BaseModel):
    """Basic user information."""
    id: str
    email: str
    name: str
    user_type: str  # manufacturer or golf_course
    golf_course_id: Optional[str] = None
    is_active: bool
    last_login: Optional[datetime] = None


class LoginResponse(BaseModel):
    """Complete login response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo