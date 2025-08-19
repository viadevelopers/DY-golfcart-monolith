from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from typing import Optional, List
from app import schemas
from app.services import map_service
from app.core.security import get_current_user

router = APIRouter()
auth_dependency = Depends(get_current_user)

@router.post("/", response_model=schemas.Map, status_code=status.HTTP_201_CREATED, summary="맵 생성")
async def create_map(map_in: schemas.MapCreateRequest, user: schemas.User = auth_dependency):
    try:
        return await map_service.create_map(map_in, user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/", response_model=schemas.MapListResponse, summary="맵 목록 조회")
async def get_maps(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    golfCourseId: Optional[str] = Query(None),
    type: Optional[schemas.MapType] = Query(None),
    search: Optional[str] = Query(None),
    user: schemas.User = auth_dependency
):
    return await map_service.get_maps(page, limit, golfCourseId, type, search)

@router.post("/upload-image", summary="맵 이미지 업로드")
async def upload_image(image: UploadFile = File(...), user: schemas.User = auth_dependency):
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="지원하지 않는 파일 형식입니다")
    result = await map_service.upload_map_image(image)
    return {"success": True, "data": result}

@router.post("/upload-metadata", summary="맵 메타데이터 폴더 업로드")
async def upload_metadata(metadata_files: List[UploadFile] = File(...), user: schemas.User = auth_dependency):
    result = await map_service.upload_map_metadata(metadata_files)
    return {"success": True, "data": result}

@router.get("/{map_id}", response_model=schemas.MapDetail, summary="맵 상세 조회")
async def get_map(map_id: str, user: schemas.User = auth_dependency):
    map_obj = await map_service.get_map_by_id(map_id)
    if not map_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="맵을 찾을 수 없음")
    return map_obj

@router.put("/{map_id}", response_model=schemas.Map, summary="맵 수정")
async def update_map(map_id: str, map_in: schemas.MapUpdateRequest, user: schemas.User = auth_dependency):
    map_obj = await map_service.update_map(map_id, map_in, user)
    if not map_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="맵을 찾을 수 없음")
    return map_obj

@router.delete("/{map_id}", status_code=status.HTTP_200_OK, summary="맵 삭제")
async def delete_map(map_id: str, user: schemas.User = auth_dependency):
    map_obj = await map_service.delete_map(map_id)
    if not map_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="맵을 찾을 수 없음")
    return {"success": True, "message": "맵이 삭제되었습니다."}
