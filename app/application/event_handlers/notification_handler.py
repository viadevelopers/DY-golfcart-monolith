import json

async def notification_handler(event_data: dict):
    """
    A handler for sending notifications based on cart status changes.
    For now, it just logs to the console.
    """
    event_name = event_data.get("event_name")

    if event_name == "CartStatusChanged":
        payload = event_data.get("payload", {})
        cart_id = event_data.get("aggregate_id")
        old_status = payload.get("old_status")
        new_status = payload.get("new_status")

        print(f"--- Notification ---")
        print(f"Cart {cart_id} status changed from '{old_status}' to '{new_status}'")
        print(f"--------------------")

    elif event_name == "BatteryCritical":
        payload = event_data.get("payload", {})
        cart_id = event_data.get("aggregate_id")
        battery_level = payload.get("battery_level")

        print(f"--- URGENT Notification ---")
        print(f"Cart {cart_id} battery is critically low: {battery_level}%")
        print(f"---------------------------")
