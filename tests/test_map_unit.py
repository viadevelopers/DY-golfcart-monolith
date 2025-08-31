"""
Unit tests for Map model, repository, and service.

Tests the independent Map implementation based on Title 1 PRD requirements.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from PIL import Image

from app.models.map import Map
from app.repositories.map_repository import MapRepository
from app.services.map_service import MapService
from app.schemas.map import (
    MapResponse, MapUploadRequest,
    MapStatusUpdateRequest
)


class TestMapModel:
    """Test Map model functionality."""
    
    def test_map_creation(self):
        """Test Map model instance creation."""
        map_id = uuid4()
        map_instance = Map(
            id=map_id,
            name="Test Golf Course Map",
            version="1.0.0",
            storage_url="s3://bucket/maps/test.png",
            file_type="image",
            status="active"
        )
        
        assert map_instance.id == map_id
        assert map_instance.name == "Test Golf Course Map"
        assert map_instance.version == "1.0.0"
        assert map_instance.status == "active"
    
    def test_map_to_dict(self):
        """Test Map.to_dict() method."""
        map_instance = Map(
            id=uuid4(),
            name="Test Map",
            version="1.0.0",
            storage_url="s3://test",
            status="active"
        )
        
        result = map_instance.to_dict()
        assert isinstance(result, dict)
        assert 'id' in result
        assert 'name' in result
        assert result['name'] == "Test Map"
        assert result['status'] == "active"
    
    def test_map_mark_as_active(self):
        """Test Map.mark_as_active() method."""
        map_instance = Map(
            id=uuid4(),
            name="Test Map",
            version="1.0.0",
            storage_url="s3://test",
            status="processing"
        )
        
        map_instance.mark_as_active()
        assert map_instance.status == "active"
        assert map_instance.processing_completed_at is not None
        assert map_instance.processing_errors is None
    
    def test_map_mark_as_failed(self):
        """Test Map.mark_as_failed() method."""
        map_instance = Map(
            id=uuid4(),
            name="Test Map",
            version="1.0.0",
            storage_url="s3://test",
            status="processing"
        )
        
        error_details = {"error": "Processing failed", "code": 500}
        map_instance.mark_as_failed(error_details)
        
        assert map_instance.status == "failed"
        assert map_instance.processing_errors == error_details
        assert map_instance.processing_completed_at is not None
    
    def test_map_archive(self):
        """Test Map.archive() method."""
        map_instance = Map(
            id=uuid4(),
            name="Test Map",
            version="1.0.0",
            storage_url="s3://test",
            status="active"
        )
        
        map_instance.archive()
        assert map_instance.status == "archived"
        assert map_instance.updated_at is not None
    
    def test_map_create_from_upload(self):
        """Test Map.create_from_upload() factory method."""
        map_instance = Map.create_from_upload(
            name="Uploaded Map",
            version="2.0.0",
            storage_url="s3://bucket/map.png",
            file_type="image",
            file_size=1024000,
            original_filename="course_map.png"
        )
        
        assert map_instance.name == "Uploaded Map"
        assert map_instance.version == "2.0.0"
        assert map_instance.storage_url == "s3://bucket/map.png"
        assert map_instance.file_type == "image"
        assert map_instance.file_size == 1024000
        assert map_instance.original_filename == "course_map.png"
        assert map_instance.status == "processing"


class TestMapRepository:
    """Test MapRepository functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.query.return_value = db.query
        db.filter.return_value = db.filter
        db.first.return_value = None
        db.all.return_value = []
        db.count.return_value = 0
        return db
    
    @pytest.fixture
    def repository(self, mock_db):
        """Create MapRepository instance with mock DB."""
        return MapRepository(mock_db)
    
    def test_repository_create(self, repository, mock_db):
        """Test MapRepository.create() method."""
        map_data = {
            'name': 'New Map',
            'version': '1.0.0',
            'storage_url': 's3://test',
            'status': 'active'
        }
        
        # Mock the Map creation
        mock_map = Mock(spec=Map)
        with patch('app.repositories.map_repository.Map', return_value=mock_map):
            result = repository.create(map_data)
            
            mock_db.add.assert_called_once_with(mock_map)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_map)
            assert result == mock_map
    
    def test_repository_get_by_id(self, repository, mock_db):
        """Test MapRepository.get_by_id() method."""
        test_id = uuid4()
        mock_map = Mock(spec=Map)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_map
        
        result = repository.get_by_id(test_id)
        
        assert result == mock_map
        mock_db.query.assert_called_with(Map)
    
    def test_repository_get_active(self, repository, mock_db):
        """Test MapRepository.get_active() method."""
        mock_maps = [Mock(spec=Map), Mock(spec=Map)]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_maps
        
        result = repository.get_active()
        
        assert result == mock_maps
        mock_db.query.assert_called_with(Map)
    
    def test_repository_update_status(self, repository, mock_db):
        """Test MapRepository.update_status() method."""
        test_id = uuid4()
        mock_map = Mock(spec=Map)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_map
        
        result = repository.update_status(test_id, 'archived')
        
        assert result is True
        assert mock_map.status == 'archived'
        mock_db.commit.assert_called_once()
    
    def test_repository_archive(self, repository, mock_db):
        """Test MapRepository.archive() method."""
        test_id = uuid4()
        mock_map = Mock(spec=Map)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_map
        
        result = repository.archive(test_id)
        
        assert result is True
        assert mock_map.status == 'archived'
    
    def test_repository_search_with_filters(self, repository, mock_db):
        """Test MapRepository.search() with various filters."""
        filters = {
            'status': 'active',
            'file_type': 'geojson',
            'name_contains': 'Golf'
        }
        
        mock_maps = [Mock(spec=Map), Mock(spec=Map)]
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.count.return_value = 2
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = mock_maps
        
        maps, total = repository.search(filters, skip=0, limit=10)
        
        assert len(maps) == 2
        assert total == 2
    
    def test_repository_get_statistics(self, repository, mock_db):
        """Test MapRepository.get_statistics() method."""
        mock_db.query.return_value.scalar.side_effect = [10, 5, 2, 1, 2]
        mock_db.query.return_value.filter.return_value.scalar.side_effect = [5, 2, 1, 2, 3, 7]
        mock_db.query.return_value.group_by.return_value.all.return_value = [
            ('geojson', 3),
            ('image', 7)
        ]
        
        stats = repository.get_statistics()
        
        assert stats['total'] == 10
        assert stats['by_status']['active'] == 5
        assert stats['by_status']['archived'] == 2
        assert stats['by_file_type']['geojson'] == 3
        assert stats['by_file_type']['image'] == 7


class TestMapService:
    """Test MapService functionality."""
    
    @pytest.fixture
    def service(self):
        """Create MapService instance."""
        return MapService()
    
    @patch('app.services.map_service.get_db_context')
    @patch('app.services.map_service.S3Service')
    def test_service_process_map_upload(self, mock_s3_class, mock_db_context, service):
        """Test MapService.process_map_upload() method."""
        # Setup mock S3 service
        mock_s3_instance = MagicMock()
        mock_s3_class.return_value = mock_s3_instance
        mock_s3_instance.upload_map.return_value = {
            'url': 's3://bucket/maps/test.png',
            's3_key': 'maps/test.png'
        }
        mock_s3_instance.generate_tiles.return_value = {
            'tiles': ['tile1.png', 'tile2.png']
        }
        
        # Manually set the s3_service on the service instance
        service.s3_service = mock_s3_instance
        
        # Setup mock database context
        mock_db = MagicMock()
        mock_db_context.return_value.__enter__.return_value = mock_db
        
        # Create test image data
        img = Image.new('RGB', (100, 100), color=(0, 128, 0))  # Green as RGB tuple
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        file_data = img_bytes.getvalue()
        
        result = service.process_map_upload(
            file_data=file_data,
            filename='test_map.png',
            name='Test Map',
            version='1.0.0',
            center_lat=37.7749,
            center_lng=-122.4194,
            zoom_levels=[10, 12, 14]
        )
        
        assert 'map_id' in result
        assert 'storage_url' in result
        assert result['storage_url'] == 's3://bucket/maps/test.png'
        assert result['status'] == 'processed'
        
        # Verify S3 service was called
        mock_s3_instance.upload_map.assert_called_once()
        mock_s3_instance.generate_tiles.assert_called_once()
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @patch('app.services.map_service.get_db_context')
    def test_service_list_maps(self, mock_db_context, service):
        """Test MapService.list_maps() method."""
        mock_db = MagicMock()
        mock_maps = [Mock(spec=Map), Mock(spec=Map)]
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_maps
        
        result = service.list_maps({}, mock_db, skip=0, limit=10)
        
        assert result == mock_maps
        mock_db.query.assert_called_with(Map)
    
    def test_service_detect_file_type(self, service):
        """Test MapService._detect_file_type() method."""
        assert service._detect_file_type('map.geojson') == 'geojson'
        assert service._detect_file_type('map.json') == 'geojson'
        assert service._detect_file_type('map.kml') == 'kml'
        assert service._detect_file_type('map.png') == 'image'
        assert service._detect_file_type('map.jpg') == 'image'
        assert service._detect_file_type('map.unknown') == 'unknown'
        assert service._detect_file_type('noextension') == 'unknown'
    
    def test_service_calculate_route_distance(self, service):
        """Test MapService._calculate_route_distance() method."""
        # Simple two-point path
        path = [
            [-122.4194, 37.7749],  # San Francisco
            [-122.4190, 37.7751]   # Slightly north
        ]
        
        distance = service._calculate_route_distance(path)
        
        # Should be a positive distance
        assert distance > 0
        # Rough estimate: should be less than 1000 meters for such close points
        assert distance < 1000
    
    def test_service_calculate_map_bounds(self, service):
        """Test MapService._calculate_map_bounds() method."""
        # Test with center point
        bounds = service._calculate_map_bounds(b'', 37.7749, -122.4194)
        
        assert len(bounds) == 2
        assert len(bounds[0]) == 2  # Southwest corner
        assert len(bounds[1]) == 2  # Northeast corner
        assert bounds[0][0] < bounds[1][0]  # West < East
        assert bounds[0][1] < bounds[1][1]  # South < North
    
    def test_service_extract_map_features(self, service):
        """Test MapService._extract_map_features() method."""
        # Test with different file types
        features_geojson = service._extract_map_features(b'', 'test.geojson')
        assert any(f['type'] == 'geojson_features' for f in features_geojson)
        
        features_kml = service._extract_map_features(b'', 'test.kml')
        assert any(f['type'] == 'kml_features' for f in features_kml)
        
        features_image = service._extract_map_features(b'', 'test.png')
        assert any(f['type'] == 'raster_image' for f in features_image)


class TestMapSchemas:
    """Test Pydantic schemas for Map data."""
    
    def test_map_response_schema(self):
        """Test MapResponse schema validation."""
        data = {
            'id': str(uuid4()),
            'name': 'Test Map',
            'version': '1.0.0',
            'storage_url': 's3://test',
            'status': 'active',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        response = MapResponse(**data)
        assert response.name == 'Test Map'
        assert response.status == 'active'
    
    def test_map_upload_request_schema(self):
        """Test MapUploadRequest schema validation."""
        data = {
            'name': 'New Map',
            'version': '1.0.0',
            'center_lat': 37.7749,
            'center_lng': -122.4194,
            'zoom_levels': [10, 12, 14, 16]
        }
        
        request = MapUploadRequest(**data)
        assert request.name == 'New Map'
        assert request.center_lat == 37.7749
        if request.zoom_levels is not None:
            assert len(request.zoom_levels) == 4
    
    def test_map_status_update_request_schema(self):
        """Test MapStatusUpdateRequest schema validation."""
        # Valid status values
        for status in ['active', 'archived', 'processing', 'failed']:
            request = MapStatusUpdateRequest(status=status)
            assert request.status == status
        
        # Invalid status should raise validation error
        with pytest.raises(ValueError):
            MapStatusUpdateRequest(status='invalid_status')