import pytest
from httpx import AsyncClient

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

async def test_successful_login(async_client: AsyncClient):
    """
    Tests successful login with correct credentials for the mock admin user.
    """
    response = await async_client.post(
        "/api/auth/login",
        data={"username": "admin@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["user"]["email"] == "admin@example.com"

async def test_login_wrong_password(async_client: AsyncClient):
    """
    Tests login with a wrong password.
    """
    response = await async_client.post(
        "/api/auth/login",
        data={"username": "admin@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "이메일 또는 비밀번호가 올바르지 않습니다" in response.json()["detail"]

async def test_login_nonexistent_user(async_client: AsyncClient):
    """
    Tests login with a user that does not exist.
    """
    response = await async_client.post(
        "/api/auth/login",
        data={"username": "nouser@example.com", "password": "password123"}
    )
    assert response.status_code == 401

async def test_get_users_unauthenticated(async_client: AsyncClient):
    """
    Tests that accessing a protected endpoint (/api/users/) without a token fails.
    """
    response = await async_client.get("/api/users/")
    assert response.status_code == 401
    assert "Not authenticated" in response.json().get("detail")

async def test_get_users_authenticated(async_client: AsyncClient, access_token: str):
    """
    Tests that accessing a protected endpoint (/api/users/) with a valid token succeeds.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.get("/api/users/", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "pagination" in data
    # The mock user DB has only one user
    assert len(data["items"]) == 1
    assert data["items"][0]["email"] == "admin@example.com"
    assert "hashed_password" not in data["items"][0]
