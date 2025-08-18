import pytest
from httpx import AsyncClient
import io

pytestmark = pytest.mark.asyncio

# State to be shared between tests
created_map_id: str = ""

async def test_create_map(async_client: AsyncClient, access_token: str, setup_golf_course: str):
    """Tests creating a new map."""
    global created_map_id
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "name": "Main Course Map",
        "golfCourseId": setup_golf_course,
        "type": "2D",
        "bounds": {
            "north": 40.7, "south": 40.5, "east": -74.0, "west": -74.2
        }
    }
    response = await async_client.post("/api/maps/", headers=headers, json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Main Course Map"
    assert "id" in data
    created_map_id = data["id"]

async def test_get_map_by_id(async_client: AsyncClient, access_token: str):
    """Tests retrieving the newly created map."""
    assert created_map_id, "Map must be created first"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.get(f"/api/maps/{created_map_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_map_id
    assert data["name"] == "Main Course Map"

async def test_upload_image(async_client: AsyncClient, access_token: str):
    """Tests uploading a map image."""
    headers = {"Authorization": f"Bearer {access_token}"}
    # Create a dummy file in memory
    dummy_file = io.BytesIO(b"dummy image data")
    dummy_file.name = "test_map.jpg"

    files = {"image": (dummy_file.name, dummy_file, "image/jpeg")}

    response = await async_client.post("/api/maps/upload-image", headers=headers, files=files)

    assert response.status_code == 200
    data = response.json()["data"]
    assert "url" in data
    assert data["filename"] == "test_map.jpg"

async def test_delete_map(async_client: AsyncClient, access_token: str):
    """Tests deleting the map."""
    assert created_map_id, "Map must be created first"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.delete(f"/api/maps/{created_map_id}", headers=headers)
    assert response.status_code == 200

async def test_verify_map_deletion(async_client: AsyncClient, access_token: str):
    """Verifies that the map is no longer accessible."""
    assert created_map_id, "Map must be created first"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.get(f"/api/maps/{created_map_id}", headers=headers)
    assert response.status_code == 404
