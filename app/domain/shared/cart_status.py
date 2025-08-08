"""CartStatus value object - single source of truth for cart status."""

from enum import Enum


class CartStatus(str, Enum):
    """Cart status enumeration used across all layers."""
    
    RUNNING = "running"
    IDLE = "idle"
    CHARGING = "charging"
    FIXING = "fixing"
    OUT_OF_SERVICE = "out_of_service"
    
    @classmethod
    def from_velocity(cls, velocity: float, current_status: 'CartStatus') -> 'CartStatus':
        """Determine status based on velocity."""
        if velocity > 0:
            return cls.RUNNING
        elif current_status == cls.RUNNING:
            return cls.IDLE
        return current_status
    
    def can_start_trip(self) -> bool:
        """Check if cart can start a trip from current status."""
        return self in [self.IDLE, self.CHARGING]
    
    def is_operational(self) -> bool:
        """Check if cart is operational."""
        return self not in [self.FIXING, self.OUT_OF_SERVICE]