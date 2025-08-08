"""Unit tests for Velocity value object."""

import pytest

from app.domain.fleet.value_objects import Velocity
from app.domain.shared.exceptions import InvalidValueException


class TestVelocity:
    """Test suite for Velocity value object."""
    
    def test_valid_velocity_creation(self):
        """Test creating a valid velocity."""
        velocity = Velocity(15.5)
        
        assert velocity.speed == 15.5
    
    def test_velocity_rounding(self):
        """Test velocity rounding."""
        velocity = Velocity(15.567)
        
        assert velocity.speed == 15.6
    
    def test_negative_velocity(self):
        """Test that negative velocity is invalid."""
        with pytest.raises(InvalidValueException) as exc:
            Velocity(-5.0)
        assert "Invalid velocity: -5.0" in str(exc.value)
    
    def test_exceeds_max_speed(self):
        """Test velocity exceeding maximum speed."""
        with pytest.raises(InvalidValueException) as exc:
            Velocity(31.0)
        assert "Exceeds maximum speed of 30.0 km/h" in str(exc.value)
    
    def test_boundary_values(self):
        """Test boundary values."""
        Velocity(0.0)  # Valid - stopped
        Velocity(30.0)  # Valid - max speed
        Velocity(15.5)  # Valid - normal speed
    
    def test_is_moving(self):
        """Test movement detection."""
        stopped = Velocity(0.0)
        slow = Velocity(0.1)
        normal = Velocity(15.0)
        
        assert stopped.is_moving() is False
        assert slow.is_moving() is True
        assert normal.is_moving() is True
    
    def test_is_stopped(self):
        """Test stopped detection."""
        stopped = Velocity(0.0)
        moving = Velocity(5.0)
        
        assert stopped.is_stopped() is True
        assert moving.is_stopped() is False
    
    def test_is_over_limit(self):
        """Test speed limit checking."""
        velocity = Velocity(20.0)
        
        assert velocity.is_over_limit(15.0) is True
        assert velocity.is_over_limit(20.0) is False
        assert velocity.is_over_limit(25.0) is False
    
    def test_to_mps_conversion(self):
        """Test conversion to meters per second."""
        velocity = Velocity(18.0)  # 18 km/h = 5 m/s
        
        assert velocity.to_mps() == 5.0
        
        stopped = Velocity(0.0)
        assert stopped.to_mps() == 0.0
        
        # Test precision
        velocity2 = Velocity(18.0)  # 18 km/h = 5 m/s
        assert velocity2.to_mps() == 5.0
    
    def test_equality(self):
        """Test velocity equality."""
        vel1 = Velocity(15.0)
        vel2 = Velocity(15.0)
        vel3 = Velocity(20.0)
        
        assert vel1 == vel2
        assert vel1 != vel3
        assert vel1 != "not a velocity"
    
    def test_hash(self):
        """Test velocity hashing."""
        vel1 = Velocity(15.0)
        vel2 = Velocity(15.0)
        vel3 = Velocity(20.0)
        
        assert hash(vel1) == hash(vel2)
        assert hash(vel1) != hash(vel3)
    
    def test_repr(self):
        """Test string representation."""
        velocity = Velocity(15.5)
        
        assert repr(velocity) == "Velocity(15.5 km/h)"