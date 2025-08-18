import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# Store the ID of the created golf course to use across tests
golf_course_id: str = ""

@pytest.fixture(scope="module")
def golf_course_payload():
    return {
        "name": "Test National GC",
        "address": "123 Golf Rd, Fairway, CA 12345",
        "location": {"latitude": 34.0522, "longitude": -118.2437},
        "description": "A beautiful test course.",
        "operatingHours": {"weekday": "06:00-18:00"}
    }

async def test_create_golf_course(async_client: AsyncClient, access_token: str, golf_course_payload: dict):
    global golf_course_id
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.post("/api/golf-courses/", headers=headers, json=golf_course_payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == golf_course_payload["name"]
    assert data["address"] == golf_course_payload["address"]
    assert "id" in data
    golf_course_id = data["id"] # Save for subsequent tests

async def test_create_duplicate_golf_course(async_client: AsyncClient, access_token: str, golf_course_payload: dict):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.post("/api/golf-courses/", headers=headers, json=golf_course_payload)
    assert response.status_code == 409 # Conflict

async def test_get_golf_course_by_id(async_client: AsyncClient, access_token: str, golf_course_payload: dict):
    assert golf_course_id, "golf_course_id must be set by test_create_golf_course"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.get(f"/api/golf-courses/{golf_course_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == golf_course_id
    assert data["name"] == golf_course_payload["name"]

async def test_get_golf_courses_list(async_client: AsyncClient, access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.get("/api/golf-courses/", headers=headers, params={"search": "Test National"})

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    assert data["items"][0]["id"] == golf_course_id

async def test_update_golf_course(async_client: AsyncClient, access_token: str):
    assert golf_course_id, "golf_course_id must be set by test_create_golf_course"
    headers = {"Authorization": f"Bearer {access_token}"}
    update_payload = {"description": "An updated description for the test course."}
    response = await async_client.put(f"/api/golf-courses/{golf_course_id}", headers=headers, json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["description"] == update_payload["description"]

async def test_delete_golf_course(async_client: AsyncClient, access_token: str):
    assert golf_course_id, "golf_course_id must be set by test_create_golf_course"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.delete(f"/api/golf-courses/{golf_course_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "골프장이 삭제되었습니다."

async def test_get_deleted_golf_course(async_client: AsyncClient, access_token: str):
    assert golf_course_id, "golf_course_id must be set by test_create_golf_course"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.get(f"/api/golf-courses/{golf_course_id}", headers=headers)

    assert response.status_code == 404
