"""
Authentication API endpoints.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    AuthContext,
    get_current_user
)
from app.models.user import ManufacturerUser, GolfCourseUser
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserInfo
)


router = APIRouter()


def authenticate_manufacturer(
    db: Session,
    email: str,
    password: str
) -> ManufacturerUser:
    """Authenticate manufacturer user."""
    user = db.query(ManufacturerUser).filter(
        ManufacturerUser.email == email
    ).first()
    
    if not user or not verify_password(password, user.password_hash):
        return None
    
    if not user.is_active:
        return None
    
    return user


def authenticate_golf_course(
    db: Session,
    email: str,
    password: str
) -> GolfCourseUser:
    """Authenticate golf course user."""
    user = db.query(GolfCourseUser).filter(
        GolfCourseUser.email == email
    ).first()
    
    if not user or not verify_password(password, user.password_hash):
        return None
    
    if not user.is_active:
        return None
    
    return user


@router.post("/manufacturer/login", response_model=LoginResponse)
async def manufacturer_login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Manufacturer user login.
    Returns JWT tokens for authentication.
    """
    user = authenticate_manufacturer(db, request.email, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token = create_access_token(
        data={
            "user_id": str(user.id),
            "email": user.email,
            "user_type": "manufacturer",
            "is_superuser": user.is_superuser
        }
    )
    
    refresh_token = create_refresh_token(
        data={
            "user_id": str(user.id),
            "user_type": "manufacturer"
        }
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600,  # 1 hour
        user=UserInfo(
            id=str(user.id),
            email=user.email,
            name=user.name,
            user_type="manufacturer",
            is_active=user.is_active,
            last_login=user.last_login
        )
    )


@router.post("/golf-course/login", response_model=LoginResponse)
async def golf_course_login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Golf course user login.
    Returns JWT tokens for authentication.
    """
    user = authenticate_golf_course(db, request.email, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token = create_access_token(
        data={
            "user_id": str(user.id),
            "email": user.email,
            "user_type": "golf_course",
            "golf_course_id": str(user.golf_course_id),
            "is_admin": user.is_admin
        }
    )
    
    refresh_token = create_refresh_token(
        data={
            "user_id": str(user.id),
            "user_type": "golf_course",
            "golf_course_id": str(user.golf_course_id)
        }
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600,  # 1 hour
        user=UserInfo(
            id=str(user.id),
            email=user.email,
            name=user.name,
            user_type="golf_course",
            golf_course_id=str(user.golf_course_id),
            is_active=user.is_active,
            last_login=user.last_login
        )
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    try:
        payload = decode_token(request.refresh_token)
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    # Check token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    
    user_id = payload.get("user_id")
    user_type = payload.get("user_type")
    
    # Get user based on type
    if user_type == "manufacturer":
        user = db.query(ManufacturerUser).filter(
            ManufacturerUser.id == user_id
        ).first()
    elif user_type == "golf_course":
        user = db.query(GolfCourseUser).filter(
            GolfCourseUser.id == user_id
        ).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user type",
        )
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    # Create new access token
    token_data = {
        "user_id": str(user.id),
        "email": user.email,
        "user_type": user_type
    }
    
    if user_type == "golf_course":
        token_data["golf_course_id"] = str(user.golf_course_id)
        token_data["is_admin"] = user.is_admin
    elif user_type == "manufacturer":
        token_data["is_superuser"] = user.is_superuser
    
    access_token = create_access_token(data=token_data)
    
    # Create new refresh token
    new_refresh_token = create_refresh_token(
        data={
            "user_id": str(user.id),
            "user_type": user_type,
            "golf_course_id": str(user.golf_course_id) if user_type == "golf_course" else None
        }
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=3600
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information.
    """
    # Get user based on type
    if current_user.user_type == "manufacturer":
        user = db.query(ManufacturerUser).filter(
            ManufacturerUser.id == current_user.user_id
        ).first()
    else:
        user = db.query(GolfCourseUser).filter(
            GolfCourseUser.id == current_user.user_id
        ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserInfo(
        id=str(user.id),
        email=user.email,
        name=user.name,
        user_type=current_user.user_type,
        golf_course_id=current_user.golf_course_id,
        is_active=user.is_active,
        last_login=user.last_login
    )


@router.post("/logout")
async def logout(
    current_user: AuthContext = Depends(get_current_user)
):
    """
    Logout endpoint.
    Note: With JWT, actual logout is handled client-side by removing the token.
    This endpoint can be used for server-side cleanup if needed.
    """
    # TODO: Add token to blacklist if implementing token revocation
    # TODO: Clear any server-side session data
    
    return {"message": "Successfully logged out"}