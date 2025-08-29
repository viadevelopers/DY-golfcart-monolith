"""
Security utilities for authentication and authorization.
JWT-based authentication for manufacturer and golf course users.
"""
from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 schemes for different user types
oauth2_manufacturer = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/manufacturer/login"
)
oauth2_golf_course = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/golf-course/login"
)


class UserType:
    """User type constants."""
    MANUFACTURER = "manufacturer"
    GOLF_COURSE = "golf_course"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Payload data including user_id, user_type, etc.
        expires_delta: Token expiration time
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT refresh token."""
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthContext:
    """Authentication context for request."""
    
    def __init__(
        self,
        user_id: str,
        user_type: str,
        email: str,
        golf_course_id: Optional[str] = None,
        permissions: Optional[list] = None
    ):
        self.user_id = user_id
        self.user_type = user_type
        self.email = email
        self.golf_course_id = golf_course_id
        self.permissions = permissions or []
    
    @property
    def is_manufacturer(self) -> bool:
        """Check if user is manufacturer."""
        return self.user_type == UserType.MANUFACTURER
    
    @property
    def is_golf_course(self) -> bool:
        """Check if user is golf course user."""
        return self.user_type == UserType.GOLF_COURSE
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions


async def get_current_user(
    token: str = Depends(oauth2_manufacturer),
    db: Session = Depends(get_db)
) -> AuthContext:
    """
    Get current authenticated user from token.
    Works for both manufacturer and golf course users.
    """
    payload = decode_token(token)
    
    user_id = payload.get("user_id")
    user_type = payload.get("user_type")
    email = payload.get("email")
    golf_course_id = payload.get("golf_course_id")
    
    if not user_id or not user_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    return AuthContext(
        user_id=user_id,
        user_type=user_type,
        email=email,
        golf_course_id=golf_course_id,
        permissions=payload.get("permissions", [])
    )


async def require_manufacturer(
    current_user: AuthContext = Depends(get_current_user)
) -> AuthContext:
    """Require manufacturer user."""
    if not current_user.is_manufacturer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manufacturer access required"
        )
    return current_user


async def require_golf_course(
    current_user: AuthContext = Depends(get_current_user)
) -> AuthContext:
    """Require golf course user."""
    if not current_user.is_golf_course:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Golf course access required"
        )
    return current_user