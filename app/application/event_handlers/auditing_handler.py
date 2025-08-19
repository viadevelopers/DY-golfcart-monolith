from app.database import SessionLocal
from app.infrastructure.persistence.repositories.event_log_repository import EventLogRepository

async def auditing_handler(event_data: dict):
    """
    An event handler that saves the event to the database for auditing.
    """
    db = SessionLocal()
    try:
        repo = EventLogRepository(db)
        await repo.save_event(event_data)
        db.commit()
    except Exception as e:
        print(f"Error saving event to audit log: {e}")
        db.rollback()
    finally:
        db.close()
