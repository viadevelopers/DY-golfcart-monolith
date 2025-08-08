"""CartNumber value object for golf cart identification."""

import re
from typing import Any

from app.domain.shared import ValueObject
from app.domain.shared.exceptions import InvalidValueException


class CartNumber(ValueObject):
    """Represents a unique cart number/identifier."""
    
    # Pattern: Alphanumeric, 2-20 characters
    PATTERN = re.compile(r'^[A-Z0-9]{2,20}$')
    
    def __init__(self, value: str):
        if not value or not value.strip():
            raise InvalidValueException("Cart number cannot be empty.")
        
        # Normalize to uppercase
        normalized = value.upper().strip()
        
        if not self.PATTERN.match(normalized):
            raise InvalidValueException(
                f"Invalid cart number: {value}. "
                "Must be 2-20 alphanumeric characters."
            )
        
        self._value = normalized
    
    @property
    def value(self) -> str:
        """Get cart number value."""
        return self._value
    
    def __str__(self) -> str:
        """String representation."""
        return self._value
    
    def __eq__(self, other: Any) -> bool:
        """Check equality."""
        if not isinstance(other, CartNumber):
            return False
        return self._value == other._value
    
    def __hash__(self) -> int:
        """Get hash."""
        return hash(self._value)
    
    def __repr__(self) -> str:
        """Debug representation."""
        return f"CartNumber('{self._value}')"