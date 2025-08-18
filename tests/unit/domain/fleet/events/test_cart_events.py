"""Unit tests for cart domain events."""

import pytest
from uuid import uuid4
from freezegun import freeze_time
from datetime import datetime, timezone

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
from app.domain.fleet.value_objects import Position
from app.domain.shared.cart_status import CartStatus


class TestCartEvents:
    """Test suite for cart domain events."""
    
    @pytest.fixture
    def cart_id(self):
        """Provide a cart ID for testing."""
        return uuid4()
    
    def test_cart_registered_event(self, cart_id):
        """Test CartRegistered event."""
        event = CartRegistered(cart_id, "CART001")
        
        assert event.aggregate_id == cart_id
        assert event.cart_number == "CART001"
        assert event.event_name == "CartRegistered"
        
        payload = event._get_payload()
        assert payload["cart_number"] == "CART001"
    
    def test_cart_started_event(self, cart_id):
        """Test CartStarted event."""
        position = Position(37.0, -122.0)
        event = CartStarted(cart_id, position)
        
        assert event.aggregate_id == cart_id
        assert event.position == position
        assert event.event_name == "CartStarted"
        
        payload = event._get_payload()
        assert payload["position"]["lat"] == 37.0
        assert payload["position"]["lng"] == -122.0
    
    def test_cart_stopped_event_with_duration(self, cart_id):
        """Test CartStopped event with trip duration."""
        position = Position(37.1, -122.1)
        event = CartStopped(cart_id, position, trip_duration_seconds=3600)
        
        assert event.aggregate_id == cart_id
        assert event.position == position
        assert event.trip_duration_seconds == 3600
        assert event.event_name == "CartStopped"
        
        payload = event._get_payload()
        assert payload["position"]["lat"] == 37.1
        assert payload["position"]["lng"] == -122.1
        assert payload["trip_duration_seconds"] == 3600
    
    def test_cart_stopped_event_without_duration(self, cart_id):
        """Test CartStopped event without trip duration."""
        position = Position(37.1, -122.1)
        event = CartStopped(cart_id, position)
        
        payload = event._get_payload()
        assert "trip_duration_seconds" not in payload
    
    def test_position_updated_event(self, cart_id):
        """Test PositionUpdated event."""
        old_pos = Position(37.0, -122.0)
        new_pos = Position(37.1, -122.1)
        event = PositionUpdated(cart_id, old_pos, new_pos, 15.5)
        
        assert event.aggregate_id == cart_id
        assert event.old_position == old_pos
        assert event.new_position == new_pos
        assert event.velocity == 15.5
        assert event.distance_meters > 0
        assert event.event_name == "PositionUpdated"
        
        payload = event._get_payload()
        assert payload["old_position"]["lat"] == 37.0
        assert payload["new_position"]["lat"] == 37.1
        assert payload["velocity"] == 15.5
        assert "distance_meters" in payload
    
    def test_battery_low_event(self, cart_id):
        """Test BatteryLow event."""
        event = BatteryLow(cart_id, 18.5)
        
        assert event.aggregate_id == cart_id
        assert event.battery_level == 18.5
        assert event.event_name == "BatteryLow"
        
        payload = event._get_payload()
        assert payload["battery_level"] == 18.5
    
    def test_battery_critical_event(self, cart_id):
        """Test BatteryCritical event."""
        event = BatteryCritical(cart_id, 8.5)
        
        assert event.aggregate_id == cart_id
        assert event.battery_level == 8.5
        assert event.event_name == "BatteryCritical"
        
        payload = event._get_payload()
        assert payload["battery_level"] == 8.5
    
    def test_cart_status_changed_event(self, cart_id):
        """Test CartStatusChanged event."""
        event = CartStatusChanged(
            cart_id,
            CartStatus.IDLE,
            CartStatus.RUNNING
        )
        
        assert event.aggregate_id == cart_id
        assert event.old_status == CartStatus.IDLE
        assert event.new_status == CartStatus.RUNNING
        assert event.event_name == "CartStatusChanged"
        
        payload = event._get_payload()
        assert payload["old_status"] == "idle"
        assert payload["new_status"] == "running"
    
    def test_maintenance_required_event(self, cart_id):
        """Test MaintenanceRequired event."""
        event = MaintenanceRequired(cart_id, "Battery replacement needed")
        
        assert event.aggregate_id == cart_id
        assert event.reason == "Battery replacement needed"
        assert event.event_name == "MaintenanceRequired"
        
        payload = event._get_payload()
        assert payload["reason"] == "Battery replacement needed"
    
    @freeze_time("2024-01-01 12:00:00")
    def test_event_timestamps(self, cart_id):
        """Test that all events have proper timestamps."""
        events = [
            CartRegistered(cart_id, "CART001"),
            CartStarted(cart_id, Position(0, 0)),
            CartStopped(cart_id, Position(0, 0)),
            BatteryLow(cart_id, 15.0),
            MaintenanceRequired(cart_id, "Test")
        ]
        
        expected_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        for event in events:
            assert event.occurred_at == expected_time
            event_dict = event.to_dict()
            assert event_dict["occurred_at"] == "2024-01-01T12:00:00+00:00"
    
    def test_event_serialization(self, cart_id):
        """Test event serialization to dictionary."""
        position = Position(37.0, -122.0)
        event = CartStarted(cart_id, position)
        
        event_dict = event.to_dict()
        
        # Check standard fields
        assert "event_id" in event_dict
        assert event_dict["event_name"] == "CartStarted"
        assert event_dict["aggregate_id"] == str(cart_id)
        assert "occurred_at" in event_dict
        assert "payload" in event_dict
        
        # Check payload
        assert event_dict["payload"]["position"]["lat"] == 37.0
        assert event_dict["payload"]["position"]["lng"] == -122.0