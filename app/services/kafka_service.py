"""
Kafka Service (Mock) for DY-GOLFCART Management System

Mock implementation of Kafka event publishing service.
Simulates event streaming as specified in Title 2 sequence diagram.
Ready for future replacement with actual Kafka/MSK integration.
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from collections import deque
from threading import Lock
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaProducer:
    """
    Mock Kafka Producer for event publishing.
    Simulates Kafka producer behavior for development/testing.
    
    Future: Replace with confluent-kafka or aiokafka client.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.bootstrap_servers = self.config.get(
            'bootstrap.servers', 
            getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        )
        self.client_id = self.config.get(
            'client.id',
            f"dy-golfcart-producer-{uuid.uuid4().hex[:8]}"
        )
        
        # Mock event storage (in-memory for now)
        self.events_store = deque(maxlen=1000)
        self.lock = Lock()
        self.is_connected = False
        
        # Event listeners for testing
        self.event_listeners = {}
        
        logger.info(f"Mock Kafka Producer initialized: {self.client_id}")
    
    def connect(self) -> bool:
        """Simulate connection to Kafka cluster."""
        try:
            # Simulate connection delay
            import time
            time.sleep(0.1)
            
            self.is_connected = True
            logger.info(f"Mock Kafka Producer connected to {self.bootstrap_servers}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            return False
    
    def send(
        self, 
        topic: str, 
        value: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send event to Kafka topic (mock implementation).
        
        Args:
            topic: Kafka topic name
            value: Event data
            key: Message key for partitioning
            headers: Message headers
            
        Returns:
            Mock future result with metadata
        """
        try:
            if not self.is_connected:
                self.connect()
            
            # Generate event metadata
            event_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc)
            
            # Create event record
            event_record = {
                'event_id': event_id,
                'topic': topic,
                'key': key or event_id,
                'value': value,
                'headers': headers or {},
                'timestamp': timestamp.isoformat(),
                'partition': 0,  # Mock partition
                'offset': len(self.events_store)  # Mock offset
            }
            
            # Store event
            with self.lock:
                self.events_store.append(event_record)
                
                # Notify listeners (for testing)
                if topic in self.event_listeners:
                    for listener in self.event_listeners[topic]:
                        try:
                            listener(event_record)
                        except Exception as e:
                            logger.warning(f"Event listener error: {e}")
            
            logger.debug(f"Event published to {topic}: {event_id}")
            
            # Return mock future result
            return MockFuture(event_record)
            
        except Exception as e:
            logger.error(f"Failed to send event to {topic}: {e}")
            raise Exception(f"Kafka send error: {str(e)}")
    
    def flush(self, timeout: Optional[float] = None) -> None:
        """Flush pending events (no-op for mock)."""
        logger.debug("Mock flush called")
    
    def close(self) -> None:
        """Close producer connection."""
        self.is_connected = False
        logger.info("Mock Kafka Producer closed")
    
    def add_event_listener(self, topic: str, callback: Callable) -> None:
        """Add event listener for testing purposes."""
        if topic not in self.event_listeners:
            self.event_listeners[topic] = []
        self.event_listeners[topic].append(callback)
    
    def get_events(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get stored events for testing/debugging."""
        with self.lock:
            if topic:
                return [e for e in self.events_store if e['topic'] == topic]
            return list(self.events_store)


class MockFuture:
    """Mock Future object for Kafka send operations."""
    
    def __init__(self, result: Dict[str, Any]):
        self.result = result
        self._exception = None
    
    def get(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Get the result of the send operation."""
        if self._exception:
            raise self._exception
        return {
            'topic': self.result['topic'],
            'partition': self.result['partition'],
            'offset': self.result['offset']
        }
    
    def exception(self) -> Optional[Exception]:
        """Get any exception from the operation."""
        return self._exception


class EventPublisher:
    """
    High-level event publisher for DY-GOLFCART events.
    Implements the event publishing from Title 2 sequence diagram.
    """
    
    # Event topics as per sequence diagrams
    TOPICS = {
        'CART_REGISTERED': 'event.cart.registered',
        'CART_ASSIGNED': 'event.cart.assigned',
        'CART_STATUS': 'telemetry.vehicle.status',
        'CART_TELEMETRY': 'telemetry.vehicle.data',
        'CART_COMMAND': 'command.vehicle.control',
        'GEOFENCE_ALERT': 'event.geofence.alert',
        'MAINTENANCE_EVENT': 'event.maintenance.required'
    }
    
    def __init__(self):
        self.producer = KafkaProducer({
            'client.id': 'dy-golfcart-event-publisher'
        })
        self.producer.connect()
    
    def publish_cart_registered(
        self, 
        cart_id: str,
        serial_number: str,
        cart_model_id: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Publish CartRegistered event as per Title 2 sequence.
        
        Args:
            cart_id: Cart UUID
            serial_number: Cart serial number
            cart_model_id: Cart model ID
            additional_data: Additional event data
            
        Returns:
            True if published successfully
        """
        try:
            event = {
                'event_type': 'CartRegistered',
                'cart_id': cart_id,
                'serial_number': serial_number,
                'cart_model_id': cart_model_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': additional_data or {}
            }
            
            result = self.producer.send(
                self.TOPICS['CART_REGISTERED'],
                value=event,
                key=cart_id
            )
            
            logger.info(f"CartRegistered event published for {serial_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish CartRegistered event: {e}")
            return False
    
    def publish_cart_assigned(
        self,
        cart_id: str,
        golf_course_id: str,
        cart_number: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Publish CartAssigned event as per Title 2 sequence.
        
        Args:
            cart_id: Cart UUID
            golf_course_id: Golf course UUID
            cart_number: Assigned cart number
            additional_data: Additional event data
            
        Returns:
            True if published successfully
        """
        try:
            event = {
                'event_type': 'CartAssigned',
                'cart_id': cart_id,
                'golf_course_id': golf_course_id,
                'cart_number': cart_number,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': additional_data or {}
            }
            
            result = self.producer.send(
                self.TOPICS['CART_ASSIGNED'],
                value=event,
                key=cart_id
            )
            
            logger.info(f"CartAssigned event published for cart {cart_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish CartAssigned event: {e}")
            return False
    
    def publish_cart_status(
        self,
        cart_id: str,
        status: str,
        position: Optional[Dict[str, float]] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Publish cart status update event.
        
        Args:
            cart_id: Cart UUID
            status: Cart status (IDLE, RUNNING, etc.)
            position: Current position (lat, lng)
            additional_data: Additional status data
            
        Returns:
            True if published successfully
        """
        try:
            event = {
                'event_type': 'CartStatusUpdate',
                'cart_id': cart_id,
                'status': status,
                'position': position,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': additional_data or {}
            }
            
            result = self.producer.send(
                self.TOPICS['CART_STATUS'],
                value=event,
                key=cart_id
            )
            
            logger.debug(f"Cart status update published for {cart_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish cart status: {e}")
            return False
    
    def publish_telemetry(
        self,
        cart_id: str,
        telemetry_data: Dict[str, Any]
    ) -> bool:
        """
        Publish cart telemetry data.
        
        Args:
            cart_id: Cart UUID
            telemetry_data: Telemetry measurements
            
        Returns:
            True if published successfully
        """
        try:
            event = {
                'event_type': 'Telemetry',
                'cart_id': cart_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': telemetry_data
            }
            
            result = self.producer.send(
                self.TOPICS['CART_TELEMETRY'],
                value=event,
                key=cart_id
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish telemetry: {e}")
            return False
    
    def get_published_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get published events for testing/debugging.
        
        Args:
            event_type: Filter by event type (e.g., 'CART_REGISTERED')
            
        Returns:
            List of published events
        """
        if event_type and event_type in self.TOPICS:
            topic = self.TOPICS[event_type]
            return self.producer.get_events(topic)
        return self.producer.get_events()
    
    def close(self):
        """Close the event publisher."""
        self.producer.close()


# Global instances
kafka_producer = None
event_publisher = None


def get_kafka_producer() -> KafkaProducer:
    """Get or create Kafka producer instance."""
    global kafka_producer
    if kafka_producer is None:
        kafka_producer = KafkaProducer()
        kafka_producer.connect()
    return kafka_producer


def get_event_publisher() -> EventPublisher:
    """Get or create event publisher instance."""
    global event_publisher
    if event_publisher is None:
        event_publisher = EventPublisher()
    return event_publisher


# Async support for future implementation
async def publish_event_async(
    topic: str,
    event: Dict[str, Any],
    key: Optional[str] = None
) -> bool:
    """
    Async event publishing (placeholder for future implementation).
    
    Args:
        topic: Kafka topic
        event: Event data
        key: Message key
        
    Returns:
        True if published successfully
    """
    # For now, use sync producer
    producer = get_kafka_producer()
    try:
        result = producer.send(topic, event, key)
        return True
    except Exception as e:
        logger.error(f"Async publish failed: {e}")
        return False