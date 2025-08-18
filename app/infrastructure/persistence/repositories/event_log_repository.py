from sqlalchemy.orm import Session
from app.models.event_log import EventLog
from uuid import UUID
from datetime import datetime
import json

class EventLogRepository:
    """Repository for saving domain events to the database."""

    def __init__(self, db: Session):
        self.db = db

    async def save_event(self, event_data: dict):
        """
        Create and save an event log from an event data dictionary.
        """
        event_log = EventLog(
            event_id=UUID(event_data["event_id"]),
            event_name=event_data["event_name"],
            aggregate_id=UUID(event_data["aggregate_id"]),
            occurred_at=datetime.fromisoformat(event_data["occurred_at"]),
            payload=event_data["payload"]
        )
        self.db.add(event_log)
        # The transaction will be committed by the Unit of Work or session manager
        # that the handler will use.
        self.db.flush()
