"""
Telemetry Service for DY-GOLFCART System

Handles cart telemetry data processing, aggregation, and event generation.
Supports real-time telemetry ingestion, data validation, and dashboard analytics.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc, text
from geoalchemy2 import WKTElement
from geoalchemy2.functions import ST_Distance, ST_Within

from app.core.database import get_db_context
from app.models import CartTelemetry, CartEvent, GolfCart, GolfCourse, Geofence
from app.services.kafka_service import get_event_publisher

logger = logging.getLogger(__name__)


class TelemetryProcessor:
    """
    Core telemetry data processor with validation, event generation, and storage.
    
    Features:
    - Real-time telemetry data validation and normalization
    - Automatic event generation based on telemetry analysis
    - Geofence violation detection with spatial queries
    - Battery monitoring with configurable thresholds
    - Performance metrics calculation and anomaly detection
    """
    
    def __init__(self):
        self.event_publisher = get_event_publisher()
        
        # Telemetry validation thresholds
        self.BATTERY_LOW_THRESHOLD = 20  # %
        self.BATTERY_CRITICAL_THRESHOLD = 10  # %
        self.SPEED_LIMIT_DEFAULT = 25.0  # km/h
        self.GPS_ACCURACY_THRESHOLD = 10.0  # meters HDOP
        
        # Event generation settings
        self.EVENT_COOLDOWN = 300  # 5 minutes between similar events
        
    async def process_telemetry_message(self, cart_id: str, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming telemetry message from MQTT.
        
        Args:
            cart_id: Cart identifier
            telemetry_data: Raw telemetry data from cart
            
        Returns:
            Processing result with status and generated events
        """
        try:
            # Validate and normalize telemetry data
            validated_data = self._validate_telemetry(cart_id, telemetry_data)
            if not validated_data:
                return {"status": "error", "message": "Invalid telemetry data"}
            
            # Store telemetry in database
            with get_db_context() as db:
                # Check if cart exists
                cart = db.query(GolfCart).filter(GolfCart.id == cart_id).first()
                if not cart:
                    return {"status": "error", "message": f"Cart {cart_id} not found"}
                
                # Create telemetry record
                telemetry = CartTelemetry(
                    cart_id=cart_id,
                    timestamp=datetime.now(timezone.utc),
                    position=WKTElement(f"POINT({validated_data['longitude']} {validated_data['latitude']})", srid=4326),
                    altitude_meters=validated_data.get('altitude'),
                    heading=validated_data.get('heading'),
                    speed=validated_data.get('speed'),
                    acceleration=validated_data.get('acceleration'),
                    battery_level=validated_data.get('battery_level'),
                    battery_voltage=validated_data.get('battery_voltage'),
                    battery_current=validated_data.get('battery_current'),
                    battery_temperature=validated_data.get('battery_temperature'),
                    charging_status=validated_data.get('charging_status', False),
                    engine_status=validated_data.get('engine_status', 'UNKNOWN'),
                    brake_status=validated_data.get('brake_status', False),
                    emergency_stop=validated_data.get('emergency_stop', False),
                    external_temperature=validated_data.get('external_temperature'),
                    gps_satellites=validated_data.get('gps_satellites'),
                    gps_hdop=validated_data.get('gps_hdop'),
                    sensor_data=validated_data.get('sensor_data', {}),
                    cpu_usage=validated_data.get('cpu_usage'),
                    memory_usage=validated_data.get('memory_usage'),
                    disk_usage=validated_data.get('disk_usage')
                )
                
                db.add(telemetry)
                
                # Generate events based on telemetry analysis
                generated_events = await self._analyze_and_generate_events(db, cart, telemetry, validated_data)
                
                # Update cart status
                cart.last_ping = telemetry.timestamp
                if validated_data.get('ip_address'):
                    cart.ip_address = validated_data['ip_address']
                
                result = {
                    "status": "success",
                    "telemetry_id": str(telemetry.id),
                    "events_generated": len(generated_events),
                    "events": generated_events
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Error processing telemetry for cart {cart_id}: {e}")
            return {"status": "error", "message": str(e)}
    
    def _validate_telemetry(self, cart_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and normalize telemetry data."""
        try:
            validated = {}
            
            # Required fields
            if 'latitude' not in data or 'longitude' not in data:
                logger.warning(f"Missing GPS coordinates for cart {cart_id}")
                return None
                
            lat, lng = float(data['latitude']), float(data['longitude'])
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                logger.warning(f"Invalid GPS coordinates for cart {cart_id}: {lat}, {lng}")
                return None
                
            validated['latitude'] = lat
            validated['longitude'] = lng
            
            # Optional numeric fields with validation
            numeric_fields = {
                'altitude': (-1000, 10000),
                'heading': (0, 359.99),
                'speed': (0, 100),
                'acceleration': (-20, 20),
                'battery_level': (0, 100),
                'battery_voltage': (0, 100),
                'battery_current': (-100, 100),
                'battery_temperature': (-50, 100),
                'external_temperature': (-50, 100),
                'gps_satellites': (0, 50),
                'gps_hdop': (0, 100),
                'cpu_usage': (0, 100),
                'memory_usage': (0, 100),
                'disk_usage': (0, 100)
            }
            
            for field, (min_val, max_val) in numeric_fields.items():
                if field in data and data[field] is not None:
                    try:
                        val = float(data[field])
                        if min_val <= val <= max_val:
                            validated[field] = val
                        else:
                            logger.warning(f"Value out of range for {field}: {val}")
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid numeric value for {field}: {data[field]}")
            
            # Boolean fields
            boolean_fields = ['charging_status', 'brake_status', 'emergency_stop']
            for field in boolean_fields:
                if field in data:
                    validated[field] = bool(data[field])
            
            # String fields
            if 'engine_status' in data:
                status = str(data['engine_status']).upper()
                if status in ['ON', 'OFF', 'ERROR', 'IDLE']:
                    validated['engine_status'] = status
            
            # Additional data
            if 'sensor_data' in data and isinstance(data['sensor_data'], dict):
                validated['sensor_data'] = data['sensor_data']
            
            if 'ip_address' in data:
                validated['ip_address'] = str(data['ip_address'])
            
            return validated
            
        except Exception as e:
            logger.error(f"Error validating telemetry for cart {cart_id}: {e}")
            return None
    
    async def _analyze_and_generate_events(
        self, 
        db: Session, 
        cart: GolfCart, 
        telemetry: CartTelemetry, 
        data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze telemetry and generate appropriate events."""
        events = []
        
        try:
            # Battery level monitoring
            battery_level = data.get('battery_level')
            if battery_level is not None:
                if battery_level <= self.BATTERY_CRITICAL_THRESHOLD:
                    event = await self._create_event_if_needed(
                        db, cart.id, "CRITICAL_BATTERY", "OPERATIONAL", "CRITICAL",
                        "Critical Battery Level",
                        f"Battery level critically low: {battery_level}%",
                        {"battery_level": battery_level, "threshold": self.BATTERY_CRITICAL_THRESHOLD},
                        telemetry.position, telemetry.timestamp
                    )
                    if event:
                        events.append(event)
                elif battery_level <= self.BATTERY_LOW_THRESHOLD:
                    event = await self._create_event_if_needed(
                        db, cart.id, "LOW_BATTERY", "OPERATIONAL", "WARNING",
                        "Low Battery Level",
                        f"Battery level low: {battery_level}%",
                        {"battery_level": battery_level, "threshold": self.BATTERY_LOW_THRESHOLD},
                        telemetry.position, telemetry.timestamp
                    )
                    if event:
                        events.append(event)
            
            # Emergency stop detection
            if data.get('emergency_stop'):
                event = await self._create_event_if_needed(
                    db, cart.id, "EMERGENCY_STOP", "SAFETY", "CRITICAL",
                    "Emergency Stop Activated",
                    "Cart emergency stop has been activated",
                    {"activated_at": telemetry.timestamp.isoformat()},
                    telemetry.position, telemetry.timestamp
                )
                if event:
                    events.append(event)
            
            # Speed violation detection
            speed = data.get('speed')
            if speed is not None and cart.speed_limit_override:
                if speed > cart.speed_limit_override:
                    event = await self._create_event_if_needed(
                        db, cart.id, "SPEED_VIOLATION", "OPERATIONAL", "WARNING",
                        "Speed Limit Exceeded",
                        f"Cart exceeding speed limit: {speed} km/h (limit: {cart.speed_limit_override} km/h)",
                        {"current_speed": speed, "speed_limit": cart.speed_limit_override},
                        telemetry.position, telemetry.timestamp
                    )
                    if event:
                        events.append(event)
            
            # GPS signal quality
            gps_hdop = data.get('gps_hdop')
            if gps_hdop is not None and gps_hdop > self.GPS_ACCURACY_THRESHOLD:
                event = await self._create_event_if_needed(
                    db, cart.id, "GPS_SIGNAL_POOR", "SYSTEM", "WARNING",
                    "Poor GPS Signal Quality",
                    f"GPS accuracy degraded: HDOP {gps_hdop}",
                    {"hdop": gps_hdop, "threshold": self.GPS_ACCURACY_THRESHOLD},
                    telemetry.position, telemetry.timestamp
                )
                if event:
                    events.append(event)
            
            # Geofence violation check (if cart assigned to golf course)
            if cart.golf_course_id:
                geofence_events = await self._check_geofence_violations(
                    db, cart, telemetry.position, telemetry.timestamp
                )
                events.extend(geofence_events)
            
            return events
            
        except Exception as e:
            logger.error(f"Error analyzing telemetry for cart {cart.id}: {e}")
            return events
    
    async def _create_event_if_needed(
        self,
        db: Session,
        cart_id: UUID,
        event_type: str,
        category: str,
        severity: str,
        title: str,
        description: str,
        event_data: Dict[str, Any],
        position: Any,
        timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """Create event if it hasn't been generated recently (cooldown logic)."""
        try:
            # Check for recent similar events (cooldown)
            cooldown_time = timestamp - timedelta(seconds=self.EVENT_COOLDOWN)
            recent_event = db.query(CartEvent).filter(
                and_(
                    CartEvent.cart_id == cart_id,
                    CartEvent.event_type == event_type,
                    CartEvent.timestamp > cooldown_time
                )
            ).first()
            
            if recent_event:
                return None  # Event recently generated, skip
            
            # Create new event
            event = CartEvent(
                cart_id=cart_id,
                event_type=event_type,
                event_category=category,
                severity=severity,
                title=title,
                description=description,
                event_data=event_data,
                position=position,
                timestamp=timestamp
            )
            
            db.add(event)
            
            # Publish event to Kafka
            await self.event_publisher.publish_cart_event(
                cart_id=str(cart_id),
                event_type=event_type,
                severity=severity,
                event_data=event_data
            )
            
            return {
                "event_id": str(event.id),
                "event_type": event_type,
                "severity": severity,
                "title": title
            }
            
        except Exception as e:
            logger.error(f"Error creating event {event_type} for cart {cart_id}: {e}")
            return None
    
    async def _check_geofence_violations(
        self,
        db: Session,
        cart: GolfCart,
        position: Any,
        timestamp: datetime
    ) -> List[Dict[str, Any]]:
        """Check for geofence violations using PostGIS spatial queries."""
        events = []
        
        try:
            # Get geofences for the cart's golf course
            geofences = db.query(Geofence).filter(
                Geofence.golf_course_id == cart.golf_course_id
            ).all()
            
            for geofence in geofences:
                try:
                    # Check if cart position is within geofence
                    is_within = db.query(
                        ST_Within(position, geofence.boundary)
                    ).scalar()
                    
                    if geofence.fence_type == "ALLOWED" and not is_within:
                        # Cart outside allowed area
                        event = await self._create_event_if_needed(
                            db, cart.id, "GEOFENCE_VIOLATION", "OPERATIONAL", "WARNING",
                            f"Outside {geofence.name}",
                            f"Cart has left the allowed area: {geofence.name}",
                            {
                                "geofence_id": str(geofence.id),
                                "geofence_name": geofence.name,
                                "fence_type": geofence.fence_type
                            },
                            position, timestamp
                        )
                        if event:
                            events.append(event)
                    
                    elif geofence.fence_type == "RESTRICTED" and is_within:
                        # Cart in restricted area
                        event = await self._create_event_if_needed(
                            db, cart.id, "GEOFENCE_VIOLATION", "SAFETY", "ERROR",
                            f"Entered {geofence.name}",
                            f"Cart has entered restricted area: {geofence.name}",
                            {
                                "geofence_id": str(geofence.id),
                                "geofence_name": geofence.name,
                                "fence_type": geofence.fence_type
                            },
                            position, timestamp
                        )
                        if event:
                            events.append(event)
                
                except Exception as e:
                    logger.error(f"Error checking geofence {geofence.id}: {e}")
                    continue
            
            return events
            
        except Exception as e:
            logger.error(f"Error checking geofence violations for cart {cart.id}: {e}")
            return []


class TelemetryService:
    """
    High-level telemetry service providing data aggregation and analytics.
    
    Features:
    - Cart status aggregation and dashboard metrics
    - Historical telemetry data queries with optimized indexing
    - Real-time telemetry streaming support
    - Performance analytics and trend analysis
    """
    
    def __init__(self):
        self.processor = TelemetryProcessor()
    
    async def process_telemetry(self, cart_id: str, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process telemetry data through the telemetry processor."""
        return await self.processor.process_telemetry_message(cart_id, telemetry_data)
    
    def get_cart_current_status(self, cart_id: UUID) -> Optional[Dict[str, Any]]:
        """Get current status and latest telemetry for a cart."""
        try:
            with get_db_context() as db:
                # Get latest telemetry
                latest_telemetry = db.query(CartTelemetry).filter(
                    CartTelemetry.cart_id == cart_id
                ).order_by(desc(CartTelemetry.timestamp)).first()
                
                if not latest_telemetry:
                    return None
                
                # Get cart info
                cart = db.query(GolfCart).filter(GolfCart.id == cart_id).first()
                if not cart:
                    return None
                
                # Get recent unresolved events
                recent_events = db.query(CartEvent).filter(
                    and_(
                        CartEvent.cart_id == cart_id,
                        CartEvent.resolved == False,
                        CartEvent.timestamp > (datetime.now(timezone.utc) - timedelta(hours=24))
                    )
                ).order_by(desc(CartEvent.timestamp)).limit(10).all()
                
                return {
                    "cart_id": str(cart_id),
                    "serial_number": cart.serial_number,
                    "cart_number": cart.cart_number,
                    "status": cart.status,
                    "is_online": cart.is_online,
                    "last_ping": latest_telemetry.timestamp.isoformat(),
                    "position": {
                        "latitude": latest_telemetry.coordinates[0] if latest_telemetry.coordinates else None,
                        "longitude": latest_telemetry.coordinates[1] if latest_telemetry.coordinates else None
                    },
                    "telemetry": {
                        "battery_level": latest_telemetry.battery_level,
                        "speed": latest_telemetry.speed,
                        "heading": latest_telemetry.heading,
                        "engine_status": latest_telemetry.engine_status,
                        "charging_status": latest_telemetry.charging_status,
                        "emergency_stop": latest_telemetry.emergency_stop
                    },
                    "active_events": [
                        {
                            "event_id": str(event.id),
                            "event_type": event.event_type,
                            "severity": event.severity,
                            "title": event.title,
                            "timestamp": event.timestamp.isoformat()
                        }
                        for event in recent_events
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting cart status for {cart_id}: {e}")
            return None
    
    def get_golf_course_dashboard(self, golf_course_id: UUID) -> Dict[str, Any]:
        """Get dashboard metrics for a golf course."""
        try:
            with get_db_context() as db:
                # Get all carts for the golf course
                carts = db.query(GolfCart).filter(
                    GolfCart.golf_course_id == golf_course_id
                ).all()
                
                cart_ids = [cart.id for cart in carts]
                
                if not cart_ids:
                    return {
                        "golf_course_id": str(golf_course_id),
                        "total_carts": 0,
                        "online_carts": 0,
                        "active_events": 0,
                        "carts": []
                    }
                
                # Count online carts (pinged within 2 minutes)
                online_threshold = datetime.now(timezone.utc) - timedelta(minutes=2)
                online_count = db.query(func.count(GolfCart.id)).filter(
                    and_(
                        GolfCart.golf_course_id == golf_course_id,
                        GolfCart.last_ping > online_threshold
                    )
                ).scalar() or 0
                
                # Count active unresolved events
                active_events_count = db.query(func.count(CartEvent.id)).filter(
                    and_(
                        CartEvent.cart_id.in_(cart_ids),
                        CartEvent.resolved == False,
                        CartEvent.timestamp > (datetime.now(timezone.utc) - timedelta(hours=24))
                    )
                ).scalar() or 0
                
                # Get cart statuses
                cart_statuses = []
                for cart in carts:
                    status = self.get_cart_current_status(cart.id)
                    if status:
                        cart_statuses.append(status)
                
                return {
                    "golf_course_id": str(golf_course_id),
                    "total_carts": len(carts),
                    "online_carts": online_count,
                    "active_events": active_events_count,
                    "carts": cart_statuses
                }
                
        except Exception as e:
            logger.error(f"Error getting dashboard for golf course {golf_course_id}: {e}")
            return {
                "golf_course_id": str(golf_course_id),
                "total_carts": 0,
                "online_carts": 0,
                "active_events": 0,
                "carts": [],
                "error": str(e)
            }
    
    def get_telemetry_history(
        self, 
        cart_id: UUID, 
        start_time: datetime, 
        end_time: datetime,
        metrics: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get historical telemetry data for a cart with optional metric filtering."""
        try:
            with get_db_context() as db:
                query = db.query(CartTelemetry).filter(
                    and_(
                        CartTelemetry.cart_id == cart_id,
                        CartTelemetry.timestamp >= start_time,
                        CartTelemetry.timestamp <= end_time
                    )
                ).order_by(asc(CartTelemetry.timestamp))
                
                telemetry_records = query.all()
                
                result = []
                for record in telemetry_records:
                    data = {
                        "timestamp": record.timestamp.isoformat(),
                        "position": record.coordinates if record.coordinates else None,
                        "battery_level": record.battery_level,
                        "speed": record.speed,
                        "heading": record.heading,
                        "engine_status": record.engine_status,
                        "charging_status": record.charging_status
                    }
                    
                    # Include specific metrics if requested
                    if metrics:
                        filtered_data = {"timestamp": data["timestamp"]}
                        for metric in metrics:
                            if metric in data:
                                filtered_data[metric] = data[metric]
                            elif hasattr(record, metric):
                                filtered_data[metric] = getattr(record, metric)
                        result.append(filtered_data)
                    else:
                        # Add all available metrics
                        data.update({
                            "altitude": record.altitude_meters,
                            "acceleration": record.acceleration,
                            "battery_voltage": record.battery_voltage,
                            "battery_current": record.battery_current,
                            "battery_temperature": record.battery_temperature,
                            "brake_status": record.brake_status,
                            "emergency_stop": record.emergency_stop,
                            "external_temperature": record.external_temperature,
                            "gps_satellites": record.gps_satellites,
                            "gps_hdop": record.gps_hdop,
                            "cpu_usage": record.cpu_usage,
                            "memory_usage": record.memory_usage,
                            "disk_usage": record.disk_usage
                        })
                        result.append(data)
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting telemetry history for cart {cart_id}: {e}")
            return []
    
    def get_performance_analytics(self, cart_id: UUID, days: int = 7) -> Dict[str, Any]:
        """Get performance analytics for a cart over specified time period."""
        try:
            with get_db_context() as db:
                start_time = datetime.now(timezone.utc) - timedelta(days=days)
                
                # Get aggregated metrics
                metrics = db.query(
                    func.avg(CartTelemetry.battery_level).label('avg_battery'),
                    func.min(CartTelemetry.battery_level).label('min_battery'),
                    func.max(CartTelemetry.battery_level).label('max_battery'),
                    func.avg(CartTelemetry.speed).label('avg_speed'),
                    func.max(CartTelemetry.speed).label('max_speed'),
                    func.count(CartTelemetry.id).label('data_points'),
                    func.avg(CartTelemetry.cpu_usage).label('avg_cpu'),
                    func.avg(CartTelemetry.memory_usage).label('avg_memory'),
                    func.avg(CartTelemetry.disk_usage).label('avg_disk')
                ).filter(
                    and_(
                        CartTelemetry.cart_id == cart_id,
                        CartTelemetry.timestamp >= start_time
                    )
                ).first()
                
                # Calculate uptime (time between first and last ping)
                time_range = db.query(
                    func.min(CartTelemetry.timestamp).label('first_ping'),
                    func.max(CartTelemetry.timestamp).label('last_ping')
                ).filter(
                    and_(
                        CartTelemetry.cart_id == cart_id,
                        CartTelemetry.timestamp >= start_time
                    )
                ).first()
                
                uptime_hours = 0
                if time_range.first_ping and time_range.last_ping:
                    uptime_delta = time_range.last_ping - time_range.first_ping
                    uptime_hours = uptime_delta.total_seconds() / 3600
                
                # Count events by severity
                event_counts = db.query(
                    CartEvent.severity,
                    func.count(CartEvent.id).label('count')
                ).filter(
                    and_(
                        CartEvent.cart_id == cart_id,
                        CartEvent.timestamp >= start_time
                    )
                ).group_by(CartEvent.severity).all()
                
                event_summary = {severity: 0 for severity in ['INFO', 'WARNING', 'ERROR', 'CRITICAL']}
                for severity, count in event_counts:
                    event_summary[severity] = count
                
                # Calculate distance traveled (simplified - sum of point-to-point distances)
                # This is a basic implementation; real distance calculation would need route following
                distance_query = """
                    WITH ordered_points AS (
                        SELECT position, timestamp,
                               LAG(position) OVER (ORDER BY timestamp) as prev_position
                        FROM cart_telemetry 
                        WHERE cart_id = :cart_id 
                        AND timestamp >= :start_time
                        AND position IS NOT NULL
                    )
                    SELECT COALESCE(SUM(ST_Distance(position::geography, prev_position::geography)), 0) as total_distance
                    FROM ordered_points 
                    WHERE prev_position IS NOT NULL
                """
                
                distance_result = db.execute(text(distance_query), {
                    'cart_id': str(cart_id),
                    'start_time': start_time
                }).scalar()
                
                total_distance_km = (distance_result or 0) / 1000.0  # Convert meters to km
                
                return {
                    "cart_id": str(cart_id),
                    "analysis_period_days": days,
                    "data_points": metrics.data_points or 0,
                    "uptime_hours": round(uptime_hours, 2),
                    "battery_analytics": {
                        "average_level": round(metrics.avg_battery or 0, 1),
                        "minimum_level": metrics.min_battery or 0,
                        "maximum_level": metrics.max_battery or 0
                    },
                    "speed_analytics": {
                        "average_speed_kmh": round(metrics.avg_speed or 0, 1),
                        "maximum_speed_kmh": round(metrics.max_speed or 0, 1)
                    },
                    "system_performance": {
                        "average_cpu_usage": round(metrics.avg_cpu or 0, 1),
                        "average_memory_usage": round(metrics.avg_memory or 0, 1),
                        "average_disk_usage": round(metrics.avg_disk or 0, 1)
                    },
                    "distance_traveled_km": round(total_distance_km, 2),
                    "event_summary": event_summary,
                    "total_events": sum(event_summary.values())
                }
                
        except Exception as e:
            logger.error(f"Error getting performance analytics for cart {cart_id}: {e}")
            return {
                "cart_id": str(cart_id),
                "analysis_period_days": days,
                "error": str(e)
            }
    
    def get_fleet_analytics(self, golf_course_id: UUID, days: int = 7) -> Dict[str, Any]:
        """Get fleet-wide analytics for a golf course."""
        try:
            with get_db_context() as db:
                start_time = datetime.now(timezone.utc) - timedelta(days=days)
                
                # Get all carts for the golf course
                cart_ids = db.query(GolfCart.id).filter(
                    GolfCart.golf_course_id == golf_course_id
                ).all()
                
                cart_id_list = [str(cart_id[0]) for cart_id in cart_ids]
                
                if not cart_id_list:
                    return {
                        "golf_course_id": str(golf_course_id),
                        "analysis_period_days": days,
                        "total_carts": 0,
                        "active_carts": 0,
                        "fleet_metrics": {},
                        "top_issues": []
                    }
                
                # Fleet-wide telemetry aggregation
                fleet_metrics = db.query(
                    func.count(func.distinct(CartTelemetry.cart_id)).label('active_carts'),
                    func.avg(CartTelemetry.battery_level).label('avg_battery'),
                    func.avg(CartTelemetry.speed).label('avg_speed'),
                    func.count(CartTelemetry.id).label('total_data_points')
                ).filter(
                    and_(
                        CartTelemetry.cart_id.in_(cart_id_list),
                        CartTelemetry.timestamp >= start_time
                    )
                ).first()
                
                # Top event types across the fleet
                top_events = db.query(
                    CartEvent.event_type,
                    func.count(CartEvent.id).label('count')
                ).filter(
                    and_(
                        CartEvent.cart_id.in_(cart_id_list),
                        CartEvent.timestamp >= start_time,
                        CartEvent.severity.in_(['ERROR', 'CRITICAL'])
                    )
                ).group_by(CartEvent.event_type).order_by(desc(func.count(CartEvent.id))).limit(5).all()
                
                # Cart utilization (carts with data in the period)
                active_carts_count = fleet_metrics.active_carts or 0
                total_carts_count = len(cart_id_list)
                utilization_rate = (active_carts_count / total_carts_count * 100) if total_carts_count > 0 else 0
                
                return {
                    "golf_course_id": str(golf_course_id),
                    "analysis_period_days": days,
                    "total_carts": total_carts_count,
                    "active_carts": active_carts_count,
                    "utilization_rate": round(utilization_rate, 1),
                    "fleet_metrics": {
                        "average_battery_level": round(fleet_metrics.avg_battery or 0, 1),
                        "average_speed_kmh": round(fleet_metrics.avg_speed or 0, 1),
                        "total_data_points": fleet_metrics.total_data_points or 0
                    },
                    "top_issues": [
                        {
                            "event_type": event_type,
                            "count": count,
                            "description": self._get_event_description(event_type)
                        }
                        for event_type, count in top_events
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting fleet analytics for golf course {golf_course_id}: {e}")
            return {
                "golf_course_id": str(golf_course_id),
                "analysis_period_days": days,
                "error": str(e)
            }
    
    def get_battery_trend_analysis(self, cart_id: UUID, hours: int = 24) -> Dict[str, Any]:
        """Get battery level trend analysis for predictive maintenance."""
        try:
            with get_db_context() as db:
                start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
                
                # Get battery level data points
                battery_data = db.query(
                    CartTelemetry.timestamp,
                    CartTelemetry.battery_level,
                    CartTelemetry.charging_status
                ).filter(
                    and_(
                        CartTelemetry.cart_id == cart_id,
                        CartTelemetry.timestamp >= start_time,
                        CartTelemetry.battery_level.isnot(None)
                    )
                ).order_by(asc(CartTelemetry.timestamp)).all()
                
                if len(battery_data) < 2:
                    return {
                        "cart_id": str(cart_id),
                        "analysis_period_hours": hours,
                        "insufficient_data": True
                    }
                
                # Calculate discharge rate (when not charging)
                discharge_periods = []
                charge_periods = []
                current_period = []
                is_charging = None
                
                for timestamp, battery_level, charging_status in battery_data:
                    if is_charging is None:
                        is_charging = charging_status
                        current_period = [(timestamp, battery_level)]
                    elif is_charging == charging_status:
                        current_period.append((timestamp, battery_level))
                    else:
                        # Status changed
                        if len(current_period) >= 2:
                            if is_charging:
                                charge_periods.append(current_period)
                            else:
                                discharge_periods.append(current_period)
                        current_period = [(timestamp, battery_level)]
                        is_charging = charging_status
                
                # Add final period
                if len(current_period) >= 2:
                    if is_charging:
                        charge_periods.append(current_period)
                    else:
                        discharge_periods.append(current_period)
                
                # Calculate average discharge rate
                discharge_rates = []
                for period in discharge_periods:
                    if len(period) >= 2:
                        start_time, start_battery = period[0]
                        end_time, end_battery = period[-1]
                        duration_hours = (end_time - start_time).total_seconds() / 3600
                        if duration_hours > 0 and start_battery > end_battery:
                            rate = (start_battery - end_battery) / duration_hours
                            discharge_rates.append(rate)
                
                avg_discharge_rate = sum(discharge_rates) / len(discharge_rates) if discharge_rates else 0
                
                # Predict time to critical battery level (10%)
                latest_battery = battery_data[-1][1]
                latest_charging = battery_data[-1][2]
                
                time_to_critical = None
                if not latest_charging and avg_discharge_rate > 0 and latest_battery > 10:
                    hours_to_critical = (latest_battery - 10) / avg_discharge_rate
                    time_to_critical = round(hours_to_critical, 1)
                
                return {
                    "cart_id": str(cart_id),
                    "analysis_period_hours": hours,
                    "current_battery_level": latest_battery,
                    "is_charging": latest_charging,
                    "average_discharge_rate_percent_per_hour": round(avg_discharge_rate, 2),
                    "discharge_periods_analyzed": len(discharge_periods),
                    "charge_periods_analyzed": len(charge_periods),
                    "predicted_hours_to_critical": time_to_critical,
                    "battery_health_status": self._assess_battery_health(avg_discharge_rate, latest_battery)
                }
                
        except Exception as e:
            logger.error(f"Error getting battery trend analysis for cart {cart_id}: {e}")
            return {
                "cart_id": str(cart_id),
                "analysis_period_hours": hours,
                "error": str(e)
            }
    
    def _get_event_description(self, event_type: str) -> str:
        """Get human-readable description for event type."""
        event_descriptions = {
            "LOW_BATTERY": "Battery level below threshold",
            "CRITICAL_BATTERY": "Battery level critically low",
            "EMERGENCY_STOP": "Emergency stop activated",
            "SPEED_VIOLATION": "Speed limit exceeded",
            "GEOFENCE_VIOLATION": "Cart outside designated area",
            "GPS_SIGNAL_POOR": "Poor GPS signal quality",
            "CONNECTION_LOST": "Communication lost with cart",
            "SYSTEM_ERROR": "System malfunction detected"
        }
        return event_descriptions.get(event_type, event_type.replace("_", " ").title())
    
    def _assess_battery_health(self, discharge_rate: float, current_level: float) -> str:
        """Assess battery health based on discharge rate and current level."""
        if discharge_rate == 0:
            return "Unknown"
        elif discharge_rate > 15:  # >15% per hour is concerning
            return "Poor"
        elif discharge_rate > 10:  # >10% per hour needs attention
            return "Fair"
        elif discharge_rate > 5:   # >5% per hour is normal
            return "Good"
        else:                      # <=5% per hour is excellent
            return "Excellent"


# Service instance
telemetry_service = TelemetryService()


def get_telemetry_service() -> TelemetryService:
    """Get telemetry service instance."""
    return telemetry_service