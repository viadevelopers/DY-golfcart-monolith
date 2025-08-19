"""Velocity value object for golf cart speed."""

from typing import Any

from app.domain.shared import ValueObject
from app.domain.shared.exceptions import InvalidValueException


class Velocity(ValueObject):
    """Represents velocity in km/h."""
    
    MAX_SPEED = 30.0  # Maximum allowed speed for golf carts
    
    def __init__(self, speed: float):
        if speed < 0:
            raise InvalidValueException(f"Invalid velocity: {speed}. Must be non-negative.")
        if speed > self.MAX_SPEED:
            raise InvalidValueException(f"Invalid velocity: {speed}. Exceeds maximum speed of {self.MAX_SPEED} km/h.")
        
        self._speed = round(speed, 1)
    
    @property
    def speed(self) -> float:
        """Get speed in km/h."""
        return self._speed
    
    def is_moving(self) -> bool:
        """Check if cart is moving."""
        return self._speed > 0
    
    def is_stopped(self) -> bool:
        """Check if cart is stopped."""
        return self._speed == 0
    
    def is_over_limit(self, limit: float) -> bool:
        """Check if speed exceeds given limit."""
        return self._speed > limit
    
    def to_mps(self) -> float:
        """Convert to meters per second."""
        return self._speed / 3.6
    
    def __eq__(self, other: Any) -> bool:
        """Check equality."""
        if not isinstance(other, Velocity):
            return False
        return self._speed == other._speed
    
    def __hash__(self) -> int:
        """Get hash."""
        return hash(self._speed)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Velocity({self._speed} km/h)"