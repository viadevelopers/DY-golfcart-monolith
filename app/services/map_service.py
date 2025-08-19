from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import UploadFile
from app import schemas
from app.services import golf_course_service

# ===================================================================
#  Mock Database for Sandbox Environment
# ===================================================================
MOCK_MAPS_DB: List[Dict[str, Any]] = []
# ===================================================================

async def create_map(map_data: schemas.MapCreateRequest, user: schemas.User) -> Dict[str, Any]:
    """Creates a new map in the mock DB."""
    golf_course = await golf_course_service.get_golf_course_by_id(map_data.golfCourseId)
    if not golf_course:
        raise ValueError("해당 골프장을 찾을 수 없습니다.")

    new_map = map_data.model_dump()
    new_map.update({
        "id": str(uuid4()),
        "golfCourseName": golf_course["name"],
        "version": "1.0",
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
        "createdBy": {"id": user.id, "name": user.name},
        "updatedBy": {"id": user.id, "name": user.name}
    })
    MOCK_MAPS_DB.append(new_map)
    return new_map

async def get_maps(
    page: int, limit: int, golf_course_id: Optional[str], type: Optional[str], search: Optional[str]
) -> Dict[str, Any]:
    """Retrieves a list of maps with filtering and pagination."""
    items = MOCK_MAPS_DB
    if golf_course_id:
        items = [m for m in items if m['golfCourseId'] == golf_course_id]
    if type:
        items = [m for m in items if m['type'] == type]
    if search:
        items = [m for m in items if search.lower() in m['name'].lower()]

    total = len(items)
    start = (page - 1) * limit
    end = start + limit
    paginated_items = items[start:end]

    return {
        "items": paginated_items,
        "pagination": {"page": page, "limit": limit, "total": total, "totalPages": (total + limit - 1) // limit}
    }

async def get_map_by_id(map_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single map by its ID."""
    for m in MOCK_MAPS_DB:
        if m["id"] == map_id:
            return {**m, "metadata": {}, "waypoints": [], "statistics": {}, "files": {}}
    return None

async def update_map(map_id: str, map_update: schemas.MapUpdateRequest, user: schemas.User) -> Optional[Dict[str, Any]]:
    """Updates a map's information."""
    for i, m in enumerate(MOCK_MAPS_DB):
        if m["id"] == map_id:
            update_data = map_update.model_dump(exclude_unset=True)
            MOCK_MAPS_DB[i].update(update_data)
            MOCK_MAPS_DB[i]["updatedAt"] = datetime.now(timezone.utc)
            MOCK_MAPS_DB[i]["updatedBy"] = {"id": user.id, "name": user.name}
            return MOCK_MAPS_DB[i]
    return None

async def delete_map(map_id: str) -> Optional[Dict[str, Any]]:
    """Deletes a map from the mock DB."""
    for i, m in enumerate(MOCK_MAPS_DB):
        if m["id"] == map_id:
            return MOCK_MAPS_DB.pop(i)
    return None

async def upload_map_image(image: UploadFile) -> Dict[str, Any]:
    """Simulates uploading a map image."""
    # In a real app, you'd save this to S3, etc.
    # await image.read() to get content
    return {
        "url": f"https://mock-storage.com/maps/images/{uuid4()}-{image.filename}",
        "thumbnailUrl": f"https://mock-storage.com/maps/thumbnails/{uuid4()}-{image.filename}",
        "filename": image.filename,
        "size": image.size,
        "mimeType": image.content_type,
        "resolution": "4096x4096"
    }

async def upload_map_metadata(files: List[UploadFile]) -> Dict[str, Any]:
    """Simulates uploading map metadata files."""
    total_size = sum(file.size for file in files)
    file_list = [
        {"name": file.filename, "path": f"metadata/{file.filename}", "size": file.size} for file in files
    ]
    return {
        "folderPath": f"https://mock-storage.com/maps/metadata/{uuid4()}",
        "fileCount": len(files),
        "totalSize": total_size,
        "files": file_list
    }
