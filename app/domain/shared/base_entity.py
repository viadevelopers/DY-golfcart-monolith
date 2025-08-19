"""Base Entity class for DDD implementation."""

from abc import ABC
from typing import Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone

from .domain_event import DomainEvent


class Entity(ABC):
    """Base class for all domain entities."""
    
    def __init__(self, entity_id: Optional[UUID] = None):
        self._id = entity_id or uuid4()
        self._created_at = datetime.now(timezone.utc)
        self._updated_at: Optional[datetime] = None
        self._events: List[DomainEvent] = []
    
    @property
    def id(self) -> UUID:
        """Get entity ID."""
        return self._id
    
    @property
    def created_at(self) -> datetime:
        """Get creation timestamp."""
        return self._created_at
    
    @property
    def updated_at(self) -> Optional[datetime]:
        """Get last update timestamp."""
        return self._updated_at
    
    def mark_updated(self):
        """Mark entity as updated."""
        self._updated_at = datetime.now(timezone.utc)
    
    def _raise_event(self, event: DomainEvent):
        """Raise a domain event."""
        self._events.append(event)
    
    def pull_events(self) -> List[DomainEvent]:
        """Pull and clear domain events."""
        events = self._events.copy()
        self._events.clear()
        return events
    
    def __eq__(self, other: Any) -> bool:
        """Check entity equality based on ID."""
        if not isinstance(other, Entity):
            return False
        return self._id == other._id
    
    def __hash__(self) -> int:
        """Get entity hash based on ID."""
        return hash(self._id)