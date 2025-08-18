"""Unit tests for DomainEvent class."""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from freezegun import freeze_time

from app.domain.shared import DomainEvent


class ConcreteEvent(DomainEvent):
    """Concrete implementation for testing."""
    
    def __init__(self, aggregate_id: UUID, message: str, value: int):
        super().__init__(aggregate_id)
        self.message = message
        self.value = value
    
    def _get_payload(self):
        return {
            "message": self.message,
            "value": self.value
        }


class TestDomainEvent:
    """Test suite for DomainEvent class."""
    
    @freeze_time("2024-01-01 12:00:00")
    def test_event_creation(self, sample_uuid):
        """Test domain event creation."""
        event = ConcreteEvent(sample_uuid, "test message", 42)
        
        assert event.aggregate_id == sample_uuid
        assert isinstance(event.event_id, UUID)
        assert event.occurred_at == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert event.message == "test message"
        assert event.value == 42
    
    def test_event_name(self, sample_uuid):
        """Test event name derived from class name."""
        event = ConcreteEvent(sample_uuid, "test", 1)
        
        assert event.event_name == "ConcreteEvent"
    
    @freeze_time("2024-01-01 12:00:00")
    def test_event_to_dict(self, sample_uuid):
        """Test event serialization to dictionary."""
        event = ConcreteEvent(sample_uuid, "test message", 42)
        event_dict = event.to_dict()
        
        assert "event_id" in event_dict
        assert event_dict["event_name"] == "ConcreteEvent"
        assert event_dict["aggregate_id"] == str(sample_uuid)
        assert event_dict["occurred_at"] == "2024-01-01T12:00:00+00:00"
        assert event_dict["payload"] == {
            "message": "test message",
            "value": 42
        }
    
    def test_event_unique_ids(self, sample_uuid):
        """Test that each event has a unique ID."""
        event1 = ConcreteEvent(sample_uuid, "msg1", 1)
        event2 = ConcreteEvent(sample_uuid, "msg2", 2)
        
        assert event1.event_id != event2.event_id
        assert event1.aggregate_id == event2.aggregate_id