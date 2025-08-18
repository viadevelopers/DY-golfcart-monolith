from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone
from app import schemas
from app.services import golf_course_service

# ===================================================================
#  Mock Database for Sandbox Environment
# ===================================================================
MOCK_CARTS_DB: List[Dict[str, Any]] = []
# ===================================================================

async def create_cart(cart_data: schemas.CartCreateRequest) -> Dict[str, Any]:
    """Creates a new cart in the mock DB."""
    # Check if the golf course exists
    golf_course = await golf_course_service.get_golf_course_by_id(cart_data.golfCourseId)
    if not golf_course:
        raise ValueError("해당 골프장을 찾을 수 없습니다.")

    new_cart = cart_data.model_dump()
    new_cart.update({
        "id": str(uuid4()),
        "status": "AVAILABLE",
        "batteryLevel": 100,
        "batteryStatus": "NORMAL",
        "isCharging": False,
        "golfCourseName": golf_course["name"],
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })
    MOCK_CARTS_DB.append(new_cart)
    return new_cart

async def get_cart_by_id(cart_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single cart by its ID."""
    for cart in MOCK_CARTS_DB:
        if cart["id"] == cart_id:
            # Simulate detailed view
            return {**cart, "specifications": {}, "battery": {}, "maintenance": {}}
    return None

async def get_carts(
    page: int, limit: int, golf_course_id: Optional[str], status: Optional[str],
    search: Optional[str]
) -> Dict[str, Any]:
    """Retrieves a list of carts with filtering and pagination."""
    items = MOCK_CARTS_DB

    if golf_course_id:
        items = [c for c in items if c['golfCourseId'] == golf_course_id]
    if status:
        items = [c for c in items if c['status'] == status]
    if search:
        items = [c for c in items if search.lower() in c['cartNumber'].lower() or search.lower() in c['modelName'].lower()]

    # Pagination
    total = len(items)
    start = (page - 1) * limit
    end = start + limit
    paginated_items = items[start:end]

    return {
        "items": paginated_items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": (total + limit - 1) // limit
        }
    }

async def update_cart(cart_id: str, cart_update: schemas.CartUpdateRequest) -> Optional[Dict[str, Any]]:
    """Updates a cart's information."""
    for i, cart in enumerate(MOCK_CARTS_DB):
        if cart["id"] == cart_id:
            update_data = cart_update.model_dump(exclude_unset=True)
            MOCK_CARTS_DB[i].update(update_data)
            MOCK_CARTS_DB[i]["updatedAt"] = datetime.now(timezone.utc)
            return MOCK_CARTS_DB[i]
    return None

async def delete_cart(cart_id: str) -> Optional[Dict[str, Any]]:
    """Deletes a cart from the mock DB."""
    for i, cart in enumerate(MOCK_CARTS_DB):
        if cart["id"] == cart_id:
            return MOCK_CARTS_DB.pop(i)
    return None

async def update_cart_status(cart_id: str, status_update: schemas.CartStatusUpdateRequest) -> Optional[Dict[str, Any]]:
    """Updates a cart's status."""
    for cart in MOCK_CARTS_DB:
        if cart["id"] == cart_id:
            cart["status"] = status_update.status
            cart["updatedAt"] = datetime.now(timezone.utc)
            return {
                "id": cart_id,
                "status": cart["status"],
                "statusChangedAt": cart["updatedAt"]
            }
    return None

async def get_cart_battery(cart_id: str) -> Optional[Dict[str, Any]]:
    """Gets mock battery status for a cart."""
    if not any(c['id'] == cart_id for c in MOCK_CARTS_DB):
        return None
    return {
        "cartId": cart_id,
        "level": 92,
        "status": "NORMAL",
        "isCharging": False,
        "lastUpdate": datetime.now(timezone.utc)
    }

async def get_cart_location(cart_id: str) -> Optional[Dict[str, Any]]:
    """Gets mock location for a cart."""
    if not any(c['id'] == cart_id for c in MOCK_CARTS_DB):
        return None
    return {
        "cartId": cart_id,
        "latitude": 37.4,
        "longitude": 127.1,
        "speed": 12.5,
        "lastUpdate": datetime.now(timezone.utc)
    }
