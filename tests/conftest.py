"""
Pytest configuration and shared fixtures for all tests.
Based on PRD requirements and test scenarios.
"""
import sys
from pathlib import Path
import os

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from uuid import uuid4

# Set test environment variables before imports
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/golfcart_test"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["MQTT_ENABLED"] = "false"  # Disable MQTT for tests
os.environ["DEBUG"] = "true"

from app.main import app
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.models.user import ManufacturerUser, GolfCourseUser
from app.models.golf_course import GolfCourse, Hole, Route, Geofence
from app.models.cart import CartModel, GolfCart, CartRegistration


# Test database URL (use separate test database)
TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/golfcart_test"

# Create test engine
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def setup_database():
    """Create test database tables."""
    # Create extensions
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop all tables after tests
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(setup_database) -> Generator[Session, None, None]:
    """Create a test database session."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """Create a test client with overridden database dependency."""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# User fixtures
@pytest.fixture
def test_manufacturer_user(db_session: Session) -> ManufacturerUser:
    """Create a test manufacturer user."""
    user = ManufacturerUser(
        email="admin@dygolfcart.com",
        name="Test Admin",
        phone="+1-234-567-8900",
        department="Engineering",
        password_hash=get_password_hash("Test123!@#"),
        is_active=True,
        is_superuser=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_golf_course_user(db_session: Session, test_golf_course) -> GolfCourseUser:
    """Create a test golf course user."""
    user = GolfCourseUser(
        golf_course_id=test_golf_course.id,
        email="operator@pinehills.com",
        name="Course Operator",
        phone="+1-234-567-8901",
        position="Operations Manager",
        password_hash=get_password_hash("Course123!"),
        is_active=True,
        is_admin=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def manufacturer_token(test_manufacturer_user) -> str:
    """Create a JWT token for manufacturer user."""
    return create_access_token(
        data={
            "user_id": str(test_manufacturer_user.id),
            "email": test_manufacturer_user.email,
            "user_type": "manufacturer",
            "is_superuser": test_manufacturer_user.is_superuser
        }
    )


@pytest.fixture
def golf_course_token(test_golf_course_user) -> str:
    """Create a JWT token for golf course user."""
    return create_access_token(
        data={
            "user_id": str(test_golf_course_user.id),
            "email": test_golf_course_user.email,
            "user_type": "golf_course",
            "golf_course_id": str(test_golf_course_user.golf_course_id),
            "is_admin": test_golf_course_user.is_admin
        }
    )


# Golf Course fixtures
@pytest.fixture
def test_golf_course(db_session: Session, test_manufacturer_user) -> GolfCourse:
    """Create a test golf course."""
    course = GolfCourse(
        name="Pine Hills Golf Club",
        code="PH001",
        address="123 Golf Course Road, City, State 12345",
        phone="+1-234-567-8900",
        email="info@pinehills.com",
        hole_count=18,
        status="ACTIVE",
        timezone="America/New_York",
        opening_time="06:00",
        closing_time="20:00",
        cart_speed_limit=20.0,
        auto_return_enabled=False,
        geofence_alerts_enabled=True,
        created_by=test_manufacturer_user.id
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)
    return course


@pytest.fixture
def another_golf_course(db_session: Session, test_manufacturer_user) -> GolfCourse:
    """Create another test golf course for transfer tests."""
    course = GolfCourse(
        name="Oak Valley Country Club",
        code="OV001",
        address="456 Country Club Drive, Another City, State 54321",
        phone="+1-234-567-8902",
        email="info@oakvalley.com",
        hole_count=18,
        status="ACTIVE",
        created_by=test_manufacturer_user.id
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)
    return course


@pytest.fixture
def test_golf_course_with_data(db_session: Session, test_golf_course) -> GolfCourse:
    """Create a golf course with holes, routes, and geofences."""
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Point, LineString, Polygon
    
    # Add holes
    for i in range(1, 4):
        hole = Hole(
            golf_course_id=test_golf_course.id,
            hole_number=i,
            par=4 if i % 2 == 0 else 5,
            distance_white=350 + (i * 30),
            tee_position=from_shape(Point(-122.42 + (i * 0.001), 37.77 + (i * 0.001)), srid=4326),
            green_position=from_shape(Point(-122.42 + (i * 0.002), 37.77 + (i * 0.002)), srid=4326)
        )
        db_session.add(hole)
    
    # Add routes
    route1 = Route(
        golf_course_id=test_golf_course.id,
        name="Hole 1 to 2",
        route_type="HOLE_TO_HOLE",
        path=from_shape(LineString([
            (-122.420, 37.770),
            (-122.421, 37.771),
            (-122.422, 37.772)
        ]), srid=4326),
        distance_meters=450,
        from_hole=1,
        to_hole=2,
        is_active=True,
        created_by=test_golf_course.created_by
    )
    db_session.add(route1)
    
    # Add geofences
    parking = Geofence(
        golf_course_id=test_golf_course.id,
        name="Parking Area",
        fence_type="PARKING",
        geometry=from_shape(Polygon([
            (-122.420, 37.770),
            (-122.420, 37.771),
            (-122.419, 37.771),
            (-122.419, 37.770),
            (-122.420, 37.770)
        ]), srid=4326),
        speed_limit=5.0,
        is_active=True
    )
    db_session.add(parking)
    
    db_session.commit()
    db_session.refresh(test_golf_course)
    return test_golf_course


# Cart fixtures
@pytest.fixture
def test_cart_model(db_session: Session) -> CartModel:
    """Create a test cart model."""
    model = CartModel(
        manufacturer="DY Golf Carts",
        model_name="DY-2024 Pro",
        model_code="DY2024PRO",
        year=2024,
        capacity=2,
        max_speed=20.0,
        range_km=50.0,
        charge_time_hours=6.0,
        features={
            "gps": True,
            "autonomous": True,
            "usb_charging": True,
            "weather_shield": True
        }
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def test_cart(db_session: Session, test_cart_model) -> GolfCart:
    """Create a test golf cart."""
    cart = GolfCart(
        serial_number="DY-2024-TEST-001",
        cart_model_id=test_cart_model.id,
        cart_number="001",
        status="IDLE",
        mode="MANUAL",
        firmware_version="2.1.0",
        mqtt_client_id="cart_DY-2024-TEST-001",
        total_distance_km=0.0,
        total_runtime_hours=0.0
    )
    db_session.add(cart)
    db_session.commit()
    db_session.refresh(cart)
    return cart


@pytest.fixture
def test_cart_assigned(db_session: Session, test_cart, test_golf_course,
                      test_manufacturer_user) -> GolfCart:
    """Create a test cart that is assigned to a golf course."""
    # Assign cart to golf course
    test_cart.golf_course_id = test_golf_course.id
    test_cart.cart_number = "42"
    
    # Create registration record
    registration = CartRegistration(
        cart_id=test_cart.id,
        golf_course_id=test_golf_course.id,
        registered_by=test_manufacturer_user.id,
        registration_type="NEW",
        cart_number="42",
        start_date=datetime.utcnow()
    )
    db_session.add(registration)
    
    db_session.commit()
    db_session.refresh(test_cart)
    return test_cart


@pytest.fixture
def test_geofence_hazard(db_session: Session, test_golf_course) -> Geofence:
    """Create a test hazard geofence."""
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Polygon
    
    geofence = Geofence(
        golf_course_id=test_golf_course.id,
        name="Water Hazard Hole 2",
        fence_type="HAZARD",
        geometry=from_shape(Polygon([
            (-122.4172, 37.7753),
            (-122.4172, 37.7754),
            (-122.4170, 37.7754),
            (-122.4170, 37.7753),
            (-122.4172, 37.7753)
        ]), srid=4326),
        alert_on_entry=True,
        auto_stop=True,
        is_active=True,
        severity="CRITICAL"
    )
    db_session.add(geofence)
    db_session.commit()
    db_session.refresh(geofence)
    return geofence