"""Unit tests for base Entity class."""

import pytest
from datetime import datetime, timezone
from uuid import UUID
from freezegun import freeze_time

from app.domain.shared import Entity, DomainEvent


class ConcreteEntity(Entity):
    """Concrete implementation for testing."""
    
    def __init__(self, entity_id=None):
        super().__init__(entity_id)
        self.name = "test"


class TestDomainEvent(DomainEvent):
    """Test domain event."""
    
    def __init__(self, aggregate_id: UUID, data: str):
        super().__init__(aggregate_id)
        self.data = data
    
    def _get_payload(self):
        return {"data": self.data}


class TestEntity:
    """Test suite for base Entity class."""
    
    def test_entity_creation_with_id(self, sample_uuid):
        """Test entity creation with provided ID."""
        entity = ConcreteEntity(sample_uuid)
        
        assert entity.id == sample_uuid
        assert isinstance(entity.id, UUID)
        assert entity.created_at is not None
        assert entity.updated_at is None
    
    def test_entity_creation_without_id(self):
        """Test entity creation with auto-generated ID."""
        entity = ConcreteEntity()
        
        assert entity.id is not None
        assert isinstance(entity.id, UUID)
        assert entity.created_at is not None
        assert entity.updated_at is None
    
    @freeze_time("2024-01-01 12:00:00")
    def test_entity_timestamps(self):
        """Test entity timestamp management."""
        entity = ConcreteEntity()
        
        expected_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert entity.created_at == expected_time
        assert entity.updated_at is None
        
        with freeze_time("2024-01-01 13:00:00"):
            entity.mark_updated()
            expected_updated_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
            assert entity.updated_at == expected_updated_time
    
    def test_entity_equality(self, sample_uuid):
        """Test entity equality based on ID."""
        entity1 = ConcreteEntity(sample_uuid)
        entity2 = ConcreteEntity(sample_uuid)
        entity3 = ConcreteEntity()
        
        assert entity1 == entity2
        assert entity1 != entity3
        assert entity1 != "not_an_entity"
    
    def test_entity_hash(self, sample_uuid):
        """Test entity hashing based on ID."""
        entity1 = ConcreteEntity(sample_uuid)
        entity2 = ConcreteEntity(sample_uuid)
        entity3 = ConcreteEntity()
        
        assert hash(entity1) == hash(entity2)
        assert hash(entity1) != hash(entity3)
    
    def test_domain_events(self, sample_uuid):
        """Test domain event management."""
        entity = ConcreteEntity(sample_uuid)
        
        # Initially no events
        assert len(entity.pull_events()) == 0
        
        # Raise events
        event1 = TestDomainEvent(entity.id, "event1")
        event2 = TestDomainEvent(entity.id, "event2")
        
        entity._raise_event(event1)
        entity._raise_event(event2)
        
        # Pull events
        events = entity.pull_events()
        assert len(events) == 2
        assert events[0] == event1
        assert events[1] == event2
        
        # Events cleared after pulling
        assert len(entity.pull_events()) == 0