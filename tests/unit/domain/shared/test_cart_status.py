"""Unit tests for CartStatus enumeration."""

import pytest

from app.domain.shared.cart_status import CartStatus


class TestCartStatus:
    """Test suite for CartStatus enumeration."""
    
    def test_cart_status_values(self):
        """Test all cart status values."""
        assert CartStatus.RUNNING.value == "running"
        assert CartStatus.IDLE.value == "idle"
        assert CartStatus.CHARGING.value == "charging"
        assert CartStatus.FIXING.value == "fixing"
        assert CartStatus.OUT_OF_SERVICE.value == "out_of_service"
    
    def test_from_velocity_moving(self):
        """Test status determination when moving."""
        # Any positive velocity should return RUNNING
        assert CartStatus.from_velocity(10.0, CartStatus.IDLE) == CartStatus.RUNNING
        assert CartStatus.from_velocity(0.1, CartStatus.CHARGING) == CartStatus.RUNNING
        assert CartStatus.from_velocity(20.0, CartStatus.FIXING) == CartStatus.RUNNING
    
    def test_from_velocity_stopped_from_running(self):
        """Test status determination when stopping from running."""
        # Zero velocity from RUNNING should return IDLE
        assert CartStatus.from_velocity(0.0, CartStatus.RUNNING) == CartStatus.IDLE
    
    def test_from_velocity_stopped_from_other_status(self):
        """Test status determination when stopped from non-running status."""
        # Zero velocity from other statuses should maintain current status
        assert CartStatus.from_velocity(0.0, CartStatus.IDLE) == CartStatus.IDLE
        assert CartStatus.from_velocity(0.0, CartStatus.CHARGING) == CartStatus.CHARGING
        assert CartStatus.from_velocity(0.0, CartStatus.FIXING) == CartStatus.FIXING
        assert CartStatus.from_velocity(0.0, CartStatus.OUT_OF_SERVICE) == CartStatus.OUT_OF_SERVICE
    
    def test_can_start_trip(self):
        """Test which statuses allow starting a trip."""
        assert CartStatus.IDLE.can_start_trip() is True
        assert CartStatus.CHARGING.can_start_trip() is True
        assert CartStatus.RUNNING.can_start_trip() is False
        assert CartStatus.FIXING.can_start_trip() is False
        assert CartStatus.OUT_OF_SERVICE.can_start_trip() is False
    
    def test_is_operational(self):
        """Test which statuses are considered operational."""
        assert CartStatus.RUNNING.is_operational() is True
        assert CartStatus.IDLE.is_operational() is True
        assert CartStatus.CHARGING.is_operational() is True
        assert CartStatus.FIXING.is_operational() is False
        assert CartStatus.OUT_OF_SERVICE.is_operational() is False
    
    def test_status_comparison(self):
        """Test status comparison and equality."""
        status1 = CartStatus.IDLE
        status2 = CartStatus.IDLE
        status3 = CartStatus.RUNNING
        
        assert status1 == status2
        assert status1 != status3
        assert status1 == CartStatus.IDLE
        assert status1 != CartStatus.RUNNING
    
    def test_string_conversion(self):
        """Test conversion from string."""
        assert CartStatus("idle") == CartStatus.IDLE
        assert CartStatus("running") == CartStatus.RUNNING
        assert CartStatus("charging") == CartStatus.CHARGING
        assert CartStatus("fixing") == CartStatus.FIXING
        assert CartStatus("out_of_service") == CartStatus.OUT_OF_SERVICE
    
    def test_invalid_string_conversion(self):
        """Test invalid string conversion."""
        with pytest.raises(ValueError):
            CartStatus("invalid_status")
    
    def test_iteration(self):
        """Test that all statuses can be iterated."""
        all_statuses = list(CartStatus)
        assert len(all_statuses) == 5
        assert CartStatus.RUNNING in all_statuses
        assert CartStatus.IDLE in all_statuses
        assert CartStatus.CHARGING in all_statuses
        assert CartStatus.FIXING in all_statuses
        assert CartStatus.OUT_OF_SERVICE in all_statuses