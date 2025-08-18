"""Global pytest fixtures and configuration."""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.fleet.value_objects import (
    CartNumber,
    Position,
    Battery,
    Velocity
)
from app.domain.shared.cart_status import CartStatus


@pytest.fixture
def sample_uuid():
    """Provide a sample UUID for testing."""
    return uuid4()


@pytest.fixture
def sample_cart_number():
    """Provide a sample cart number."""
    return CartNumber("CART001")


@pytest.fixture
def sample_position():
    """Provide a sample position."""
    return Position(37.7749, -122.4194)  # San Francisco coordinates


@pytest.fixture
def sample_battery():
    """Provide a sample battery."""
    return Battery(75.0)


@pytest.fixture
def sample_velocity():
    """Provide a sample velocity."""
    return Velocity(15.0)


@pytest.fixture
def sample_cart_status():
    """Provide a sample cart status."""
    return CartStatus.IDLE


@pytest.fixture
def fixed_datetime():
    """Provide a fixed datetime for testing."""
    return datetime(2024, 1, 1, 12, 0, 0)


import os

def pytest_configure(config):
    """Set environment variables before test collection."""
    os.environ["KEYCLOAK_SERVER_URL"] = "http://localhost:8080"
    os.environ["KEYCLOAK_REALM_NAME"] = "test-realm"
    os.environ["KEYCLOAK_CLIENT_ID"] = "test-client"
    os.environ["KEYCLOAK_CLIENT_SECRET"] = "test-secret"
    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost/test_db"