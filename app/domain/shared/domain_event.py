"""Base Domain Event class for DDD implementation."""

from abc import ABC
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Any, Dict


class DomainEvent(ABC):
    """Base class for all domain events."""
    
    def __init__(self, aggregate_id: UUID):
        self.event_id = uuid4()
        self.aggregate_id = aggregate_id
        self.occurred_at = datetime.now(timezone.utc)
    
    @property
    def event_name(self) -> str:
        """Get event name from class name."""
        return self.__class__.__name__
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": str(self.event_id),
            "event_name": self.event_name,
            "aggregate_id": str(self.aggregate_id),
            "occurred_at": self.occurred_at.isoformat(),
            "payload": self._get_payload()
        }
    
    def _get_payload(self) -> Dict[str, Any]:
        """Get event-specific payload. Override in subclasses."""
        return {}