"""
WebSocket endpoints for real-time telemetry and event streaming.
"""
import json
import asyncio
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_websocket_user, get_current_user, AuthContext
from app.models import GolfCart, GolfCourse
from app.services import get_realtime_processor

logger = logging.getLogger(__name__)

router = APIRouter()


class WebSocketManager:
    """
    Manages WebSocket connections for real-time telemetry streaming.
    
    Features:
    - Connection management with authentication
    - Subscription management (global, cart-specific, golf course-specific)
    - Message routing and filtering
    - Connection health monitoring
    - Automatic cleanup of dead connections
    """
    
    def __init__(self):
        # Connection storage
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_auth: Dict[str, AuthContext] = {}
        
        # Subscription management
        self.global_subscribers: Set[str] = set()
        self.cart_subscribers: Dict[str, Set[str]] = {}  # cart_id -> connection_ids
        self.golf_course_subscribers: Dict[str, Set[str]] = {}  # golf_course_id -> connection_ids
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Health monitoring
        self.last_ping: Dict[str, datetime] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, auth_context: AuthContext):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        self.active_connections[connection_id] = websocket
        self.connection_auth[connection_id] = auth_context
        self.connection_metadata[connection_id] = {
            "connected_at": datetime.utcnow(),
            "user_type": auth_context.user_type,
            "user_id": auth_context.user_id,
            "golf_course_id": auth_context.golf_course_id,
            "subscriptions": []
        }
        self.last_ping[connection_id] = datetime.utcnow()
        
        logger.info(f"WebSocket connected: {connection_id} (user: {auth_context.user_type})")
    
    async def disconnect(self, connection_id: str):
        """Disconnect and cleanup a WebSocket connection."""
        # Remove from all subscriptions
        self.global_subscribers.discard(connection_id)
        
        for cart_subs in self.cart_subscribers.values():
            cart_subs.discard(connection_id)
        
        for course_subs in self.golf_course_subscribers.values():
            course_subs.discard(connection_id)
        
        # Clean up empty subscription sets
        self.cart_subscribers = {k: v for k, v in self.cart_subscribers.items() if v}
        self.golf_course_subscribers = {k: v for k, v in self.golf_course_subscribers.items() if v}
        
        # Remove connection data
        self.active_connections.pop(connection_id, None)
        self.connection_auth.pop(connection_id, None)
        self.connection_metadata.pop(connection_id, None)
        self.last_ping.pop(connection_id, None)
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def subscribe_global(self, connection_id: str):
        """Subscribe connection to global telemetry events."""
        if connection_id in self.active_connections:
            self.global_subscribers.add(connection_id)
            self.connection_metadata[connection_id]["subscriptions"].append("global")
            logger.debug(f"Connection {connection_id} subscribed to global events")
    
    async def subscribe_cart(self, connection_id: str, cart_id: str, db: Session):
        """Subscribe connection to specific cart events."""
        if connection_id not in self.active_connections:
            return False
        
        auth_context = self.connection_auth[connection_id]
        
        # Verify cart access
        cart = db.query(GolfCart).filter(GolfCart.id == cart_id).first()
        if not cart:
            return False
        
        # Check permissions
        if (auth_context.user_type == "golf_course" and 
            cart.golf_course_id != auth_context.golf_course_id):
            return False
        
        # Add subscription
        if cart_id not in self.cart_subscribers:
            self.cart_subscribers[cart_id] = set()
        
        self.cart_subscribers[cart_id].add(connection_id)
        self.connection_metadata[connection_id]["subscriptions"].append(f"cart:{cart_id}")
        
        logger.debug(f"Connection {connection_id} subscribed to cart {cart_id}")
        return True
    
    async def subscribe_golf_course(self, connection_id: str, golf_course_id: str, db: Session):
        """Subscribe connection to golf course events."""
        if connection_id not in self.active_connections:
            return False
        
        auth_context = self.connection_auth[connection_id]
        
        # Verify golf course access
        if (auth_context.user_type == "golf_course" and 
            auth_context.golf_course_id != golf_course_id):
            return False
        
        golf_course = db.query(GolfCourse).filter(GolfCourse.id == golf_course_id).first()
        if not golf_course:
            return False
        
        # Add subscription
        if golf_course_id not in self.golf_course_subscribers:
            self.golf_course_subscribers[golf_course_id] = set()
        
        self.golf_course_subscribers[golf_course_id].add(connection_id)
        self.connection_metadata[connection_id]["subscriptions"].append(f"golf_course:{golf_course_id}")
        
        logger.debug(f"Connection {connection_id} subscribed to golf course {golf_course_id}")
        return True
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        """Send message to specific connection."""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
                self.last_ping[connection_id] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                await self.disconnect(connection_id)
    
    async def broadcast_global(self, message: Dict[str, Any]):
        """Broadcast message to all global subscribers."""
        if not self.global_subscribers:
            return
        
        disconnected = []
        for connection_id in self.global_subscribers:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
                self.last_ping[connection_id] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)
    
    async def broadcast_to_cart_subscribers(self, cart_id: str, message: Dict[str, Any]):
        """Broadcast message to cart subscribers."""
        if cart_id not in self.cart_subscribers:
            return
        
        disconnected = []
        for connection_id in self.cart_subscribers[cart_id]:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
                self.last_ping[connection_id] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error broadcasting to cart subscriber {connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)
    
    async def broadcast_to_golf_course_subscribers(self, golf_course_id: str, message: Dict[str, Any]):
        """Broadcast message to golf course subscribers."""
        if golf_course_id not in self.golf_course_subscribers:
            return
        
        disconnected = []
        for connection_id in self.golf_course_subscribers[golf_course_id]:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
                self.last_ping[connection_id] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error broadcasting to golf course subscriber {connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "global_subscribers": len(self.global_subscribers),
            "cart_subscriptions": sum(len(subs) for subs in self.cart_subscribers.values()),
            "golf_course_subscriptions": sum(len(subs) for subs in self.golf_course_subscribers.values()),
            "connections_by_type": {
                user_type: sum(
                    1 for meta in self.connection_metadata.values() 
                    if meta["user_type"] == user_type
                )
                for user_type in ["manufacturer", "golf_course", "cart_system"]
            }
        }


# Global WebSocket manager instance
ws_manager = WebSocketManager()


class TelemetryStreamHandler:
    """Handler for streaming telemetry data to WebSocket clients."""
    
    def __init__(self, manager: WebSocketManager):
        self.manager = manager
        self.processor = get_realtime_processor()
        self._registered = False
    
    async def initialize(self):
        """Initialize the stream handler and register with telemetry processor."""
        if not self._registered:
            # Register as subscriber to real-time processor
            self.processor.subscribe_to_events(self._handle_telemetry_message)
            self._registered = True
            logger.info("Telemetry stream handler initialized")
    
    async def _handle_telemetry_message(self, message: Dict[str, Any]):
        """Handle incoming telemetry message and route to appropriate subscribers."""
        try:
            message_type = message.get("type")
            cart_id = message.get("cart_id")
            cart_serial = message.get("cart_serial")
            
            # Enhance message with timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.utcnow().isoformat()
            
            # Broadcast to global subscribers
            await self.manager.broadcast_global(message)
            
            # Broadcast to cart-specific subscribers
            if cart_id:
                await self.manager.broadcast_to_cart_subscribers(cart_id, message)
            elif cart_serial:
                # If we only have serial, we'd need to look up the cart_id
                # For now, use serial as identifier
                await self.manager.broadcast_to_cart_subscribers(cart_serial, message)
            
            logger.debug(f"Streamed {message_type} message for cart {cart_id or cart_serial}")
            
        except Exception as e:
            logger.error(f"Error handling telemetry stream message: {e}")


# Global stream handler
stream_handler = TelemetryStreamHandler(ws_manager)


@router.websocket("/stream")
async def telemetry_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time telemetry streaming.
    
    Query Parameters:
    - token: JWT authentication token
    
    Message Types:
    - subscribe: Subscribe to telemetry streams
    - ping: Keep-alive ping
    - unsubscribe: Unsubscribe from streams
    
    Subscription Types:
    - global: All telemetry events (manufacturer only)
    - cart:{cart_id}: Specific cart events
    - golf_course:{golf_course_id}: All carts in golf course
    """
    # Authenticate WebSocket connection
    try:
        auth_context = await get_websocket_user(token, db)
    except Exception as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    connection_id = f"{auth_context.user_type}_{auth_context.user_id}_{datetime.utcnow().timestamp()}"
    
    # Initialize stream handler if needed
    await stream_handler.initialize()
    
    try:
        await ws_manager.connect(websocket, connection_id, auth_context)
        
        # Send connection confirmation
        await ws_manager.send_personal_message({
            "type": "connection_established",
            "connection_id": connection_id,
            "user_type": auth_context.user_type,
            "timestamp": datetime.utcnow().isoformat(),
            "available_subscriptions": {
                "global": auth_context.user_type == "manufacturer",
                "cart_specific": True,
                "golf_course": auth_context.golf_course_id is not None or auth_context.user_type == "manufacturer"
            }
        }, connection_id)
        
        # Message handling loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                
                if message_type == "ping":
                    # Handle ping/pong for keep-alive
                    await ws_manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }, connection_id)
                
                elif message_type == "subscribe":
                    # Handle subscription requests
                    subscription_type = message.get("subscription_type")
                    
                    if subscription_type == "global":
                        if auth_context.user_type == "manufacturer":
                            await ws_manager.subscribe_global(connection_id)
                            await ws_manager.send_personal_message({
                                "type": "subscription_confirmed",
                                "subscription": "global",
                                "timestamp": datetime.utcnow().isoformat()
                            }, connection_id)
                        else:
                            await ws_manager.send_personal_message({
                                "type": "subscription_denied",
                                "subscription": "global",
                                "reason": "Insufficient permissions",
                                "timestamp": datetime.utcnow().isoformat()
                            }, connection_id)
                    
                    elif subscription_type == "cart":
                        cart_id = message.get("cart_id")
                        if cart_id:
                            success = await ws_manager.subscribe_cart(connection_id, cart_id, db)
                            if success:
                                await ws_manager.send_personal_message({
                                    "type": "subscription_confirmed",
                                    "subscription": f"cart:{cart_id}",
                                    "timestamp": datetime.utcnow().isoformat()
                                }, connection_id)
                            else:
                                await ws_manager.send_personal_message({
                                    "type": "subscription_denied",
                                    "subscription": f"cart:{cart_id}",
                                    "reason": "Cart not found or access denied",
                                    "timestamp": datetime.utcnow().isoformat()
                                }, connection_id)
                    
                    elif subscription_type == "golf_course":
                        golf_course_id = message.get("golf_course_id")
                        if golf_course_id:
                            success = await ws_manager.subscribe_golf_course(connection_id, golf_course_id, db)
                            if success:
                                await ws_manager.send_personal_message({
                                    "type": "subscription_confirmed",
                                    "subscription": f"golf_course:{golf_course_id}",
                                    "timestamp": datetime.utcnow().isoformat()
                                }, connection_id)
                            else:
                                await ws_manager.send_personal_message({
                                    "type": "subscription_denied",
                                    "subscription": f"golf_course:{golf_course_id}",
                                    "reason": "Golf course not found or access denied",
                                    "timestamp": datetime.utcnow().isoformat()
                                }, connection_id)
                
                elif message_type == "get_stats":
                    # Send connection statistics (manufacturer only)
                    if auth_context.user_type == "manufacturer":
                        stats = ws_manager.get_connection_stats()
                        await ws_manager.send_personal_message({
                            "type": "connection_stats",
                            "stats": stats,
                            "timestamp": datetime.utcnow().isoformat()
                        }, connection_id)
                
                else:
                    # Unknown message type
                    await ws_manager.send_personal_message({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    }, connection_id)
                
            except json.JSONDecodeError:
                await ws_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON message",
                    "timestamp": datetime.utcnow().isoformat()
                }, connection_id)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected normally: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
    finally:
        await ws_manager.disconnect(connection_id)


@router.get("/stream/stats")
async def get_websocket_stats(
    auth_context: AuthContext = Depends(get_current_user)
):
    """Get WebSocket connection statistics (manufacturer only)."""
    if auth_context.user_type != "manufacturer":
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ws_manager.get_connection_stats()


# Initialize the stream handler on module import
@router.on_event("startup")
async def initialize_websocket_streaming():
    """Initialize WebSocket streaming on startup."""
    try:
        await stream_handler.initialize()
        logger.info("WebSocket telemetry streaming initialized")
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket streaming: {e}")