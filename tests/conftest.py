import pytest
import asyncio
from typing import AsyncGenerator, Generator

import httpx
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.security import create_access_token

@pytest.fixture(scope="session")
def event_loop(request) -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    A fixture that creates an httpx.AsyncClient for making API requests
    to the test server.
    """
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture(scope="module")
def access_token() -> str:
    """
    Fixture to create an access token for the mock admin user.
    This bypasses the /login endpoint for faster, more isolated tests
    of protected endpoints.
    """
    return create_access_token(data={"sub": "admin@example.com", "role": "ADMIN"})

from app.services.golf_course_service import MOCK_GOLF_COURSES_DB

@pytest.fixture(scope="module", autouse=True)
async def setup_golf_course(async_client: AsyncClient) -> str:
    """
    Fixture to create a single golf course for each test module,
    and yield its ID. This runs automatically for each test module.
    It's robust against being run multiple times in the same session.
    """
    # Check if already created in this test session
    for course in MOCK_GOLF_COURSES_DB:
        if course['name'] == "Global Test GC":
            return course['id']

    # If not found, create it
    token = create_access_token(data={"sub": "admin@example.com", "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": "Global Test GC",
        "address": "1 Global Test Parkway",
        "location": {"latitude": 0.0, "longitude": 0.0}
    }
    response = await async_client.post("/api/golf-courses/", headers=headers, json=payload)
    assert response.status_code == 201, "Failed to create prerequisite golf course for tests"
    golf_course_id = response.json()["id"]
    return golf_course_id