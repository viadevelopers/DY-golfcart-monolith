from fastapi import APIRouter, Depends, Query
from typing import Optional
from app import schemas
from app.services import user_service
from app.core.security import get_current_user

router = APIRouter()
auth_dependency = Depends(get_current_user)

@router.get("/", response_model=schemas.UserListResponse, summary="사용자 목록 조회")
async def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[schemas.Role] = Query(None),
    status: Optional[schemas.UserStatus] = Query(None),
    search: Optional[str] = Query(None),
    user: schemas.User = auth_dependency
):
    """Retrieve a list of users with filtering and pagination."""
    # The role and status enums from the schema will be passed as strings
    role_str = role.value if role else None
    status_str = status.value if status else None
    return await user_service.get_users(page, limit, role_str, status_str, search)
