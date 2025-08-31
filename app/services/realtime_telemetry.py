"""
Real-time Telemetry Event Processing

Handles real-time telemetry data from MQTT messages, processes them through
the telemetry service, and provides real-time event streaming capabilities.
"""

import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, deque

from app.core.config import settings
from app.services.telemetry_service import get_telemetry_service
from app.services.mqtt_service import mqtt_service

logger = logging.getLogger(__name__)


class RealTimeTelemetryProcessor:
    """
    Real-time telemetry processor that handles incoming MQTT telemetry data
    and processes it through the telemetry service with event streaming.
    
    Features:
    - Asynchronous telemetry processing with thread pool for database operations
    - Real-time event streaming to connected clients
    - Message buffering and batch processing for high throughput
    - Error handling and retry mechanisms
    - Performance monitoring and metrics
    """
    
    def __init__(self):
        self.telemetry_service = get_telemetry_service()
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="telemetry")
        
        # Event streaming
        self.event_subscribers: List[Callable] = []
        self.cart_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Message buffering for batch processing
        self.message_buffer: deque = deque(maxlen=1000)
        self.batch_size = 10
        self.batch_timeout = 5.0  # seconds
        
        # Performance metrics
        self.processed_messages = 0
        self.failed_messages = 0
        self.last_reset = datetime.now(timezone.utc)
        
        # Processing state
        self.processing_active = False
        self.batch_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize real-time telemetry processing."""
        try:
            # Register MQTT message handlers
            await self._register_mqtt_handlers()
            
            # Start batch processing task
            self.processing_active = True
            self.batch_task = asyncio.create_task(self._batch_processor())
            
            logger.info("Real-time telemetry processor initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize real-time telemetry processor: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the real-time processor."""
        try:
            self.processing_active = False
            
            if self.batch_task:
                self.batch_task.cancel()
                try:
                    await self.batch_task
                except asyncio.CancelledError:
                    pass
            
            # Process remaining messages
            await self._process_buffered_messages()
            
            # Shutdown executor
            self.executor.shutdown(wait=True)
            
            logger.info("Real-time telemetry processor shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during telemetry processor shutdown: {e}")
    
    async def _register_mqtt_handlers(self):
        """Register MQTT message handlers for telemetry data."""
        # Handler for telemetry data
        telemetry_pattern = f"{settings.MQTT_TOPIC_PREFIX}/cart/+/telemetry"
        mqtt_service.add_message_handler(telemetry_pattern, self._handle_telemetry_message)
        
        # Handler for cart status updates
        status_pattern = f"{settings.MQTT_TOPIC_PREFIX}/cart/+/status"
        mqtt_service.add_message_handler(status_pattern, self._handle_status_message)
        
        # Handler for cart events
        event_pattern = f"{settings.MQTT_TOPIC_PREFIX}/cart/+/event"
        mqtt_service.add_message_handler(event_pattern, self._handle_event_message)
        
        logger.info("Registered MQTT handlers for real-time telemetry processing")
    
    def _handle_telemetry_message(self, topic: str, payload: Dict[str, Any]):
        """Handle incoming telemetry message from MQTT."""
        try:
            # Extract cart ID from topic (assumes format: prefix/cart/{cart_id}/telemetry)
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3 and topic_parts[-2] != '+':
                cart_serial = topic_parts[-2]
                
                # Add to buffer for batch processing
                self.message_buffer.append({
                    'type': 'telemetry',
                    'cart_serial': cart_serial,
                    'payload': payload,
                    'timestamp': datetime.now(timezone.utc),
                    'topic': topic
                })
                
                logger.debug(f"Buffered telemetry message from cart {cart_serial}")
            else:
                logger.warning(f"Invalid telemetry topic format: {topic}")
                
        except Exception as e:
            logger.error(f"Error handling telemetry message from {topic}: {e}")
            self.failed_messages += 1
    
    def _handle_status_message(self, topic: str, payload: Dict[str, Any]):
        """Handle cart status message from MQTT."""
        try:
            # Extract cart ID from topic
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3 and topic_parts[-2] != '+':
                cart_serial = topic_parts[-2]
                
                # Add to buffer for processing
                self.message_buffer.append({
                    'type': 'status',
                    'cart_serial': cart_serial,
                    'payload': payload,
                    'timestamp': datetime.now(timezone.utc),
                    'topic': topic
                })
                
                logger.debug(f"Buffered status message from cart {cart_serial}")
            else:
                logger.warning(f"Invalid status topic format: {topic}")
                
        except Exception as e:
            logger.error(f"Error handling status message from {topic}: {e}")
            self.failed_messages += 1
    
    def _handle_event_message(self, topic: str, payload: Dict[str, Any]):
        """Handle cart event message from MQTT."""
        try:
            # Extract cart ID from topic
            topic_parts = topic.split('/')
            if len(topic_parts) >= 3 and topic_parts[-2] != '+':
                cart_serial = topic_parts[-2]
                
                # Process event immediately (don't buffer)
                asyncio.create_task(self._process_event_message(cart_serial, payload))
                
                logger.debug(f"Processing event message from cart {cart_serial}")
            else:
                logger.warning(f"Invalid event topic format: {topic}")
                
        except Exception as e:
            logger.error(f"Error handling event message from {topic}: {e}")
            self.failed_messages += 1
    
    async def _batch_processor(self):
        """Background task for batch processing of buffered messages."""
        while self.processing_active:
            try:
                await asyncio.sleep(self.batch_timeout)
                
                if self.message_buffer:
                    await self._process_buffered_messages()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
                await asyncio.sleep(1)  # Brief pause before retry
    
    async def _process_buffered_messages(self):
        """Process buffered messages in batches."""
        try:
            # Get batch of messages
            batch = []
            for _ in range(min(self.batch_size, len(self.message_buffer))):
                if self.message_buffer:
                    batch.append(self.message_buffer.popleft())
            
            if not batch:
                return
            
            # Process batch in parallel
            tasks = []
            for message in batch:
                if message['type'] == 'telemetry':
                    task = asyncio.create_task(
                        self._process_telemetry_message(
                            message['cart_serial'], 
                            message['payload']
                        )
                    )
                elif message['type'] == 'status':
                    task = asyncio.create_task(
                        self._process_status_message(
                            message['cart_serial'], 
                            message['payload']
                        )
                    )
                else:
                    continue
                
                tasks.append(task)
            
            # Wait for all tasks to complete
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count successful/failed processing
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Batch processing error: {result}")
                        self.failed_messages += 1
                    else:
                        self.processed_messages += 1
                        
                logger.debug(f"Processed batch of {len(batch)} messages")
                
        except Exception as e:
            logger.error(f"Error processing message batch: {e}")
    
    async def _process_telemetry_message(self, cart_serial: str, payload: Dict[str, Any]):
        """Process telemetry message through telemetry service."""
        try:
            # Convert cart serial to cart_id (UUID)
            # In a real implementation, you'd look up the cart by serial number
            # For now, assume the cart_serial is the UUID string
            cart_id = cart_serial
            
            # Process telemetry through service
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: asyncio.run(
                    self.telemetry_service.process_telemetry(cart_id, payload)
                )
            )
            
            # Stream result to subscribers
            if result.get('status') == 'success':
                await self._stream_telemetry_update(cart_id, result)
                
                # If events were generated, stream them too
                if result.get('events_generated', 0) > 0:
                    await self._stream_events(cart_id, result.get('events', []))
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing telemetry for cart {cart_serial}: {e}")
            raise
    
    async def _process_status_message(self, cart_serial: str, payload: Dict[str, Any]):
        """Process cart status message."""
        try:
            # Process status update
            # This could include cart mode changes, connectivity status, etc.
            status_update = {
                'cart_serial': cart_serial,
                'status': payload.get('status'),
                'mode': payload.get('mode'),
                'timestamp': payload.get('timestamp', datetime.now(timezone.utc).isoformat())
            }
            
            # Stream status update to subscribers
            await self._stream_status_update(cart_serial, status_update)
            
            return status_update
            
        except Exception as e:
            logger.error(f"Error processing status for cart {cart_serial}: {e}")
            raise
    
    async def _process_event_message(self, cart_serial: str, payload: Dict[str, Any]):
        """Process cart event message."""
        try:
            # Process incoming cart event
            event_data = {
                'cart_serial': cart_serial,
                'event_type': payload.get('event_type'),
                'severity': payload.get('severity'),
                'message': payload.get('message'),
                'data': payload.get('data', {}),
                'timestamp': payload.get('timestamp', datetime.now(timezone.utc).isoformat())
            }
            
            # Stream event to subscribers
            await self._stream_cart_event(cart_serial, event_data)
            
            return event_data
            
        except Exception as e:
            logger.error(f"Error processing event for cart {cart_serial}: {e}")
            raise
    
    async def _stream_telemetry_update(self, cart_id: str, telemetry_data: Dict[str, Any]):
        """Stream telemetry update to subscribers."""
        try:
            message = {
                'type': 'telemetry_update',
                'cart_id': cart_id,
                'data': telemetry_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Send to global subscribers
            await self._notify_subscribers(self.event_subscribers, message)
            
            # Send to cart-specific subscribers
            if cart_id in self.cart_subscribers:
                await self._notify_subscribers(self.cart_subscribers[cart_id], message)
                
        except Exception as e:
            logger.error(f"Error streaming telemetry update: {e}")
    
    async def _stream_events(self, cart_id: str, events: List[Dict[str, Any]]):
        """Stream generated events to subscribers."""
        try:
            for event in events:
                message = {
                    'type': 'cart_event',
                    'cart_id': cart_id,
                    'event': event,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # Send to global subscribers
                await self._notify_subscribers(self.event_subscribers, message)
                
                # Send to cart-specific subscribers
                if cart_id in self.cart_subscribers:
                    await self._notify_subscribers(self.cart_subscribers[cart_id], message)
                    
        except Exception as e:
            logger.error(f"Error streaming events: {e}")
    
    async def _stream_status_update(self, cart_serial: str, status_data: Dict[str, Any]):
        """Stream cart status update to subscribers."""
        try:
            message = {
                'type': 'status_update',
                'cart_serial': cart_serial,
                'data': status_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Send to global subscribers
            await self._notify_subscribers(self.event_subscribers, message)
            
            # Send to cart-specific subscribers
            if cart_serial in self.cart_subscribers:
                await self._notify_subscribers(self.cart_subscribers[cart_serial], message)
                
        except Exception as e:
            logger.error(f"Error streaming status update: {e}")
    
    async def _stream_cart_event(self, cart_serial: str, event_data: Dict[str, Any]):
        """Stream cart event to subscribers."""
        try:
            message = {
                'type': 'cart_event_direct',
                'cart_serial': cart_serial,
                'event': event_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Send to global subscribers
            await self._notify_subscribers(self.event_subscribers, message)
            
            # Send to cart-specific subscribers
            if cart_serial in self.cart_subscribers:
                await self._notify_subscribers(self.cart_subscribers[cart_serial], message)
                
        except Exception as e:
            logger.error(f"Error streaming cart event: {e}")
    
    async def _notify_subscribers(self, subscribers: List[Callable], message: Dict[str, Any]):
        """Notify subscribers with message."""
        if not subscribers:
            return
            
        notification_tasks = []
        for subscriber in subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    task = asyncio.create_task(subscriber(message))
                else:
                    # Wrap sync function in executor
                    task = asyncio.create_task(
                        asyncio.get_event_loop().run_in_executor(
                            self.executor, subscriber, message
                        )
                    )
                notification_tasks.append(task)
            except Exception as e:
                logger.error(f"Error creating notification task: {e}")
        
        # Execute notifications concurrently
        if notification_tasks:
            await asyncio.gather(*notification_tasks, return_exceptions=True)
    
    def subscribe_to_events(self, callback: Callable):
        """Subscribe to all real-time telemetry events."""
        if callback not in self.event_subscribers:
            self.event_subscribers.append(callback)
            logger.debug(f"Added global event subscriber: {callback}")
    
    def subscribe_to_cart(self, cart_id: str, callback: Callable):
        """Subscribe to events for a specific cart."""
        if callback not in self.cart_subscribers[cart_id]:
            self.cart_subscribers[cart_id].append(callback)
            logger.debug(f"Added cart-specific subscriber for {cart_id}: {callback}")
    
    def unsubscribe_from_events(self, callback: Callable):
        """Unsubscribe from all events."""
        if callback in self.event_subscribers:
            self.event_subscribers.remove(callback)
            logger.debug(f"Removed global event subscriber: {callback}")
    
    def unsubscribe_from_cart(self, cart_id: str, callback: Callable):
        """Unsubscribe from events for a specific cart."""
        if cart_id in self.cart_subscribers and callback in self.cart_subscribers[cart_id]:
            self.cart_subscribers[cart_id].remove(callback)
            logger.debug(f"Removed cart-specific subscriber for {cart_id}: {callback}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics."""
        now = datetime.now(timezone.utc)
        uptime = (now - self.last_reset).total_seconds()
        
        return {
            'processed_messages': self.processed_messages,
            'failed_messages': self.failed_messages,
            'success_rate': (
                self.processed_messages / (self.processed_messages + self.failed_messages) * 100
                if (self.processed_messages + self.failed_messages) > 0 else 0
            ),
            'messages_per_second': self.processed_messages / uptime if uptime > 0 else 0,
            'buffered_messages': len(self.message_buffer),
            'active_global_subscribers': len(self.event_subscribers),
            'active_cart_subscribers': sum(len(subs) for subs in self.cart_subscribers.values()),
            'uptime_seconds': uptime,
            'processing_active': self.processing_active
        }
    
    def reset_metrics(self):
        """Reset processing metrics."""
        self.processed_messages = 0
        self.failed_messages = 0
        self.last_reset = datetime.now(timezone.utc)


# Global processor instance
realtime_processor = RealTimeTelemetryProcessor()


def get_realtime_processor() -> RealTimeTelemetryProcessor:
    """Get the real-time telemetry processor instance."""
    return realtime_processor