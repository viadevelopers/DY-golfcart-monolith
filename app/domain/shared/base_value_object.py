"""Base Value Object class for DDD implementation."""

from abc import ABC, abstractmethod
from typing import Any


class ValueObject(ABC):
    """Base class for all value objects."""
    
    @abstractmethod
    def __eq__(self, other: Any) -> bool:
        """Value objects are equal if their values are equal."""
        pass
    
    @abstractmethod
    def __hash__(self) -> int:
        """Value objects must be hashable."""
        pass
    
    def __ne__(self, other: Any) -> bool:
        """Not equal comparison."""
        return not self.__eq__(other)