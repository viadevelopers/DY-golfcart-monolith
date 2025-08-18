from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from app import schemas
from app.services import cart_service
from app.core.security import get_current_user

router = APIRouter()

# Dependency for this router
auth_dependency = Depends(get_current_user)

@router.post("/", response_model=schemas.Cart, status_code=status.HTTP_201_CREATED, summary="카트 생성")
async def create_cart(cart_in: schemas.CartCreateRequest, user: schemas.User = auth_dependency):
    try:
        return await cart_service.create_cart(cart_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/", response_model=schemas.CartListResponse, summary="카트 목록 조회")
async def get_carts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    golfCourseId: Optional[str] = Query(None),
    status: Optional[schemas.CartStatus] = Query(None),
    search: Optional[str] = Query(None),
    user: schemas.User = auth_dependency
):
    return await cart_service.get_carts(page, limit, golfCourseId, status, search)

@router.get("/{cart_id}", response_model=schemas.CartDetail, summary="카트 상세 조회")
async def get_cart(cart_id: str, user: schemas.User = auth_dependency):
    cart = await cart_service.get_cart_by_id(cart_id)
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="카트를 찾을 수 없음")
    return cart

@router.put("/{cart_id}", response_model=schemas.Cart, summary="카트 수정")
async def update_cart(cart_id: str, cart_in: schemas.CartUpdateRequest, user: schemas.User = auth_dependency):
    cart = await cart_service.update_cart(cart_id, cart_in)
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="카트를 찾을 수 없음")
    return cart

@router.delete("/{cart_id}", status_code=status.HTTP_200_OK, summary="카트 삭제")
async def delete_cart(cart_id: str, user: schemas.User = auth_dependency):
    cart = await cart_service.delete_cart(cart_id)
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="카트를 찾을 수 없음")
    return {"success": True, "message": "카트가 삭제되었습니다."}

@router.patch("/{cart_id}/status", summary="카트 상태 업데이트")
async def update_cart_status(cart_id: str, status_in: schemas.CartStatusUpdateRequest, user: schemas.User = auth_dependency):
    result = await cart_service.update_cart_status(cart_id, status_in)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="카트를 찾을 수 없음")
    return {"success": True, "data": result}

@router.get("/{cart_id}/battery", summary="카트 배터리 상태 조회")
async def get_cart_battery(cart_id: str, user: schemas.User = auth_dependency):
    result = await cart_service.get_cart_battery(cart_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="카트를 찾을 수 없음")
    return {"success": True, "data": result}

@router.get("/{cart_id}/location", summary="카트 위치 조회")
async def get_cart_location(cart_id: str, user: schemas.User = auth_dependency):
    result = await cart_service.get_cart_location(cart_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="카트를 찾을 수 없음")
    return {"success": True, "data": result}
