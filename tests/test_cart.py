import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# State to be shared between tests
created_cart_id: str = ""

async def test_create_cart(async_client: AsyncClient, access_token: str, setup_golf_course: str):
    """Tests creating a new cart associated with the setup golf course."""
    global created_cart_id
    golf_course_id = setup_golf_course

    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "cartNumber": "C-101",
        "modelName": "Express S4",
        "golfCourseId": golf_course_id
    }
    response = await async_client.post("/api/carts/", headers=headers, json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["cartNumber"] == "C-101"
    assert data["golfCourseId"] == golf_course_id
    created_cart_id = data["id"]


async def test_get_cart_by_id(async_client: AsyncClient, access_token: str):
    """Tests retrieving the newly created cart."""
    assert created_cart_id, "Cart must be created first"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.get(f"/api/carts/{created_cart_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_cart_id
    assert data["cartNumber"] == "C-101"

async def test_list_carts(async_client: AsyncClient, access_token: str, setup_golf_course: str):
    """Tests listing carts and filtering by golf course."""
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"golfCourseId": setup_golf_course}
    response = await async_client.get("/api/carts/", headers=headers, params=params)

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == created_cart_id

async def test_update_cart_status(async_client: AsyncClient, access_token: str):
    """Tests updating the cart's status."""
    assert created_cart_id, "Cart must be created first"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"status": "MAINTENANCE"}
    response = await async_client.patch(f"/api/carts/{created_cart_id}/status", headers=headers, json=payload)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "MAINTENANCE"

async def test_get_cart_telemetry(async_client: AsyncClient, access_token: str):
    """Tests the battery and location endpoints."""
    assert created_cart_id, "Cart must be created first"
    headers = {"Authorization": f"Bearer {access_token}"}

    # Test battery
    response_batt = await async_client.get(f"/api/carts/{created_cart_id}/battery", headers=headers)
    assert response_batt.status_code == 200
    assert "level" in response_batt.json()["data"]

    # Test location
    response_loc = await async_client.get(f"/api/carts/{created_cart_id}/location", headers=headers)
    assert response_loc.status_code == 200
    assert "latitude" in response_loc.json()["data"]

async def test_delete_cart(async_client: AsyncClient, access_token: str):
    """Tests deleting the cart."""
    assert created_cart_id, "Cart must be created first"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.delete(f"/api/carts/{created_cart_id}", headers=headers)
    assert response.status_code == 200

async def test_verify_cart_deletion(async_client: AsyncClient, access_token: str):
    """Verifies that the cart is no longer accessible."""
    assert created_cart_id, "Cart must be created first"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.get(f"/api/carts/{created_cart_id}", headers=headers)
    assert response.status_code == 404
