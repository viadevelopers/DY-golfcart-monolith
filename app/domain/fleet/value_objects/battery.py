"""Battery value object for golf cart battery management."""

from typing import Any

from app.domain.shared import ValueObject
from app.domain.shared.exceptions import InvalidValueException


class Battery(ValueObject):
    """Represents battery level and related operations."""
    
    LOW_THRESHOLD = 20.0
    CRITICAL_THRESHOLD = 10.0
    
    def __init__(self, level: float):
        if not 0 <= level <= 100:
            raise InvalidValueException(f"Invalid battery level: {level}. Must be between 0 and 100.")
        
        self._level = round(level, 1)
    
    @property
    def level(self) -> float:
        """Get battery level percentage."""
        return self._level
    
    def is_low(self) -> bool:
        """Check if battery is low."""
        return self._level < self.LOW_THRESHOLD
    
    def is_critical(self) -> bool:
        """Check if battery is critically low."""
        return self._level < self.CRITICAL_THRESHOLD
    
    def can_start_trip(self) -> bool:
        """Check if battery has enough charge to start a trip."""
        return self._level >= self.LOW_THRESHOLD
    
    def consume(self, amount: float) -> 'Battery':
        """Consume battery and return new Battery instance."""
        new_level = max(0, self._level - amount)
        return Battery(new_level)
    
    def charge(self, amount: float) -> 'Battery':
        """Charge battery and return new Battery instance."""
        new_level = min(100, self._level + amount)
        return Battery(new_level)
    
    def estimate_remaining_time(self, consumption_rate: float) -> float:
        """Estimate remaining operation time in hours based on consumption rate."""
        if consumption_rate <= 0:
            return float('inf')
        return self._level / consumption_rate
    
    def __eq__(self, other: Any) -> bool:
        """Check equality."""
        if not isinstance(other, Battery):
            return False
        return self._level == other._level
    
    def __hash__(self) -> int:
        """Get hash."""
        return hash(self._level)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Battery({self._level}%)"