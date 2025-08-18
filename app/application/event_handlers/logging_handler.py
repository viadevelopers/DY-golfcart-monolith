import json

async def log_event_handler(event_data: dict):
    """A simple event handler that logs the event to the console."""
    print(f"--- New Domain Event ---")
    print(json.dumps(event_data, indent=2))
    print(f"------------------------")
