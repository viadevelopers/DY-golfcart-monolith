from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user, require_role


router = APIRouter(prefix="/api", tags=["protected"])


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "username": current_user.get("preferred_username"),
        "email": current_user.get("email"),
        "roles": current_user.get("realm_access", {}).get("roles", []),
        "sub": current_user.get("sub")
    }


@router.get("/admin")
async def admin_only(current_user: dict = Depends(require_role("admin"))):
    return {
        "message": "Welcome admin!",
        "user": current_user.get("preferred_username")
    }


@router.get("/user-data")
async def get_user_data(current_user: dict = Depends(get_current_user)):
    return {
        "message": "This is protected user data",
        "user_id": current_user.get("sub"),
        "data": {
            "example": "This could be user-specific data from your database"
        }
    }