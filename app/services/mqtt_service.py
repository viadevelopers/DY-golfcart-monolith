"""
MQTT Service for DY-GOLFCART Cart Communication

Event-driven MQTT client service for real-time communication with golf carts.
Handles cart telemetry, status updates, configuration synchronization, and commands.
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from contextlib import asynccontextmanager

import paho.mqtt.client as mqtt
from paho.mqtt.client import Client

from app.core.config import settings

logger = logging.getLogger(__name__)


class MQTTClient:
    """
    MQTT Client for cart communication with event-driven architecture.
    
    Features:
    - Automatic reconnection with exponential backoff
    - Topic-based message routing
    - Cart configuration synchronization
    - Real-time telemetry processing
    - Command publishing to carts
    """
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.connected = False
        self.message_handlers: Dict[str, List[Callable]] = {}
        self._connection_attempts = 0
        self._max_reconnect_delay = 300  # 5 minutes
        
    async def initialize(self):
        """Initialize MQTT client with configuration."""
        if not settings.MQTT_ENABLED:
            logger.info("MQTT is disabled, skipping initialization")
            return
            
        try:
            # Create MQTT client instance
            self.client = mqtt.Client(
                client_id=settings.MQTT_CLIENT_ID,
                protocol=mqtt.MQTTv311
            )
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_subscribe = self._on_subscribe
            self.client.on_publish = self._on_publish
            
            # Configure authentication
            if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
                self.client.username_pw_set(
                    settings.MQTT_USERNAME, 
                    settings.MQTT_PASSWORD
                )
            
            # Configure TLS if enabled
            if settings.MQTT_USE_TLS:
                self.client.tls_set()
            
            # Set keep alive
            self.client.keepalive = settings.MQTT_KEEPALIVE
            
            logger.info("MQTT client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MQTT client: {e}")
            raise
    
    async def connect(self):
        """Connect to MQTT broker with retry logic."""
        if not settings.MQTT_ENABLED or not self.client:
            logger.info("MQTT connection skipped (disabled or not initialized)")
            return False
            
        try:
            logger.info(f"Connecting to MQTT broker at {settings.MQTT_BROKER_URL}:{settings.MQTT_PORT}")
            
            # Attempt connection
            result = self.client.connect(
                settings.MQTT_BROKER_URL,
                settings.MQTT_PORT,
                settings.MQTT_KEEPALIVE
            )
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                # Start the network loop
                self.client.loop_start()
                logger.info("MQTT connection initiated")
                return True
            else:
                logger.error(f"MQTT connection failed with code: {result}")
                return False
                
        except Exception as e:
            logger.error(f"MQTT connection error: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client and self.connected:
            try:
                self.client.loop_stop()
                self.client.disconnect()
                self.connected = False
                logger.info("MQTT client disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting MQTT client: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when client connects to MQTT broker."""
        if rc == 0:
            self.connected = True
            self._connection_attempts = 0
            logger.info("Successfully connected to MQTT broker")
            
            # Subscribe to cart topics
            self._subscribe_to_cart_topics()
            
        else:
            self.connected = False
            logger.error(f"MQTT connection failed with code {rc}")
            
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when client disconnects from MQTT broker."""
        self.connected = False
        if rc != 0:
            logger.warning(f"MQTT client disconnected unexpectedly (code: {rc})")
            # Auto-reconnect will be handled by the client
        else:
            logger.info("MQTT client disconnected")
    
    def _on_message(self, client, userdata, message):
        """Callback for when a message is received."""
        try:
            topic = message.topic
            payload = json.loads(message.payload.decode())
            
            logger.debug(f"Received MQTT message on topic {topic}: {payload}")
            
            # Route message to registered handlers
            self._route_message(topic, payload)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in MQTT message: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback for when subscription is successful."""
        logger.debug(f"Subscription successful with QoS: {granted_qos}")
    
    def _on_publish(self, client, userdata, mid):
        """Callback for when message is published."""
        logger.debug(f"Message published successfully (mid: {mid})")
    
    def _subscribe_to_cart_topics(self):
        """Subscribe to cart-related MQTT topics."""
        if not self.client:
            return
            
        # Subscribe to telemetry topics from all carts
        telemetry_topic = f"{settings.MQTT_TOPIC_PREFIX}/cart/+/telemetry"
        self.client.subscribe(telemetry_topic, settings.MQTT_QOS)
        
        # Subscribe to status topics from all carts  
        status_topic = f"{settings.MQTT_TOPIC_PREFIX}/cart/+/status"
        self.client.subscribe(status_topic, settings.MQTT_QOS)
        
        # Subscribe to event topics
        event_topic = f"{settings.MQTT_TOPIC_PREFIX}/events/+"
        self.client.subscribe(event_topic, settings.MQTT_QOS)
        
        logger.info("Subscribed to cart MQTT topics")
    
    def _route_message(self, topic: str, payload: Dict[str, Any]):
        """Route incoming messages to registered handlers."""
        # Find matching handlers for this topic
        for topic_pattern, handlers in self.message_handlers.items():
            if self._topic_matches(topic, topic_pattern):
                for handler in handlers:
                    try:
                        handler(topic, payload)
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern (supports + wildcard)."""
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        if len(topic_parts) != len(pattern_parts):
            return False
            
        for topic_part, pattern_part in zip(topic_parts, pattern_parts):
            if pattern_part != '+' and pattern_part != topic_part:
                return False
                
        return True
    
    def add_message_handler(self, topic_pattern: str, handler: Callable):
        """Add a message handler for a topic pattern."""
        if topic_pattern not in self.message_handlers:
            self.message_handlers[topic_pattern] = []
        self.message_handlers[topic_pattern].append(handler)
        logger.debug(f"Added message handler for topic pattern: {topic_pattern}")
    
    def publish(self, topic: str, payload: Dict[str, Any], retain: bool = False) -> bool:
        """
        Publish a message to MQTT topic.
        
        Args:
            topic: MQTT topic to publish to
            payload: Message payload (will be JSON encoded)
            retain: Whether to retain the message
            
        Returns:
            bool: True if message was queued for publishing
        """
        if not self.client or not self.connected:
            logger.warning(f"Cannot publish to {topic}: MQTT not connected")
            return False
            
        try:
            json_payload = json.dumps(payload)
            result = self.client.publish(
                topic, 
                json_payload, 
                qos=settings.MQTT_QOS,
                retain=retain
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published message to {topic}")
                return True
            else:
                logger.error(f"Failed to publish to {topic}: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing to {topic}: {e}")
            return False
    
    def publish_cart_config(self, cart_serial: str, config: Dict[str, Any]) -> bool:
        """
        Publish configuration to a specific cart.
        
        Args:
            cart_serial: Cart serial number
            config: Configuration data
            
        Returns:
            bool: True if published successfully
        """
        topic = settings.MQTT_CONFIG_TOPIC.format(
            prefix=settings.MQTT_TOPIC_PREFIX,
            cart_id=cart_serial
        )
        
        # Add timestamp to config
        config_with_timestamp = {
            **config,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return self.publish(topic, config_with_timestamp)
    
    def publish_cart_command(self, cart_serial: str, command: Dict[str, Any]) -> bool:
        """
        Publish command to a specific cart.
        
        Args:
            cart_serial: Cart serial number
            command: Command data
            
        Returns:
            bool: True if published successfully
        """
        topic = settings.MQTT_COMMAND_TOPIC.format(
            prefix=settings.MQTT_TOPIC_PREFIX,
            cart_id=cart_serial
        )
        
        # Add timestamp to command
        command_with_timestamp = {
            **command,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return self.publish(topic, command_with_timestamp)
    
    def publish_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Publish system event.
        
        Args:
            event_type: Type of event (e.g., 'alert', 'status')
            event_data: Event data
            
        Returns:
            bool: True if published successfully
        """
        topic = settings.MQTT_EVENT_TOPIC.format(
            prefix=settings.MQTT_TOPIC_PREFIX,
            event_type=event_type
        )
        
        # Add timestamp to event
        event_with_timestamp = {
            **event_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return self.publish(topic, event_with_timestamp)


# Global MQTT service instance
mqtt_service = MQTTClient()


@asynccontextmanager
async def get_mqtt_service():
    """
    Context manager for MQTT service.
    Ensures proper initialization and cleanup.
    """
    if not mqtt_service.client:
        await mqtt_service.initialize()
        
    if not mqtt_service.connected:
        await mqtt_service.connect()
        
    try:
        yield mqtt_service
    finally:
        # Keep connection alive for reuse
        # Only disconnect on application shutdown
        pass


async def initialize_mqtt_service():
    """Initialize MQTT service during application startup."""
    try:
        await mqtt_service.initialize()
        if settings.MQTT_ENABLED:
            await mqtt_service.connect()
        logger.info("MQTT service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MQTT service: {e}")
        # Don't raise exception to prevent app startup failure
        

async def shutdown_mqtt_service():
    """Shutdown MQTT service during application shutdown."""
    try:
        await mqtt_service.disconnect()
        logger.info("MQTT service shutdown complete")
    except Exception as e:
        logger.error(f"Error during MQTT service shutdown: {e}")


def create_cart_sync_config(golf_course, cart) -> Dict[str, Any]:
    """
    Create configuration data for cart synchronization.
    
    Args:
        golf_course: Golf course model instance
        cart: Cart model instance
        
    Returns:
        Dict containing cart configuration
    """
    config = {
        "command": "update_map",
        "golf_course_id": str(golf_course.id),
        "golf_course_name": golf_course.name,
        "speed_limit": golf_course.cart_speed_limit
    }
    
    # Add map URL if available
    if golf_course.maps:
        active_map = next((m for m in golf_course.maps if m.is_active), None)
        if active_map:
            config["map_url"] = active_map.static_image_url
    
    # Add routes
    if golf_course.routes:
        config["routes"] = [
            {
                "id": str(route.id),
                "name": route.name,
                "type": route.route_type,
                "speed_limit": route.speed_limit,
                "is_active": route.is_active,
                "is_preferred": route.is_preferred
            }
            for route in golf_course.routes if route.is_active
        ]
    
    # Add geofences
    if golf_course.geofences:
        config["geofences"] = [
            {
                "id": str(fence.id),
                "name": fence.name,
                "type": fence.fence_type,
                "speed_limit": fence.speed_limit,
                "alert_on_entry": fence.alert_on_entry,
                "alert_on_exit": fence.alert_on_exit,
                "auto_stop": fence.auto_stop,
                "severity": fence.severity,
                "is_active": fence.is_active
            }
            for fence in golf_course.geofences if fence.is_active
        ]
    
    return config