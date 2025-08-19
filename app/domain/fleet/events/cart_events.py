"""Domain events for golf cart operations."""

from typing import Any, Dict, Optional
from uuid import UUID

from app.domain.shared import DomainEvent
from app.domain.shared.cart_status import CartStatus
from app.domain.fleet.value_objects import Position


class CartRegistered(DomainEvent):
    """Event raised when a new cart is registered."""
    
    def __init__(self, cart_id: UUID, cart_number: str):
        super().__init__(cart_id)
        self.cart_number = cart_number
    
    def _get_payload(self) -> Dict[str, Any]:
        return {
            "cart_number": self.cart_number
        }


class CartStarted(DomainEvent):
    """Event raised when a cart starts a trip."""
    
    def __init__(self, cart_id: UUID, position: Position):
        super().__init__(cart_id)
        self.position = position
    
    def _get_payload(self) -> Dict[str, Any]:
        return {
            "position": self.position.to_dict()
        }


class CartStopped(DomainEvent):
    """Event raised when a cart stops."""
    
    def __init__(self, cart_id: UUID, position: Position, trip_duration_seconds: Optional[int] = None):
        super().__init__(cart_id)
        self.position = position
        self.trip_duration_seconds = trip_duration_seconds
    
    def _get_payload(self) -> Dict[str, Any]:
        payload = {"position": self.position.to_dict()}
        if self.trip_duration_seconds:
            payload["trip_duration_seconds"] = self.trip_duration_seconds
        return payload


class PositionUpdated(DomainEvent):
    """Event raised when cart position is updated."""
    
    def __init__(self, cart_id: UUID, old_position: Position, new_position: Position, velocity: float):
        super().__init__(cart_id)
        self.old_position = old_position
        self.new_position = new_position
        self.velocity = velocity
        self.distance_meters = old_position.distance_to(new_position)
    
    def _get_payload(self) -> Dict[str, Any]:
        return {
            "old_position": self.old_position.to_dict(),
            "new_position": self.new_position.to_dict(),
            "velocity": self.velocity,
            "distance_meters": self.distance_meters
        }


class BatteryLow(DomainEvent):
    """Event raised when battery level is low."""
    
    def __init__(self, cart_id: UUID, battery_level: float):
        super().__init__(cart_id)
        self.battery_level = battery_level
    
    def _get_payload(self) -> Dict[str, Any]:
        return {
            "battery_level": self.battery_level
        }


class BatteryCritical(DomainEvent):
    """Event raised when battery level is critically low."""
    
    def __init__(self, cart_id: UUID, battery_level: float):
        super().__init__(cart_id)
        self.battery_level = battery_level
    
    def _get_payload(self) -> Dict[str, Any]:
        return {
            "battery_level": self.battery_level
        }


class CartStatusChanged(DomainEvent):
    """Event raised when cart status changes."""
    
    def __init__(self, cart_id: UUID, old_status: CartStatus, new_status: CartStatus):
        super().__init__(cart_id)
        self.old_status = old_status
        self.new_status = new_status
    
    def _get_payload(self) -> Dict[str, Any]:
        return {
            "old_status": self.old_status.value,
            "new_status": self.new_status.value
        }


class MaintenanceRequired(DomainEvent):
    """Event raised when cart requires maintenance."""
    
    def __init__(self, cart_id: UUID, reason: str):
        super().__init__(cart_id)
        self.reason = reason
    
    def _get_payload(self) -> Dict[str, Any]:
        return {
            "reason": self.reason
        }