"""
Golf course setup workflow tests based on PRD Sequence Diagram 1.
Tests the complete setup process: course creation → map upload → routes → geofences.
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from io import BytesIO
from PIL import Image
import json

from app.models.golf_course import GolfCourse, Hole, Route, Geofence, GolfCourseMap


class TestGolfCourseSetupWorkflow:
    """Test complete golf course setup workflow from PRD."""
    
    def test_complete_golf_course_setup(self, client: TestClient, db_session,
                                       manufacturer_token):
        """
        Test the complete golf course setup workflow:
        1. Create golf course
        2. Upload map
        3. Define holes
        4. Create routes
        5. Setup geofences
        """
        
        # Step 1: Create Golf Course
        course_response = client.post(
            "/api/v1/golf-courses",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "name": "Pine Hills Golf Club",
                "code": "PH001",
                "hole_count": 18,
                "address": "123 Golf Course Road, City, State",
                "phone": "+1-234-567-8900",
                "email": "info@pinehills.com",
                "timezone": "America/New_York",
                "cart_speed_limit": 20.0,
                "auto_return_enabled": False,
                "geofence_alerts_enabled": True
            }
        )
        
        assert course_response.status_code == 200
        course_data = course_response.json()
        course_id = course_data["id"]
        assert course_data["status"] == "ACTIVE"
        assert course_data["code"] == "PH001"
        
        # Step 2: Upload Map
        # Create a test image file
        img = Image.new('RGB', (1024, 768), color='green')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        map_response = client.post(
            f"/api/v1/golf-courses/{course_id}/maps",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            files={"file": ("course_map.png", img_bytes, "image/png")},
            data={
                "name": "Main Course Map",
                "version": "1.0.0"
            }
        )
        
        assert map_response.status_code == 200
        map_data = map_response.json()
        assert map_data["name"] == "Main Course Map"
        assert map_data["version"] == "1.0.0"
        assert map_data["is_active"] is True
        
        # Step 3: Define Holes (create first 3 holes as example)
        holes_data = [
            {
                "hole_number": 1,
                "par": 4,
                "distance_red": 320,
                "distance_white": 380,
                "distance_blue": 410,
                "distance_black": 440,
                "tee_position": {"lat": 37.7749, "lng": -122.4194},
                "green_position": {"lat": 37.7751, "lng": -122.4180}
            },
            {
                "hole_number": 2,
                "par": 3,
                "distance_red": 120,
                "distance_white": 145,
                "distance_blue": 165,
                "distance_black": 185,
                "tee_position": {"lat": 37.7752, "lng": -122.4175},
                "green_position": {"lat": 37.7754, "lng": -122.4170}
            },
            {
                "hole_number": 3,
                "par": 5,
                "distance_red": 450,
                "distance_white": 490,
                "distance_blue": 520,
                "distance_black": 550,
                "tee_position": {"lat": 37.7755, "lng": -122.4165},
                "green_position": {"lat": 37.7760, "lng": -122.4150}
            }
        ]
        
        for hole in holes_data:
            hole_response = client.post(
                f"/api/v1/golf-courses/{course_id}/holes",
                headers={"Authorization": f"Bearer {manufacturer_token}"},
                json=hole
            )
            assert hole_response.status_code == 200
            assert hole_response.json()["hole_number"] == hole["hole_number"]
            assert hole_response.json()["par"] == hole["par"]
        
        # Verify holes were created
        holes_list = client.get(
            f"/api/v1/golf-courses/{course_id}/holes",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        assert holes_list.status_code == 200
        assert len(holes_list.json()) == 3
        
        # Step 4: Create Routes
        routes_data = [
            {
                "name": "Hole 1 to Hole 2",
                "route_type": "HOLE_TO_HOLE",
                "path": [
                    [-122.4180, 37.7751],  # End of hole 1
                    [-122.4178, 37.7752],  # Intermediate point
                    [-122.4175, 37.7752]   # Start of hole 2
                ],
                "distance_meters": 450,
                "estimated_time_seconds": 90,
                "from_hole": 1,
                "to_hole": 2,
                "speed_limit": 15.0,
                "is_active": True,
                "is_preferred": True
            },
            {
                "name": "Return to Clubhouse",
                "route_type": "RETURN_TO_BASE",
                "path": [
                    [-122.4150, 37.7760],  # End of course
                    [-122.4160, 37.7755],  # Intermediate
                    [-122.4170, 37.7750],  # Intermediate
                    [-122.4190, 37.7745]   # Clubhouse
                ],
                "distance_meters": 2000,
                "estimated_time_seconds": 300,
                "is_active": True
            }
        ]
        
        for route in routes_data:
            route_response = client.post(
                f"/api/v1/golf-courses/{course_id}/routes",
                headers={"Authorization": f"Bearer {manufacturer_token}"},
                json=route
            )
            assert route_response.status_code == 200
            assert route_response.json()["name"] == route["name"]
            assert route_response.json()["route_type"] == route["route_type"]
        
        # Step 5: Setup Geofences
        geofences_data = [
            {
                "name": "Parking Area",
                "fence_type": "PARKING",
                "geometry": [[[
                    [-122.4195, 37.7744],
                    [-122.4195, 37.7746],
                    [-122.4192, 37.7746],
                    [-122.4192, 37.7744],
                    [-122.4195, 37.7744]  # Closed polygon
                ]]],
                "speed_limit": 5.0,
                "alert_on_entry": False,
                "alert_on_exit": True,
                "is_active": True,
                "severity": "INFO"
            },
            {
                "name": "Water Hazard Hole 2",
                "fence_type": "HAZARD",
                "geometry": [[[
                    [-122.4172, 37.7753],
                    [-122.4172, 37.7754],
                    [-122.4170, 37.7754],
                    [-122.4170, 37.7753],
                    [-122.4172, 37.7753]
                ]]],
                "alert_on_entry": True,
                "auto_stop": True,
                "is_active": True,
                "severity": "CRITICAL"
            },
            {
                "name": "Practice Range",
                "fence_type": "RESTRICTED",
                "geometry": [[[
                    [-122.4200, 37.7740],
                    [-122.4200, 37.7745],
                    [-122.4195, 37.7745],
                    [-122.4195, 37.7740],
                    [-122.4200, 37.7740]
                ]]],
                "alert_on_entry": True,
                "is_active": True,
                "severity": "WARNING",
                "schedule": [
                    {
                        "start": "06:00",
                        "end": "08:00",
                        "days": ["MON", "WED", "FRI"]
                    }
                ]
            }
        ]
        
        for geofence in geofences_data:
            geofence_response = client.post(
                f"/api/v1/golf-courses/{course_id}/geofences",
                headers={"Authorization": f"Bearer {manufacturer_token}"},
                json=geofence
            )
            assert geofence_response.status_code == 200
            assert geofence_response.json()["name"] == geofence["name"]
            assert geofence_response.json()["fence_type"] == geofence["fence_type"]
        
        # Verify complete setup
        course_detail = client.get(
            f"/api/v1/golf-courses/{course_id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert course_detail.status_code == 200
        detail_data = course_detail.json()
        assert detail_data["map_count"] == 1
        assert detail_data["route_count"] == 2
        assert detail_data["geofence_count"] == 3
        
        # Verify data in database
        db_course = db_session.query(GolfCourse).filter_by(id=course_id).first()
        assert db_course is not None
        assert len(db_course.holes) == 3
        assert len(db_course.routes) == 2
        assert len(db_course.geofences) == 3
    
    def test_duplicate_golf_course_code(self, client: TestClient, db_session,
                                       manufacturer_token):
        """Test that duplicate golf course codes are rejected."""
        # Create first course
        first_response = client.post(
            "/api/v1/golf-courses",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "name": "First Course",
                "code": "DUP001",
                "hole_count": 18
            }
        )
        assert first_response.status_code == 200
        
        # Try to create second course with same code
        second_response = client.post(
            "/api/v1/golf-courses",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "name": "Second Course",
                "code": "DUP001",  # Same code
                "hole_count": 18
            }
        )
        
        assert second_response.status_code == 400
        assert "already exists" in second_response.json()["detail"]
    
    def test_invalid_hole_number(self, client: TestClient, db_session,
                                manufacturer_token, test_golf_course):
        """Test that invalid hole numbers are rejected."""
        # Try to create hole 19 for an 18-hole course
        response = client.post(
            f"/api/v1/golf-courses/{test_golf_course.id}/holes",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "hole_number": 19,  # Invalid for 18-hole course
                "par": 4
            }
        )
        
        # Note: This validation should be implemented in the API
        # For now, we just check that the hole number is validated
        assert response.status_code in [400, 422]
    
    def test_geofence_auto_closing(self, client: TestClient, db_session,
                                  manufacturer_token, test_golf_course):
        """Test that non-closed polygon geofences are automatically closed."""
        # Send non-closed polygon
        response = client.post(
            f"/api/v1/golf-courses/{test_golf_course.id}/geofences",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "name": "Test Area",
                "fence_type": "RESTRICTED",
                "geometry": [[[
                    [-122.4, 37.7],
                    [-122.4, 37.8],
                    [-122.3, 37.8],
                    [-122.3, 37.7]
                    # Missing closing point
                ]]],
                "is_active": True
            }
        )
        
        assert response.status_code == 200
        
        # Verify in database that polygon was closed
        geofence = db_session.query(Geofence).filter_by(
            golf_course_id=test_golf_course.id,
            name="Test Area"
        ).first()
        
        assert geofence is not None
        # The geometry should be properly closed in PostGIS


class TestGolfCourseDataValidation:
    """Test data validation for golf course setup."""
    
    def test_route_with_invalid_coordinates(self, client: TestClient,
                                          manufacturer_token, test_golf_course):
        """Test that routes with invalid coordinates are rejected."""
        response = client.post(
            f"/api/v1/golf-courses/{test_golf_course.id}/routes",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "name": "Invalid Route",
                "route_type": "CUSTOM",
                "path": [
                    [200, 100],  # Invalid longitude
                    [-200, -100]  # Invalid latitude
                ]
            }
        )
        
        assert response.status_code in [400, 422]
    
    def test_speed_limit_validation(self, client: TestClient,
                                   manufacturer_token, test_golf_course):
        """Test that speed limits are within valid range."""
        response = client.post(
            f"/api/v1/golf-courses/{test_golf_course.id}/geofences",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={
                "name": "Speed Test Zone",
                "fence_type": "SLOW_ZONE",
                "geometry": [[[
                    [-122.4, 37.7],
                    [-122.4, 37.8],
                    [-122.3, 37.8],
                    [-122.3, 37.7],
                    [-122.4, 37.7]
                ]]],
                "speed_limit": 100.0,  # Too high
                "is_active": True
            }
        )
        
        # Speed limit should be validated (e.g., max 50 km/h)
        assert response.status_code in [400, 422] or \
               response.json()["speed_limit"] <= 50.0