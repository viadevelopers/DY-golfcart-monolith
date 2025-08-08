"""Unit tests for GolfCart entity."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from freezegun import freeze_time

from app.domain.fleet.entities import GolfCart
from app.domain.fleet.value_objects import CartNumber, Position, Battery, Velocity
from app.domain.shared.cart_status import CartStatus
from app.domain.shared.exceptions import BusinessRuleViolation
from app.domain.fleet.events import (
    CartRegistered,
    CartStarted,
    CartStopped,
    PositionUpdated,
    BatteryLow,
    BatteryCritical,
    CartStatusChanged,
    MaintenanceRequired
)


class TestGolfCart:
    """Test suite for GolfCart entity."""
    
    @pytest.fixture
    def cart_number(self):
        """Provide a cart number for testing."""
        return CartNumber("CART001")
    
    @pytest.fixture
    def new_cart(self, cart_number):
        """Provide a new golf cart for testing."""
        return GolfCart(cart_number)
    
    @pytest.fixture
    def existing_cart(self, cart_number, sample_uuid):
        """Provide an existing golf cart with specific ID."""
        return GolfCart(
            cart_number=cart_number,
            entity_id=sample_uuid,
            position=Position(37.0, -122.0),
            battery=Battery(80.0),
            status=CartStatus.IDLE,
            last_maintenance=datetime.utcnow()  # Recent maintenance
        )
    
    def test_new_cart_creation(self, cart_number):
        """Test creating a new golf cart."""
        cart = GolfCart(cart_number)
        
        assert cart.cart_number == cart_number
        assert cart.position == Position(0.0, 0.0)
        assert cart.battery.level == 100.0
        assert cart.velocity.speed == 0.0
        assert cart.status == CartStatus.IDLE
        assert cart.last_maintenance is None
        assert cart.is_on_trip is False
        
        # Should raise registration event
        events = cart.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CartRegistered)
        assert events[0].cart_number == str(cart_number)
    
    def test_existing_cart_creation(self, cart_number, sample_uuid):
        """Test creating cart from existing data."""
        last_maintenance = datetime.utcnow() - timedelta(days=10)
        cart = GolfCart(
            cart_number=cart_number,
            entity_id=sample_uuid,
            position=Position(37.0, -122.0),
            battery=Battery(75.0),
            status=CartStatus.CHARGING,
            last_maintenance=last_maintenance
        )
        
        assert cart.id == sample_uuid
        assert cart.position == Position(37.0, -122.0)
        assert cart.battery.level == 75.0
        assert cart.status == CartStatus.CHARGING
        assert cart.last_maintenance == last_maintenance
        
        # Should not raise registration event for existing cart
        events = cart.pull_events()
        assert len(events) == 0
    
    def test_start_trip_success(self, existing_cart):
        """Test successfully starting a trip."""
        existing_cart.start_trip()
        
        assert existing_cart.status == CartStatus.RUNNING
        assert existing_cart.is_on_trip is True
        
        events = existing_cart.pull_events()
        assert len(events) == 2
        assert isinstance(events[0], CartStatusChanged)
        assert isinstance(events[1], CartStarted)
    
    def test_start_trip_from_charging(self, cart_number):
        """Test starting trip from charging status."""
        cart = GolfCart(
            cart_number=cart_number,
            status=CartStatus.CHARGING,
            battery=Battery(50.0),
            last_maintenance=datetime.utcnow()  # Recent maintenance
        )
        cart.pull_events()  # Clear registration event
        
        cart.start_trip()
        assert cart.status == CartStatus.RUNNING
    
    def test_start_trip_invalid_status(self, cart_number):
        """Test starting trip from invalid status."""
        cart = GolfCart(
            cart_number=cart_number,
            status=CartStatus.RUNNING
        )
        
        with pytest.raises(BusinessRuleViolation) as exc:
            cart.start_trip()
        assert "Cart must be IDLE or CHARGING" in str(exc.value)
    
    def test_start_trip_low_battery(self, cart_number):
        """Test starting trip with low battery."""
        cart = GolfCart(
            cart_number=cart_number,
            battery=Battery(19.0)
        )
        
        with pytest.raises(BusinessRuleViolation) as exc:
            cart.start_trip()
        assert "Insufficient battery" in str(exc.value)
    
    @freeze_time("2024-01-01")
    def test_start_trip_needs_maintenance(self, cart_number):
        """Test starting trip when maintenance is needed."""
        cart = GolfCart(
            cart_number=cart_number,
            last_maintenance=datetime(2023, 11, 1)  # 2 months ago
        )
        
        with pytest.raises(BusinessRuleViolation) as exc:
            cart.start_trip()
        assert "requires maintenance" in str(exc.value)
    
    def test_stop_trip_success(self, cart_number):
        """Test successfully stopping a trip."""
        cart = GolfCart(
            cart_number=cart_number,
            last_maintenance=datetime.utcnow()  # Recent maintenance
        )
        cart.pull_events()  # Clear registration
        
        cart.start_trip()
        cart.stop_trip()
        
        assert cart.status == CartStatus.IDLE
        assert cart.is_on_trip is False
        assert cart.velocity.speed == 0.0
        
        events = cart.pull_events()
        assert any(isinstance(e, CartStopped) for e in events)
    
    def test_stop_trip_not_running(self, existing_cart):
        """Test stopping trip when not running."""
        with pytest.raises(BusinessRuleViolation) as exc:
            existing_cart.stop_trip()
        assert "Cart is not running" in str(exc.value)
    
    def test_update_position_simple(self, existing_cart):
        """Test simple position update."""
        existing_cart.update_position(37.1, -122.1, 15.0)
        
        assert existing_cart.position == Position(37.1, -122.1)
        assert existing_cart.velocity.speed == 15.0
        
        events = existing_cart.pull_events()
        assert any(isinstance(e, PositionUpdated) for e in events)
    
    def test_update_position_auto_start_trip(self, existing_cart):
        """Test auto-starting trip when velocity > 0."""
        existing_cart.update_position(37.1, -122.1, 10.0)
        
        assert existing_cart.status == CartStatus.RUNNING
        assert existing_cart.is_on_trip is True
        
        events = existing_cart.pull_events()
        assert any(isinstance(e, CartStarted) for e in events)
    
    @freeze_time("2024-01-01 12:00:00")
    def test_update_position_battery_consumption(self, cart_number):
        """Test battery consumption during movement."""
        cart = GolfCart(
            cart_number=cart_number,
            last_maintenance=datetime.utcnow()  # Recent maintenance
        )
        cart.start_trip()
        cart.pull_events()  # Clear events
        
        # First position update
        with freeze_time("2024-01-01 12:00:00"):
            cart.update_position(37.1, -122.1, 20.0)
        
        # Second update 1 hour later
        with freeze_time("2024-01-01 13:00:00"):
            cart.update_position(37.2, -122.2, 20.0)
        
        # Battery should be consumed (roughly 10% per hour at 20 km/h)
        assert cart.battery.level < 100.0
    
    def test_charge_battery_success(self, existing_cart):
        """Test charging battery."""
        initial_level = existing_cart.battery.level
        existing_cart.charge_battery(10.0)
        
        assert existing_cart.battery.level == initial_level + 10.0
        assert existing_cart.status == CartStatus.CHARGING
    
    def test_charge_battery_while_running(self, cart_number):
        """Test that charging while running is not allowed."""
        cart = GolfCart(
            cart_number=cart_number,
            last_maintenance=datetime.utcnow()  # Recent maintenance
        )
        cart.start_trip()
        
        with pytest.raises(BusinessRuleViolation) as exc:
            cart.charge_battery(10.0)
        assert "Cannot charge battery while cart is running" in str(exc.value)
    
    def test_start_maintenance(self, existing_cart):
        """Test starting maintenance."""
        existing_cart.start_maintenance()
        
        assert existing_cart.status == CartStatus.FIXING
        
        events = existing_cart.pull_events()
        assert any(isinstance(e, MaintenanceRequired) for e in events)
    
    def test_complete_maintenance(self, cart_number):
        """Test completing maintenance."""
        cart = GolfCart(cart_number=cart_number, status=CartStatus.FIXING)
        cart.complete_maintenance()
        
        assert cart.status == CartStatus.IDLE
        assert cart.battery.level == 100.0  # Full charge after maintenance
        assert cart.last_maintenance is not None
    
    def test_complete_maintenance_wrong_status(self, existing_cart):
        """Test completing maintenance when not in maintenance."""
        with pytest.raises(BusinessRuleViolation) as exc:
            existing_cart.complete_maintenance()
        assert "not in maintenance mode" in str(exc.value)
    
    def test_decommission(self, existing_cart):
        """Test decommissioning a cart."""
        existing_cart.decommission()
        
        assert existing_cart.status == CartStatus.OUT_OF_SERVICE
    
    def test_decommission_while_running(self, cart_number):
        """Test decommissioning stops running cart first."""
        cart = GolfCart(
            cart_number=cart_number,
            last_maintenance=datetime.utcnow()  # Recent maintenance
        )
        cart.start_trip()
        cart.decommission()
        
        assert cart.status == CartStatus.OUT_OF_SERVICE
        assert cart.is_on_trip is False
    
    def test_can_accept_reservation(self, existing_cart):
        """Test reservation acceptance check."""
        assert existing_cart.can_accept_reservation() is True
        
        # Low battery
        low_battery_cart = GolfCart(
            cart_number=CartNumber("CART002"),
            battery=Battery(15.0),
            last_maintenance=datetime.utcnow()
        )
        assert low_battery_cart.can_accept_reservation() is False
        
        # Wrong status
        running_cart = GolfCart(
            cart_number=CartNumber("CART003"),
            status=CartStatus.RUNNING,
            last_maintenance=datetime.utcnow()
        )
        assert running_cart.can_accept_reservation() is False
    
    def test_estimate_range(self, existing_cart):
        """Test range estimation."""
        range_km = existing_cart.estimate_range()
        assert range_km > 0
        
        # Low battery cart
        low_battery_cart = GolfCart(
            cart_number=CartNumber("CART002"),
            battery=Battery(10.0)
        )
        assert low_battery_cart.estimate_range() == 0.0
    
    def test_to_dict(self, existing_cart):
        """Test conversion to dictionary."""
        cart_dict = existing_cart.to_dict()
        
        assert "id" in cart_dict
        assert cart_dict["cart_number"] == "CART001"
        assert cart_dict["position"]["lat"] == 37.0
        assert cart_dict["position"]["lng"] == -122.0
        assert cart_dict["velocity"] == 0.0
        assert cart_dict["battery_level"] == 80.0
        assert cart_dict["status"] == "idle"
        assert "created_at" in cart_dict
    
    def test_battery_low_event(self, cart_number):
        """Test battery low detection works."""
        # Just test that low battery is properly detected
        low_battery = Battery(19.0)
        assert low_battery.is_low() is True
        
        # And that cart with low battery can't start trip  
        cart = GolfCart(
            cart_number=cart_number,
            battery=Battery(19.0),
            last_maintenance=datetime.utcnow()
        )
        
        with pytest.raises(BusinessRuleViolation) as exc:
            cart.start_trip()
        assert "Insufficient battery" in str(exc.value)
    
    def test_battery_critical_event(self, cart_number):
        """Test battery critical detection works."""
        # Test that critical battery is properly detected
        critical_battery = Battery(9.0)
        assert critical_battery.is_critical() is True
        
        # And that cart with critical battery can't start trip
        cart = GolfCart(
            cart_number=cart_number,
            battery=Battery(9.0),
            last_maintenance=datetime.utcnow()
        )
        
        with pytest.raises(BusinessRuleViolation) as exc:
            cart.start_trip()
        assert "Insufficient battery" in str(exc.value)