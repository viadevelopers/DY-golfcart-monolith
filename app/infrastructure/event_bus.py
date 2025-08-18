import json
import asyncio
import socket
from typing import Dict, List, Callable
from app.domain.shared.domain_event import DomainEvent
from app.redis import get_redis_connection
import redis.exceptions

class EventBus:
    """An event bus for publishing events to a Redis Stream."""

    def __init__(self, redis_conn, stream_name: str = "domain_events"):
        self.redis = redis_conn
        self.stream_name = stream_name

    async def publish(self, event: DomainEvent):
        """Publish a domain event to the Redis Stream."""
        event_data = event.to_dict()
        # The stream message must be a dictionary of bytes or strings.
        # We'll serialize the entire event payload into a single JSON string.
        message = {"event_json": json.dumps(event_data)}
        await self.redis.xadd(self.stream_name, message)


class EventDispatcher:
    """
    A dispatcher that listens to events from a Redis Stream using a consumer group
    and calls the appropriate handlers.
    """

    def __init__(self, event_bus: EventBus, group_name: str = "event_handlers"):
        self.event_bus = event_bus
        self.group_name = group_name
        # Create a unique consumer name for this instance
        self.consumer_name = f"{group_name}-{socket.gethostname()}-{asyncio.get_running_loop().__hash__()}"
        self._handlers: Dict[str, List[Callable]] = {}

    def register(self, event_name: str, handler: Callable):
        """Register a handler for a specific event name."""
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)

    async def _handle_message(self, message_id: str, event_json: str):
        """Handle a raw message from the stream."""
        try:
            event_data = json.loads(event_json)
            event_name = event_data.get("event_name")

            if event_name in self._handlers:
                # Create a list of coroutines for all handlers of this event
                tasks = [handler(event_data) for handler in self._handlers[event_name]]
                # Run all handlers concurrently
                await asyncio.gather(*tasks)

            # Acknowledge the message after successful processing
            await self.event_bus.redis.xack(self.event_bus.stream_name, self.group_name, message_id)

        except json.JSONDecodeError:
            print(f"Error decoding JSON for message {message_id}: {event_json}")
        except Exception as e:
            print(f"Error processing message {message_id}: {e}")
            # In a real system, you might want to implement a dead-letter queue
            # or other error handling mechanism instead of just printing.

    async def _ensure_consumer_group_exists(self):
        """Create the consumer group if it doesn't already exist."""
        try:
            await self.event_bus.redis.xgroup_create(
                name=self.event_bus.stream_name,
                groupname=self.group_name,
                mkstream=True,  # Create the stream if it doesn't exist
                id='0'  # Start from the beginning of the stream
            )
            print(f"Created consumer group '{self.group_name}' for stream '{self.event_bus.stream_name}'.")
        except redis.exceptions.ResponseError as e:
            # If the group already exists, Redis will raise a ResponseError.
            # This is expected, so we can ignore it.
            if "BUSYGROUP" not in str(e):
                raise

    async def start(self):
        """Start listening for events and dispatching them."""
        await self._ensure_consumer_group_exists()
        print(f"Event dispatcher started. Consumer '{self.consumer_name}' in group '{self.group_name}' listening on stream '{self.event_bus.stream_name}'.")

        while True:
            try:
                # Read from the stream as part of the consumer group.
                # `block=0` means wait forever for new messages.
                # '>' is a special ID that means "only new messages that have never been delivered to another consumer".
                response = await self.event_bus.redis.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams={self.event_bus.stream_name: '>'},
                    count=1,
                    block=0
                )

                if response:
                    # response is a list of streams, e.g., [[b'stream-name', [(b'message-id', {b'key': b'value'})]]]
                    for stream_name, messages in response:
                        for message_id, fields in messages:
                            # The message ID and fields are bytes, so we need to decode them.
                            # We expect a single field 'event_json' containing the event data.
                            await self._handle_message(message_id.decode(), fields[b'event_json'].decode())

            except Exception as e:
                print(f"Error in event dispatcher loop: {e}")
                # Wait a bit before retrying to avoid spamming errors in a tight loop.
                await asyncio.sleep(5)
