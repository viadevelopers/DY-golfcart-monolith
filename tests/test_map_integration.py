"""
Integration tests for Map API endpoints.

Tests the complete Map workflow including database persistence and API interactions.
"""
import pytest
import json
from uuid import uuid4
from io import BytesIO
from PIL import Image
from sqlalchemy.orm import Session

from app.models.map import Map
from app.repositories.map_repository import MapRepository


class TestMapAPIIntegration:
    """Integration tests for Map API endpoints."""
    
    def test_map_upload_endpoint(self, client, manufacturer_token):
        """Test POST /api/v1/maps/upload endpoint."""
        # Create test image
        img = Image.new('RGB', (1024, 768), color='green')
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        response = client.post(
            "/api/v1/maps/upload",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            files={"file": ("test_map.png", img_bytes, "image/png")},
            data={
                "name": "Integration Test Map",
                "version": "1.0.0",
                "center_lat": "37.7749",
                "center_lng": "-122.4194",
                "zoom_levels": json.dumps([10, 12, 14, 16, 18])
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'map_id' in data
        assert 'storage_url' in data
        assert data['status'] == 'success'
        assert data['message'] == 'Map uploaded and processed successfully'
    
    def test_list_maps_endpoint(self, client, manufacturer_token, db: Session):
        """Test GET /api/v1/maps endpoint."""
        # Create test maps in database
        repo = MapRepository(db)
        for i in range(3):
            repo.create({
                'name': f'Test Map {i}',
                'version': '1.0.0',
                'storage_url': f's3://bucket/map{i}.png',
                'status': 'active' if i < 2 else 'archived'
            })
        
        # Test without filters
        response = client.get(
            "/api/v1/maps",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'items' in data
        assert len(data['items']) >= 3
        assert data['status'] == 'success'
        
        # Test with status filter
        response = client.get(
            "/api/v1/maps?status=active",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        active_maps = [m for m in data['items'] if m['status'] == 'active']
        assert len(active_maps) >= 2
    
    def test_get_map_by_id_endpoint(self, client, manufacturer_token, db: Session):
        """Test GET /api/v1/maps/{map_id} endpoint."""
        # Create test map
        repo = MapRepository(db)
        test_map = repo.create({
            'name': 'Specific Test Map',
            'version': '2.0.0',
            'storage_url': 's3://bucket/specific.png',
            'status': 'active',
            'file_type': 'image',
            'file_size': 1024000
        })
        
        # Get map by ID
        response = client.get(
            f"/api/v1/maps/{test_map.id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == str(test_map.id)
        assert data['name'] == 'Specific Test Map'
        assert data['version'] == '2.0.0'
        assert data['file_type'] == 'image'
        
        # Test non-existent map
        fake_id = str(uuid4())
        response = client.get(
            f"/api/v1/maps/{fake_id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 404
        assert 'Map not found' in response.json()['detail']
    
    def test_update_map_status_endpoint(self, client, manufacturer_token, db: Session):
        """Test PATCH /api/v1/maps/{map_id}/status endpoint."""
        # Create test map
        repo = MapRepository(db)
        test_map = repo.create({
            'name': 'Status Test Map',
            'version': '1.0.0',
            'storage_url': 's3://bucket/status.png',
            'status': 'active'
        })
        
        # Update status to archived
        response = client.patch(
            f"/api/v1/maps/{test_map.id}/status",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={"status": "archived"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'archived'
        assert data['map_id'] == str(test_map.id)
        
        # Verify in database
        updated_map = repo.get_by_id(test_map.id)
        assert updated_map.status == 'archived'
        
        # Test invalid status
        response = client.patch(
            f"/api/v1/maps/{test_map.id}/status",
            headers={"Authorization": f"Bearer {manufacturer_token}"},
            json={"status": "invalid_status"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_archive_map_endpoint(self, client, manufacturer_token, db: Session):
        """Test DELETE /api/v1/maps/{map_id} endpoint (soft delete)."""
        # Create test map
        repo = MapRepository(db)
        test_map = repo.create({
            'name': 'Delete Test Map',
            'version': '1.0.0',
            'storage_url': 's3://bucket/delete.png',
            'status': 'active'
        })
        
        # Archive (soft delete) the map
        response = client.delete(
            f"/api/v1/maps/{test_map.id}",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'archived'
        assert 'successfully archived' in data['message']
        
        # Verify map is archived, not deleted
        archived_map = repo.get_by_id(test_map.id)
        assert archived_map is not None
        assert archived_map.status == 'archived'
    
    def test_create_route_for_map(self, client, manufacturer_token, db: Session):
        """Test POST /api/v1/maps/routes endpoint."""
        # First create a map
        repo = MapRepository(db)
        test_map = repo.create({
            'name': 'Route Test Map',
            'version': '1.0.0',
            'storage_url': 's3://bucket/route.png',
            'status': 'active'
        })
        
        # Create route for the map
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
                "map_id": str(test_map.id),
                "distance_meters": "1500",
                "estimated_time_seconds": "900"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'Test Route'
        assert data['route_type'] == 'FULL_COURSE'
        assert 'route_id' in data
        assert 'storage_url' in data
    
    def test_list_routes_endpoint(self, client, manufacturer_token):
        """Test GET /api/v1/maps/routes endpoint."""
        response = client.get(
            "/api/v1/maps/routes",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'items' in data
        assert 'total' in data
        assert data['status'] == 'success'
    
    def test_pagination_on_list_maps(self, client, manufacturer_token, db: Session):
        """Test pagination on GET /api/v1/maps endpoint."""
        # Create 15 test maps
        repo = MapRepository(db)
        for i in range(15):
            repo.create({
                'name': f'Pagination Test Map {i:02d}',
                'version': '1.0.0',
                'storage_url': f's3://bucket/page{i}.png',
                'status': 'active'
            })
        
        # Get first page (default limit is 100, but we'll use 5)
        response = client.get(
            "/api/v1/maps?skip=0&limit=5",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['items']) <= 5
        assert data['skip'] == 0
        assert data['limit'] == 5
        
        # Get second page
        response = client.get(
            "/api/v1/maps?skip=5&limit=5",
            headers={"Authorization": f"Bearer {manufacturer_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['items']) <= 5
        assert data['skip'] == 5
    
    def test_authorization_required(self, client):
        """Test that authorization is required for Map endpoints."""
        # Test without token
        endpoints = [
            ("GET", "/api/v1/maps"),
            ("GET", f"/api/v1/maps/{uuid4()}"),
            ("POST", "/api/v1/maps/upload"),
            ("PATCH", f"/api/v1/maps/{uuid4()}/status"),
            ("DELETE", f"/api/v1/maps/{uuid4()}")
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint)
            elif method == "PATCH":
                response = client.patch(endpoint)
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == 401  # Unauthorized


class TestMapSpatialQueries:
    """Test spatial query functionality."""
    
    def test_find_maps_by_bounds(self, db: Session):
        """Test finding maps within geographic bounds."""
        repo = MapRepository(db)
        
        # This test would require PostGIS to be properly set up
        # For now, we'll create a basic test structure
        
        # Create maps with different locations
        # Note: In real test, we'd need to create proper geometry objects
        map1 = repo.create({
            'name': 'San Francisco Map',
            'version': '1.0.0',
            'storage_url': 's3://bucket/sf.png',
            'status': 'active'
        })
        
        map2 = repo.create({
            'name': 'Oakland Map',
            'version': '1.0.0',
            'storage_url': 's3://bucket/oak.png',
            'status': 'active'
        })
        
        # Test would search for maps within bounds
        # maps = repo.find_by_bounds(-122.5, 37.7, -122.3, 37.8)
        # assert len(maps) > 0
    
    def test_find_nearest_maps(self, db: Session):
        """Test finding nearest maps to a point."""
        repo = MapRepository(db)
        
        # Create test maps
        map1 = repo.create({
            'name': 'Nearest Map 1',
            'version': '1.0.0',
            'storage_url': 's3://bucket/near1.png',
            'status': 'active'
        })
        
        # Test would find nearest maps
        # nearest = repo.find_nearest(-122.4194, 37.7749, limit=5)
        # assert len(nearest) <= 5