"""
Authentication tests based on PRD requirements.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from jose import jwt

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models.user import ManufacturerUser, GolfCourseUser


class TestManufacturerAuthentication:
    """Test manufacturer authentication flows."""
    
    def test_successful_manufacturer_login(self, client: TestClient, db_session):
        """Test successful manufacturer login returns JWT tokens."""
        # Create test manufacturer user
        user = ManufacturerUser(
            email="admin@dygolfcart.com",
            name="Test Admin",
            password_hash=get_password_hash("Test123!@#"),
            is_active=True,
            is_superuser=True
        )
        db_session.add(user)
        db_session.commit()
        
        # Attempt login
        response = client.post(
            "/api/v1/auth/manufacturer/login",
            json={
                "email": "admin@dygolfcart.com",
                "password": "Test123!@#"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        
        # Verify user info
        assert data["user"]["email"] == "admin@dygolfcart.com"
        assert data["user"]["user_type"] == "manufacturer"
        assert data["user"]["is_active"] is True
        
        # Verify JWT token is valid
        payload = jwt.decode(
            data["access_token"],
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        assert payload["email"] == "admin@dygolfcart.com"
        assert payload["user_type"] == "manufacturer"
        assert payload["is_superuser"] is True
    
    def test_manufacturer_login_wrong_password(self, client: TestClient, db_session):
        """Test manufacturer login with wrong password returns 401."""
        # Create test user
        user = ManufacturerUser(
            email="admin@dygolfcart.com",
            name="Test Admin",
            password_hash=get_password_hash("Test123!@#"),
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        
        # Attempt login with wrong password
        response = client.post(
            "/api/v1/auth/manufacturer/login",
            json={
                "email": "admin@dygolfcart.com",
                "password": "WrongPassword"
            }
        )
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_manufacturer_login_inactive_user(self, client: TestClient, db_session):
        """Test inactive manufacturer cannot login."""
        # Create inactive user
        user = ManufacturerUser(
            email="inactive@dygolfcart.com",
            name="Inactive User",
            password_hash=get_password_hash("Test123!@#"),
            is_active=False
        )
        db_session.add(user)
        db_session.commit()
        
        response = client.post(
            "/api/v1/auth/manufacturer/login",
            json={
                "email": "inactive@dygolfcart.com",
                "password": "Test123!@#"
            }
        )
        
        assert response.status_code == 401


class TestGolfCourseAuthentication:
    """Test golf course user authentication flows."""
    
    def test_successful_golf_course_login(self, client: TestClient, db_session, test_golf_course):
        """Test successful golf course user login."""
        # Create golf course user
        user = GolfCourseUser(
            golf_course_id=test_golf_course.id,
            email="operator@pinehills.com",
            name="Course Operator",
            password_hash=get_password_hash("Course123!"),
            is_active=True,
            is_admin=True
        )
        db_session.add(user)
        db_session.commit()
        
        # Attempt login
        response = client.post(
            "/api/v1/auth/golf-course/login",
            json={
                "email": "operator@pinehills.com",
                "password": "Course123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response
        assert "access_token" in data
        assert data["user"]["user_type"] == "golf_course"
        assert data["user"]["golf_course_id"] == str(test_golf_course.id)
        
        # Verify JWT contains golf_course_id
        payload = jwt.decode(
            data["access_token"],
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        assert payload["golf_course_id"] == str(test_golf_course.id)
        assert payload["is_admin"] is True
    
    def test_golf_course_user_access_control(self, client: TestClient, db_session, 
                                            test_golf_course, another_golf_course):
        """Test golf course users can only access their own course data."""
        # Create user for first course
        user = GolfCourseUser(
            golf_course_id=test_golf_course.id,
            email="user@course1.com",
            name="Course 1 User",
            password_hash=get_password_hash("Password1!"),
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        
        # Login
        login_response = client.post(
            "/api/v1/auth/golf-course/login",
            json={
                "email": "user@course1.com",
                "password": "Password1!"
            }
        )
        token = login_response.json()["access_token"]
        
        # Try to access own course - should succeed
        response = client.get(
            f"/api/v1/golf-courses/{test_golf_course.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Try to access another course - should fail
        response = client.get(
            f"/api/v1/golf-courses/{another_golf_course.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]


class TestTokenRefresh:
    """Test token refresh functionality."""
    
    def test_successful_token_refresh(self, client: TestClient, db_session):
        """Test refreshing access token with valid refresh token."""
        # Create user and login
        user = ManufacturerUser(
            email="admin@dygolfcart.com",
            name="Test Admin",
            password_hash=get_password_hash("Test123!@#"),
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        
        # Login to get tokens
        login_response = client.post(
            "/api/v1/auth/manufacturer/login",
            json={
                "email": "admin@dygolfcart.com",
                "password": "Test123!@#"
            }
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        
        # Verify new access token works
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {data['access_token']}"}
        )
        assert me_response.status_code == 200
    
    def test_expired_refresh_token(self, client: TestClient):
        """Test refresh with expired token fails."""
        # Create expired refresh token
        expired_token = create_access_token(
            data={
                "user_id": "test-id",
                "user_type": "manufacturer",
                "type": "refresh"
            },
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_token}
        )
        
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]


class TestAuthorizationRoles:
    """Test role-based access control."""
    
    def test_manufacturer_can_create_golf_course(self, client: TestClient, 
                                                manufacturer_token):
        """Test manufacturer can create golf courses."""
        response = client.post(
            "/api/v1/golf-courses",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "name": "New Golf Course",
                "code": "NGC001",
                "hole_count": 18
            }
        )
        
        assert response.status_code in [200, 201]
    
    def test_golf_course_user_cannot_create_golf_course(self, client: TestClient,
                                                       golf_course_token):
        """Test golf course user cannot create new golf courses."""
        response = client.post(
            "/api/v1/golf-courses",
            headers={"Authorization": f"Bearer {golf_course_token}"},
            json={
                "name": "New Golf Course",
                "code": "NGC002",
                "hole_count": 18
            }
        )
        
        assert response.status_code == 403
        assert "Manufacturer access required" in response.json()["detail"]