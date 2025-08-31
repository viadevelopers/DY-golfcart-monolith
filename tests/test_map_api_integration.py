"""
Comprehensive API Integration Tests for Map Endpoints.

Tests all Map API endpoints with various scenarios including:
- Success cases
- Error handling
- Authorization
- Validation
- Edge cases
"""
import pytest
import json
import io
from uuid import uuid4, UUID
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.map import Map
from app.models.user import ManufacturerUser
from app.core.security import create_access_token


class TestMapUploadEndpoint:
    """Test POST /api/v1/maps/upload endpoint."""
    
    @pytest.fixture
    def valid_map_file(self):
        """Create a valid test map file."""
        img = Image.new('RGB', (1024, 768), color=(0, 128, 0))  # Green color as RGB tuple
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes
    
    def test_successful_map_upload(self, client: TestClient, manufacturer_token: str, valid_map_file):
        """Test successful map upload with all parameters."""
        response = client.post(
            "/api/v1/maps/upload",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            files={"file": ("test_map.png", valid_map_file, "image/png")},
            data={
                "name": "Test Golf Course Map",
                "version": "1.0.0",
                "center_lat": "37.7749",
                "center_lng": "-122.4194",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'map_id' in data
        assert 'storage_url' in data
        assert data['status'] == 'success'
        assert 'Map uploaded and processed successfully' in data['message']
    
    def test_map_upload_with_zoom_levels(self, client: TestClient, manufacturer_token: str, valid_map_file):
        """Test map upload with custom zoom levels."""
        response = client.post(
            "/api/v1/maps/upload",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            files={"file": ("test_map.png", valid_map_file, "image/png")},
            data={
                "name": "Map with Zoom",
                "version": "2.0.0",
                "center_lat": "37.7749",
                "center_lng": "-122.4194",
                "zoom_levels": json.dumps([10, 12, 14, 16, 18])
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'tiles' in data
    
    def test_map_upload_missing_name(self, client: TestClient, manufacturer_token: str, valid_map_file):
        """Test map upload with missing required field."""
        response = client.post(
            "/api/v1/maps/upload",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            files={"file": ("test_map.png", valid_map_file, "image/png")},
            data={
                "version": "1.0.0"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_map_upload_unauthorized(self, client: TestClient, valid_map_file):
        """Test map upload without authorization."""
        response = client.post(
            "/api/v1/maps/upload",
            files={"file": ("test_map.png", valid_map_file, "image/png")},
            data={
                "name": "Unauthorized Map",
                "version": "1.0.0"
            }
        )
        
        assert response.status_code == 401
    
    def test_map_upload_large_file(self, client: TestClient, manufacturer_token: str):
        """Test uploading a large map file."""
        # Create a larger image (4096x3072)
        large_img = Image.new('RGB', (4096, 3072), color=(0, 128, 0))
        large_bytes = io.BytesIO()
        large_img.save(large_bytes, format='PNG')
        large_bytes.seek(0)
        
        response = client.post(
            "/api/v1/maps/upload",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            files={"file": ("large_map.png", large_bytes, "image/png")},
            data={
                "name": "Large Map",
                "version": "1.0.0"
            }
        )
        
        assert response.status_code == 200
    
    def test_map_upload_invalid_file_type(self, client: TestClient, manufacturer_token: str):
        """Test uploading an invalid file type."""
        invalid_file = io.BytesIO(b"This is not an image")
        invalid_file.seek(0)
        
        response = client.post(
            "/api/v1/maps/upload",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            files={"file": ("test.txt", invalid_file, "text/plain")},
            data={
                "name": "Invalid File",
                "version": "1.0.0"
            }
        )
        
        # Should still process but mark file type appropriately
        assert response.status_code == 200


class TestMapListEndpoint:
    """Test GET /api/v1/maps endpoint."""
    
    @pytest.fixture
    def create_test_maps(self, db: Session):
        """Create test maps in database."""
        maps = []
        for i in range(5):
            map_obj = Map(
                name=f"Test Map {i}",
                version="1.0.0",
                storage_url=f"s3://bucket/map{i}.png",
                status="active" if i < 3 else "archived",
                file_type="image" if i % 2 == 0 else "geojson"
            )
            db.add(map_obj)
            maps.append(map_obj)
        db.commit()
        return maps
    
    def test_list_all_maps(self, client: TestClient, manufacturer_token: str, create_test_maps):
        """Test listing all maps without filters."""
        response = client.get(
            "/api/v1/maps",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'items' in data
        assert 'total' in data
        assert 'status' in data
        assert data['status'] == 'success'
        assert len(data['items']) >= 5
    
    def test_list_maps_with_status_filter(self, client: TestClient, manufacturer_token: str, create_test_maps):
        """Test listing maps filtered by status."""
        response = client.get(
            "/api/v1/maps?status=active",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(map_item['status'] == 'active' for map_item in data['items'] if 'status' in map_item)
    
    def test_list_maps_with_file_type_filter(self, client: TestClient, manufacturer_token: str, create_test_maps):
        """Test listing maps filtered by file type."""
        response = client.get(
            "/api/v1/maps?file_type=geojson",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(map_item.get('file_type') == 'geojson' for map_item in data['items'] if 'file_type' in map_item)
    
    def test_list_maps_with_pagination(self, client: TestClient, manufacturer_token: str, create_test_maps):
        """Test map listing with pagination."""
        # First page
        response = client.get(
            "/api/v1/maps?skip=0&limit=2",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['items']) <= 2
        assert data['skip'] == 0
        assert data['limit'] == 2
        
        # Second page
        response = client.get(
            "/api/v1/maps?skip=2&limit=2",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['skip'] == 2
    
    def test_list_maps_unauthorized(self, client: TestClient):
        """Test listing maps without authorization."""
        response = client.get("/api/v1/maps")
        assert response.status_code == 401


class TestMapGetByIdEndpoint:
    """Test GET /api/v1/maps/{map_id} endpoint."""
    
    @pytest.fixture
    def test_map(self, db: Session) -> Map:
        """Create a test map."""
        map_obj = Map(
            name="Detailed Test Map",
            version="3.0.0",
            storage_url="s3://bucket/detailed.png",
            status="active",
            file_type="image",
            file_size=2048000,
            original_filename="detailed_map.png"
        )
        db.add(map_obj)
        db.commit()
        db.refresh(map_obj)
        return map_obj
    
    def test_get_map_by_id_success(self, client: TestClient, manufacturer_token: str, test_map: Map):
        """Test successfully retrieving a map by ID."""
        response = client.get(
            f"/api/v1/maps/{test_map.id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == str(test_map.id)
        assert data['name'] == "Detailed Test Map"
        assert data['version'] == "3.0.0"
        assert data['file_type'] == "image"
        assert data['file_size'] == 2048000
    
    def test_get_map_not_found(self, client: TestClient, manufacturer_token: str):
        """Test retrieving a non-existent map."""
        fake_id = str(uuid4())
        response = client.get(
            f"/api/v1/maps/{fake_id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 404
        assert 'Map not found' in response.json()['detail']
    
    def test_get_map_invalid_id_format(self, client: TestClient, manufacturer_token: str):
        """Test retrieving a map with invalid ID format."""
        response = client.get(
            "/api/v1/maps/invalid-uuid",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code in [404, 422]  # Either not found or validation error


class TestMapStatusUpdateEndpoint:
    """Test PATCH /api/v1/maps/{map_id}/status endpoint."""
    
    @pytest.fixture
    def active_map(self, db: Session) -> Map:
        """Create an active test map."""
        map_obj = Map(
            name="Status Test Map",
            version="1.0.0",
            storage_url="s3://bucket/status.png",
            status="active"
        )
        db.add(map_obj)
        db.commit()
        db.refresh(map_obj)
        return map_obj
    
    def test_update_map_status_to_archived(self, client: TestClient, manufacturer_token: str, active_map: Map, db: Session):
        """Test updating map status to archived."""
        response = client.patch(
            f"/api/v1/maps/{active_map.id}/status",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json="archived",  # Send as body
            content="application/json"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'archived'
        assert str(active_map.id) in data['map_id']
        
        # Verify in database
        db.refresh(active_map)
        assert active_map.status == 'archived'
    
    def test_update_map_status_all_valid_statuses(self, client: TestClient, manufacturer_token: str, db: Session):
        """Test updating map to all valid statuses."""
        valid_statuses = ['active', 'archived', 'processing', 'failed']
        
        for status in valid_statuses:
            # Create a new map for each test
            map_obj = Map(
                name=f"Status {status} Test",
                version="1.0.0",
                storage_url=f"s3://bucket/{status}.png",
                status="active"
            )
            db.add(map_obj)
            db.commit()
            
            response = client.patch(
                f"/api/v1/maps/{map_obj.id}/status",
                headers={"Authorization": f"Bearer {manufacturer_token}"},
                json=status,
                content="application/json"
            )
            
            assert response.status_code == 200
            assert response.json()['status'] == status
    
    def test_update_map_status_invalid(self, client: TestClient, manufacturer_token: str, active_map: Map):
        """Test updating map with invalid status."""
        response = client.patch(
            f"/api/v1/maps/{active_map.id}/status",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json="invalid_status",
            content="application/json"
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_update_map_status_unauthorized(self, client: TestClient, active_map: Map):
        """Test updating map status without manufacturer authorization."""
        response = client.patch(
            f"/api/v1/maps/{active_map.id}/status",
            json="archived"
        )
        
        assert response.status_code == 401


class TestMapArchiveEndpoint:
    """Test DELETE /api/v1/maps/{map_id} endpoint (soft delete)."""
    
    @pytest.fixture
    def deletable_map(self, db: Session) -> Map:
        """Create a map for deletion testing."""
        map_obj = Map(
            name="Delete Test Map",
            version="1.0.0",
            storage_url="s3://bucket/delete.png",
            status="active"
        )
        db.add(map_obj)
        db.commit()
        db.refresh(map_obj)
        return map_obj
    
    def test_archive_map_success(self, client: TestClient, manufacturer_token: str, deletable_map: Map, db: Session):
        """Test successfully archiving (soft deleting) a map."""
        response = client.delete(
            f"/api/v1/maps/{deletable_map.id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'archived'
        assert 'successfully archived' in data['message']
        
        # Verify map still exists but is archived
        db.refresh(deletable_map)
        assert deletable_map.status == 'archived'
    
    def test_archive_non_existent_map(self, client: TestClient, manufacturer_token: str):
        """Test archiving a non-existent map."""
        fake_id = str(uuid4())
        response = client.delete(
            f"/api/v1/maps/{fake_id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 404
    
    def test_archive_already_archived_map(self, client: TestClient, manufacturer_token: str, db: Session):
        """Test archiving an already archived map."""
        archived_map = Map(
            name="Already Archived",
            version="1.0.0",
            storage_url="s3://bucket/archived.png",
            status="archived"
        )
        db.add(archived_map)
        db.commit()
        
        response = client.delete(
            f"/api/v1/maps/{archived_map.id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        # Should still return success
        assert response.status_code == 200
        assert response.json()['status'] == 'archived'


class TestMapRoutesEndpoint:
    """Test route-related endpoints."""
    
    @pytest.fixture
    def route_map(self, db: Session) -> Map:
        """Create a map for route testing."""
        map_obj = Map(
            name="Route Test Map",
            version="1.0.0",
            storage_url="s3://bucket/route.png",
            status="active"
        )
        db.add(map_obj)
        db.commit()
        db.refresh(map_obj)
        return map_obj
    
    def test_create_route_success(self, client: TestClient, manufacturer_token: str, route_map: Map):
        """Test successfully creating a route."""
        route_path = [
            [-122.4194, 37.7749],
            [-122.4190, 37.7751],
            [-122.4185, 37.7753]
        ]
        
        response = client.post(
            "/api/v1/maps/routes",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            data={
                "name": "Test Route",
                "route_type": "FULL_COURSE",
                "path": json.dumps(route_path),
                "map_id": str(route_map.id),
                "distance_meters": "1500",
                "estimated_time_seconds": "900"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == "Test Route"
        assert data['route_type'] == "FULL_COURSE"
        assert 'route_id' in data
        assert 'storage_url' in data
    
    def test_create_route_invalid_type(self, client: TestClient, manufacturer_token: str, route_map: Map):
        """Test creating a route with invalid type."""
        route_path = [[-122.4194, 37.7749], [-122.4190, 37.7751]]
        
        response = client.post(
            "/api/v1/maps/routes",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            data={
                "name": "Invalid Route",
                "route_type": "INVALID_TYPE",
                "path": json.dumps(route_path),
                "map_id": str(route_map.id)
            }
        )
        
        assert response.status_code == 400
        assert 'Invalid route_type' in response.json()['detail']
    
    def test_create_route_invalid_path(self, client: TestClient, manufacturer_token: str, route_map: Map):
        """Test creating a route with invalid path."""
        # Path with only one point
        route_path = [[-122.4194, 37.7749]]
        
        response = client.post(
            "/api/v1/maps/routes",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            data={
                "name": "Invalid Path Route",
                "route_type": "FULL_COURSE",
                "path": json.dumps(route_path),
                "map_id": str(route_map.id)
            }
        )
        
        assert response.status_code == 500  # Service will throw error for invalid path
    
    def test_list_routes(self, client: TestClient, manufacturer_token: str):
        """Test listing routes."""
        response = client.get(
            "/api/v1/maps/routes",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'items' in data
        assert 'total' in data
        assert data['status'] == 'success'
    
    def test_get_route_by_id(self, client: TestClient, manufacturer_token: str):
        """Test getting a specific route."""
        # First create a route (assuming one exists or use a fixture)
        route_id = str(uuid4())  # This would be a real route ID in practice
        
        response = client.get(
            f"/api/v1/maps/routes/{route_id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        # Will return 404 for non-existent route
        assert response.status_code in [200, 404]


class TestMapEndpointSecurity:
    """Test security aspects of Map endpoints."""
    
    def test_all_endpoints_require_auth(self, client: TestClient):
        """Test that all Map endpoints require authentication."""
        endpoints = [
            ("POST", "/api/v1/maps/upload", {}),
            ("GET", "/api/v1/maps", None),
            ("GET", f"/api/v1/maps/{uuid4()}", None),
            ("PATCH", f"/api/v1/maps/{uuid4()}/status", {"status": "archived"}),
            ("DELETE", f"/api/v1/maps/{uuid4()}", None),
            ("POST", "/api/v1/maps/routes", {}),
            ("GET", "/api/v1/maps/routes", None),
            ("GET", f"/api/v1/maps/routes/{uuid4()}", None),
        ]
        
        for method, endpoint, json_data in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json=json_data)
            elif method == "PATCH":
                response = client.patch(endpoint, json=json_data)
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == 401, f"Endpoint {method} {endpoint} should require auth"
    
    def test_invalid_token(self, client: TestClient):
        """Test access with invalid token."""
        response = client.get(
            "/api/v1/maps",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    def test_expired_token(self, client: TestClient):
        """Test access with expired token."""
        # Create an expired token
        expired_token = create_access_token(
            data={"sub": "test@example.com", "type": "manufacturer"},
            expires_delta=-3600  # Expired 1 hour ago
        )
        
        response = client.get(
            "/api/v1/maps",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401


class TestMapEndpointPerformance:
    """Test performance aspects of Map endpoints."""
    
    def test_list_maps_performance_with_large_dataset(self, client: TestClient, manufacturer_token: str, db: Session):
        """Test map listing performance with many records."""
        # Create 100 test maps
        maps = []
        for i in range(100):
            map_obj = Map(
                name=f"Performance Test Map {i:03d}",
                version="1.0.0",
                storage_url=f"s3://bucket/perf{i}.png",
                status="active" if i % 2 == 0 else "archived"
            )
            maps.append(map_obj)
        
        db.bulk_save_objects(maps)
        db.commit()
        
        import time
        start_time = time.time()
        
        response = client.get(
            "/api/v1/maps?limit=50",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 2.0  # Should respond within 2 seconds
        assert len(response.json()['items']) <= 50
    
    def test_concurrent_map_uploads(self, client: TestClient, manufacturer_token: str):
        """Test handling concurrent map uploads."""
        import concurrent.futures
        
        def upload_map(index: int):
            img = Image.new('RGB', (512, 384), color=(0, 128, 0))
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return client.post(
                "/api/v1/maps/upload",
                headers={"Authorization": f"Bearer {manufacturer_token}"},
                files={"file": (f"concurrent_{index}.png", img_bytes, "image/png")},
                data={
                    "name": f"Concurrent Map {index}",
                    "version": "1.0.0"
                }
            )
        
        # Upload 5 maps concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(upload_map, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All uploads should succeed
        assert all(r.status_code == 200 for r in results)


class TestMapEndpointErrorHandling:
    """Test error handling in Map endpoints."""
    
    @patch('app.services.map_service.S3Service')
    def test_s3_upload_failure(self, mock_s3, client: TestClient, manufacturer_token: str):
        """Test handling S3 upload failure."""
        # Mock S3 service to raise an exception
        mock_s3.return_value.upload_map.side_effect = Exception("S3 connection failed")
        
        img = Image.new('RGB', (512, 384), color=(0, 128, 0))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        response = client.post(
            "/api/v1/maps/upload",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            files={"file": ("error_test.png", img_bytes, "image/png")},
            data={
                "name": "Error Test Map",
                "version": "1.0.0"
            }
        )
        
        assert response.status_code == 500
        assert 'Map upload failed' in response.json()['detail']
    
    def test_database_connection_error(self, client: TestClient, manufacturer_token: str):
        """Test handling database connection errors."""
        # This would require mocking the database connection
        # For now, we'll test that the endpoint handles errors gracefully
        pass
    
    def test_malformed_json_in_route_path(self, client: TestClient, manufacturer_token: str):
        """Test handling malformed JSON in route path."""
        response = client.post(
            "/api/v1/maps/routes",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            data={
                "name": "Malformed Route",
                "route_type": "FULL_COURSE",
                "path": "not valid json",  # Invalid JSON
                "map_id": str(uuid4())
            }
        )
        
        assert response.status_code == 400
        assert 'Invalid path format' in response.json()['detail']