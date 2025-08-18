from fastapi import APIRouter, Query
from app.services import address_service

router = APIRouter()

@router.get("/search", summary="우편번호 검색")
async def search_address(
    postalCode: str = Query(..., pattern=r'^\d{5}$')
):
    """Search address by postal code."""
    result = await address_service.search_by_postal_code(postalCode)
    return {"success": True, "data": result}

@router.get("/reverse-geocode", summary="역지오코딩")
async def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180)
):
    """Reverse geocode from coordinates."""
    result = await address_service.search_by_coordinates(lat, lng)
    return {"success": True, "data": result}
