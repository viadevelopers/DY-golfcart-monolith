from typing import Dict, Any, Optional

async def search_by_postal_code(postal_code: str) -> Dict[str, Any]:
    """
    Simulates searching for an address by postal code.
    Returns mock data.
    """
    return {
        "postalCode": postal_code,
        "address": "서울특별시 강남구 테헤란로 212 (역삼동)",
        "englishAddress": "212, Teheran-ro, Gangnam-gu, Seoul, Republic of Korea",
        "addressType": "ROAD",
        "latitude": 37.5009,
        "longitude": 127.0396
    }

async def search_by_coordinates(lat: float, lng: float) -> Dict[str, Any]:
    """
    Simulates reverse geocoding.
    Returns mock data.
    """
    return {
        "address": "서울특별시 강남구 역삼동",
        "postalCode": "06234",
        "addressType": "JIBUN",
        "building": "멀티캠퍼스",
        "coordinates": {
            "latitude": lat,
            "longitude": lng
        }
    }
