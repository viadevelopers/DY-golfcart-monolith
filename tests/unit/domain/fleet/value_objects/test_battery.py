"""Unit tests for Battery value object."""

import pytest
from math import isinf

from app.domain.fleet.value_objects import Battery
from app.domain.shared.exceptions import InvalidValueException


class TestBattery:
    """Test suite for Battery value object."""
    
    def test_valid_battery_creation(self):
        """Test creating a valid battery."""
        battery = Battery(75.5)
        
        assert battery.level == 75.5
    
    def test_battery_rounding(self):
        """Test battery level rounding."""
        battery = Battery(75.567)
        
        assert battery.level == 75.6
    
    def test_invalid_battery_levels(self):
        """Test invalid battery levels."""
        with pytest.raises(InvalidValueException) as exc:
            Battery(-1)
        assert "Invalid battery level: -1" in str(exc.value)
        
        with pytest.raises(InvalidValueException) as exc:
            Battery(101)
        assert "Invalid battery level: 101" in str(exc.value)
    
    def test_boundary_values(self):
        """Test boundary values."""
        Battery(0)  # Valid
        Battery(100)  # Valid
        Battery(50.5)  # Valid
    
    def test_is_low(self):
        """Test low battery detection."""
        low_battery = Battery(19.9)
        normal_battery = Battery(20.0)
        high_battery = Battery(80.0)
        
        assert low_battery.is_low() is True
        assert normal_battery.is_low() is False
        assert high_battery.is_low() is False
    
    def test_is_critical(self):
        """Test critical battery detection."""
        critical_battery = Battery(9.9)
        low_battery = Battery(10.0)
        normal_battery = Battery(50.0)
        
        assert critical_battery.is_critical() is True
        assert low_battery.is_critical() is False
        assert normal_battery.is_critical() is False
    
    def test_can_start_trip(self):
        """Test trip start capability check."""
        good_battery = Battery(20.0)
        low_battery = Battery(19.9)
        
        assert good_battery.can_start_trip() is True
        assert low_battery.can_start_trip() is False
    
    def test_consume_battery(self):
        """Test battery consumption."""
        battery = Battery(80.0)
        
        # Normal consumption
        new_battery = battery.consume(10.0)
        assert new_battery.level == 70.0
        assert battery.level == 80.0  # Original unchanged (immutable)
        
        # Consumption that would go below zero
        depleted = battery.consume(100.0)
        assert depleted.level == 0.0
    
    def test_charge_battery(self):
        """Test battery charging."""
        battery = Battery(30.0)
        
        # Normal charging
        charged = battery.charge(20.0)
        assert charged.level == 50.0
        assert battery.level == 30.0  # Original unchanged (immutable)
        
        # Charging that would exceed 100
        overcharged = battery.charge(80.0)
        assert overcharged.level == 100.0
    
    def test_estimate_remaining_time(self):
        """Test remaining time estimation."""
        battery = Battery(50.0)
        
        # Normal consumption rate
        time = battery.estimate_remaining_time(10.0)
        assert time == 5.0  # 50% / 10% per hour = 5 hours
        
        # Zero consumption rate
        time = battery.estimate_remaining_time(0.0)
        assert isinf(time)
        
        # Negative consumption rate (should be infinity)
        time = battery.estimate_remaining_time(-5.0)
        assert isinf(time)
    
    def test_equality(self):
        """Test battery equality."""
        battery1 = Battery(75.0)
        battery2 = Battery(75.0)
        battery3 = Battery(50.0)
        
        assert battery1 == battery2
        assert battery1 != battery3
        assert battery1 != "not a battery"
    
    def test_hash(self):
        """Test battery hashing."""
        battery1 = Battery(75.0)
        battery2 = Battery(75.0)
        battery3 = Battery(50.0)
        
        assert hash(battery1) == hash(battery2)
        assert hash(battery1) != hash(battery3)
    
    def test_repr(self):
        """Test string representation."""
        battery = Battery(75.5)
        
        assert repr(battery) == "Battery(75.5%)"