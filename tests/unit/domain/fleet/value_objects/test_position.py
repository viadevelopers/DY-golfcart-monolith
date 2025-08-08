"""Unit tests for Position value object."""

import pytest
from math import isclose

from app.domain.fleet.value_objects import Position
from app.domain.shared.exceptions import InvalidValueException


class TestPosition:
    """Test suite for Position value object."""
    
    def test_valid_position_creation(self):
        """Test creating a valid position."""
        position = Position(37.7749, -122.4194)
        
        assert position.latitude == 37.7749
        assert position.longitude == -122.4194
        assert position.lat == 37.7749  # Test alias
        assert position.lng == -122.4194  # Test alias
    
    def test_invalid_latitude(self):
        """Test invalid latitude values."""
        with pytest.raises(InvalidValueException) as exc:
            Position(91, 0)
        assert "Invalid latitude: 91" in str(exc.value)
        
        with pytest.raises(InvalidValueException) as exc:
            Position(-91, 0)
        assert "Invalid latitude: -91" in str(exc.value)
    
    def test_invalid_longitude(self):
        """Test invalid longitude values."""
        with pytest.raises(InvalidValueException) as exc:
            Position(0, 181)
        assert "Invalid longitude: 181" in str(exc.value)
        
        with pytest.raises(InvalidValueException) as exc:
            Position(0, -181)
        assert "Invalid longitude: -181" in str(exc.value)
    
    def test_boundary_values(self):
        """Test boundary values for coordinates."""
        # Valid boundary values
        Position(90, 180)
        Position(-90, -180)
        Position(0, 0)
    
    def test_distance_calculation(self):
        """Test distance calculation between positions."""
        # San Francisco
        pos1 = Position(37.7749, -122.4194)
        # Los Angeles (approximately 559 km apart)
        pos2 = Position(34.0522, -118.2437)
        
        distance = pos1.distance_to(pos2)
        # Distance should be approximately 559,000 meters
        assert isclose(distance, 559000, rel_tol=0.01)
        
        # Same position should have zero distance
        same_pos = Position(37.7749, -122.4194)
        assert pos1.distance_to(same_pos) == 0
    
    def test_is_within_bounds(self):
        """Test boundary checking."""
        position = Position(37.7749, -122.4194)
        
        # Within bounds
        assert position.is_within_bounds(37.0, 38.0, -123.0, -122.0)
        
        # Outside bounds
        assert not position.is_within_bounds(38.0, 39.0, -123.0, -122.0)
        assert not position.is_within_bounds(37.0, 38.0, -122.0, -121.0)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        position = Position(37.7749, -122.4194)
        pos_dict = position.to_dict()
        
        assert pos_dict == {
            "lat": 37.7749,
            "lng": -122.4194
        }
    
    def test_equality(self):
        """Test position equality."""
        pos1 = Position(37.7749, -122.4194)
        pos2 = Position(37.7749, -122.4194)
        pos3 = Position(34.0522, -118.2437)
        
        assert pos1 == pos2
        assert pos1 != pos3
        assert pos1 != "not a position"
    
    def test_hash(self):
        """Test position hashing."""
        pos1 = Position(37.7749, -122.4194)
        pos2 = Position(37.7749, -122.4194)
        pos3 = Position(34.0522, -118.2437)
        
        assert hash(pos1) == hash(pos2)
        assert hash(pos1) != hash(pos3)
        
        # Can be used in sets
        position_set = {pos1, pos2, pos3}
        assert len(position_set) == 2
    
    def test_repr(self):
        """Test string representation."""
        position = Position(37.7749, -122.4194)
        
        assert repr(position) == "Position(lat=37.7749, lng=-122.4194)"