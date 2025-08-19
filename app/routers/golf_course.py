from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
from app import schemas
from app.services import golf_course_service
from app.core.security import get_current_user

router = APIRouter()

@router.post(
    "/",
    response_model=schemas.GolfCourse,
    status_code=status.HTTP_201_CREATED,
    summary="골프장 생성"
)
async def create_golf_course(
    course_in: schemas.GolfCourseCreateRequest,
    current_user: schemas.User = Depends(get_current_user)
):
    """Create a new golf course."""
    try:
        return await golf_course_service.create_golf_course(course_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.get(
    "/",
    response_model=schemas.GolfCourseListResponse,
    summary="골프장 목록 조회"
)
async def get_golf_courses(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[schemas.GolfCourseStatus] = Query(None),
    sortBy: str = Query("createdAt", enum=["name", "createdAt", "updatedAt"]),
    sortOrder: str = Query("desc", enum=["asc", "desc"]),
    current_user: schemas.User = Depends(get_current_user)
):
    """Retrieve a list of golf courses."""
    return await golf_course_service.get_golf_courses(page, limit, search, status, sortBy, sortOrder)

@router.get(
    "/check-duplicate",
    summary="골프장명 중복 확인"
)
async def check_duplicate(
    name: str,
    excludeId: Optional[str] = None,
    current_user: schemas.User = Depends(get_current_user)
):
    """Check if a golf course name is a duplicate."""
    is_duplicate = await golf_course_service.check_duplicate_name(name, excludeId)
    return {"isDuplicate": is_duplicate}


@router.get(
    "/{course_id}",
    response_model=schemas.GolfCourseDetail,
    summary="골프장 상세 조회"
)
async def get_golf_course(
    course_id: str,
    current_user: schemas.User = Depends(get_current_user)
):
    """Retrieve details of a specific golf course."""
    course = await golf_course_service.get_golf_course_by_id(course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="골프장을 찾을 수 없음")
    return course

@router.put(
    "/{course_id}",
    response_model=schemas.GolfCourse,
    summary="골프장 수정"
)
async def update_golf_course(
    course_id: str,
    course_in: schemas.GolfCourseUpdateRequest,
    current_user: schemas.User = Depends(get_current_user)
):
    """Update an existing golf course."""
    course = await golf_course_service.update_golf_course(course_id, course_in)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="골프장을 찾을 수 없음")
    return course

@router.delete(
    "/{course_id}",
    status_code=status.HTTP_200_OK,
    summary="골프장 삭제"
)
async def delete_golf_course(
    course_id: str,
    current_user: schemas.User = Depends(get_current_user)
):
    """Delete a golf course."""
    course = await golf_course_service.delete_golf_course(course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="골프장을 찾을 수 없음")
    return {"success": True, "message": "골프장이 삭제되었습니다."}
