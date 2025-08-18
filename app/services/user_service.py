from typing import List, Optional, Dict, Any
from app.services.auth_service import MOCK_USERS_DB
from app import schemas

async def get_users(
    page: int, limit: int, role: Optional[str], status: Optional[str], search: Optional[str]
) -> Dict[str, Any]:
    """Retrieves a list of users with filtering and pagination."""
    # Convert dict to list for processing
    items = list(MOCK_USERS_DB.values())

    if role:
        items = [u for u in items if u['role'] == role]
    if status:
        items = [u for u in items if u['status'] == status]
    if search:
        items = [u for u in items if search.lower() in u['name'].lower() or search.lower() in u['email'].lower()]

    # Exclude password hash from response
    response_items = []
    for item in items:
        # Pydantic model will filter this, but it's good practice to remove it
        user_data = item.copy()
        user_data.pop('hashed_password', None)
        response_items.append(user_data)

    # Pagination
    total = len(response_items)
    start = (page - 1) * limit
    end = start + limit
    paginated_items = response_items[start:end]

    return {
        "items": paginated_items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": (total + limit - 1) // limit
        }
    }
