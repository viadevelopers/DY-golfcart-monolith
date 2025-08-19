from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.services import auth_service
from app.core.security import create_access_token, create_refresh_token
from app.schemas import LoginResponse, Token, RefreshTokenRequest, SuccessResponse, User

router = APIRouter()

@router.post("/login", response_model=LoginResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    User login to get access and refresh tokens.
    """
    user_dict = await auth_service.authenticate_user(
        email=form_data.username, password=form_data.password
    )
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # The service returns a dict, we cast it to the Pydantic model
    user = User(**user_dict)

    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.email})

    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "user": user,
    }

@router.post("/refresh", response_model=Token)
async def refresh_access_token(request: RefreshTokenRequest):
    """
    Refresh the access token using a refresh token.
    (Mock implementation)
    """
    # In a real app, you would verify the refresh token and find the user
    # For now, we'll just create new tokens for the admin user as a mock
    access_token = create_access_token(data={"sub": "admin@example.com", "role": "ADMIN"})
    refresh_token = create_refresh_token(data={"sub": "admin@example.com"})
    return {"accessToken": access_token, "refreshToken": refresh_token}

@router.post("/logout", response_model=SuccessResponse)
async def logout():
    """
    User logout.
    (Mock implementation)
    """
    # In a real app, you might blacklist the token or clear a server-side session
    return {"success": True, "message": "로그아웃되었습니다."}