from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone
from app import schemas

# ===================================================================
#  Mock Database for Sandbox Environment
# ===================================================================
MOCK_GOLF_COURSES_DB: List[Dict[str, Any]] = []
# ===================================================================

async def create_golf_course(course_data: schemas.GolfCourseCreateRequest) -> Dict[str, Any]:
    """Creates a new golf course in the mock DB."""
    if any(gc['name'] == course_data.name for gc in MOCK_GOLF_COURSES_DB):
        raise ValueError("중복된 골프장명입니다")

    new_course = course_data.model_dump()
    new_course.update({
        "id": str(uuid4()),
        "status": "ACTIVE",
        "coursesCount": 0,
        "cartsCount": 0,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    })
    MOCK_GOLF_COURSES_DB.append(new_course)
    return new_course

async def get_golf_course_by_id(course_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single golf course by its ID."""
    for course in MOCK_GOLF_COURSES_DB:
        if course["id"] == course_id:
            # Simulate detailed view
            return {**course, "courses": [], "managers": []}
    return None

async def get_golf_courses(
    page: int, limit: int, search: Optional[str], status: Optional[str],
    sort_by: str, sort_order: str
) -> Dict[str, Any]:
    """Retrieves a list of golf courses with filtering, sorting, and pagination."""
    items = MOCK_GOLF_COURSES_DB

    if search:
        items = [gc for gc in items if search.lower() in gc['name'].lower() or search.lower() in gc['address'].lower()]
    if status:
        items = [gc for gc in items if gc['status'] == status]

    # Sorting
    items.sort(key=lambda x: x.get(sort_by, datetime.min), reverse=sort_order == 'desc')

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

async def update_golf_course(course_id: str, course_update: schemas.GolfCourseUpdateRequest) -> Optional[Dict[str, Any]]:
    """Updates a golf course's information."""
    for i, course in enumerate(MOCK_GOLF_COURSES_DB):
        if course["id"] == course_id:
            update_data = course_update.model_dump(exclude_unset=True)
            MOCK_GOLF_COURSES_DB[i].update(update_data)
            MOCK_GOLF_COURSES_DB[i]["updatedAt"] = datetime.now(timezone.utc)
            return MOCK_GOLF_COURSES_DB[i]
    return None

async def delete_golf_course(course_id: str) -> Optional[Dict[str, Any]]:
    """Deletes a golf course from the mock DB."""
    for i, course in enumerate(MOCK_GOLF_COURSES_DB):
        if course["id"] == course_id:
            return MOCK_GOLF_COURSES_DB.pop(i)
    return None

async def check_duplicate_name(name: str, exclude_id: Optional[str]) -> bool:
    """Checks if a golf course name is a duplicate."""
    for course in MOCK_GOLF_COURSES_DB:
        if course["name"] == name and course["id"] != exclude_id:
            return True
    return False
