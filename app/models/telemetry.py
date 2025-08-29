"""
Telemetry and event models for real-time cart data.
Includes partitioned tables for efficient time-series data.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Float, JSON, BigInteger, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.core.database import Base


class CartTelemetry(Base):
    """
    Real-time telemetry data from golf carts.
    This table should be partitioned by timestamp for performance.
    """
    
    __tablename__ = "cart_telemetry"
    
    # Use composite primary key for partitioning
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    cart_id = Column(UUID(as_uuid=True), ForeignKey("golf_carts.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Position data (PostGIS)
    position = Column(Geometry("POINT", srid=4326), nullable=False)
    altitude_meters = Column(Float)
    
    # Motion data
    heading = Column(Float)  # Degrees (0-359)
    speed = Column(Float)  # km/h
    acceleration = Column(Float)  # m/s²
    
    # Battery data
    battery_level = Column(Integer)  # Percentage (0-100)
    battery_voltage = Column(Float)
    battery_current = Column(Float)
    battery_temperature = Column(Float)
    charging_status = Column(Boolean, default=False)
    
    # System status
    engine_status = Column(String(20))  # ON, OFF, ERROR
    brake_status = Column(Boolean, default=False)
    emergency_stop = Column(Boolean, default=False)
    
    # Environmental
    external_temperature = Column(Float)  # Celsius
    
    # GPS quality
    gps_satellites = Column(Integer)
    gps_hdop = Column(Float)  # Horizontal dilution of precision
    
    # Sensor data (flexible JSON)
    sensor_data = Column(JSON)  # Additional sensor readings
    
    # Performance
    cpu_usage = Column(Float)  # Percentage
    memory_usage = Column(Float)  # Percentage
    disk_usage = Column(Float)  # Percentage
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_cart_telemetry_cart_time', 'cart_id', 'timestamp'),
        Index('idx_cart_telemetry_timestamp', 'timestamp'),
        # Partitioning removed for MVP - can be added later for production
    )
    
    # Relationships
    cart = relationship("GolfCart", back_populates="telemetry")
    
    def __repr__(self):
        return f"<CartTelemetry Cart:{self.cart_id} Time:{self.timestamp}>"
    
    @property
    def coordinates(self):
        """Get coordinates as tuple (lat, lng)."""
        if self.position:
            # Extract coordinates from PostGIS geometry
            # This would need proper deserialization
            return None
        return None


class CartEvent(Base):
    """
    Cart events and alerts.
    Stores important events like geofence violations, maintenance alerts, etc.
    """
    
    __tablename__ = "cart_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    cart_id = Column(UUID(as_uuid=True), ForeignKey("golf_carts.id"), nullable=False)
    
    # Event classification
    event_type = Column(String(50), nullable=False, index=True)  # GEOFENCE_VIOLATION, LOW_BATTERY, MAINTENANCE_DUE, etc.
    event_category = Column(String(30), nullable=False)  # OPERATIONAL, MAINTENANCE, SAFETY, SYSTEM
    severity = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    
    # Event details
    title = Column(String(200), nullable=False)
    description = Column(Text)
    event_data = Column(JSON, nullable=False)  # Flexible event-specific data
    
    # Location when event occurred
    position = Column(Geometry("POINT", srid=4326))
    
    # Timing
    timestamp = Column(DateTime, nullable=False, index=True)
    duration_seconds = Column(Integer)  # For events that have duration
    
    # Resolution
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(UUID(as_uuid=True))  # User who acknowledged
    acknowledged_at = Column(DateTime)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    
    # Automated actions taken
    auto_actions = Column(JSON)  # e.g., ["speed_limited", "notification_sent"]
    
    # Related entities
    related_geofence_id = Column(UUID(as_uuid=True))  # If geofence-related
    related_route_id = Column(UUID(as_uuid=True))  # If route-related
    related_assignment_id = Column(UUID(as_uuid=True))  # If assignment-related
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_cart_events_cart_time', 'cart_id', 'timestamp'),
        Index('idx_cart_events_type_severity', 'event_type', 'severity'),
        Index('idx_cart_events_unresolved', 'resolved', 'severity'),
    )
    
    # Relationships
    cart = relationship("GolfCart", back_populates="events")
    
    def __repr__(self):
        return f"<CartEvent {self.event_type} Cart:{self.cart_id} Severity:{self.severity}>"
    
    @property
    def is_critical(self):
        """Check if event is critical severity."""
        return self.severity == "CRITICAL"
    
    @property
    def needs_attention(self):
        """Check if event needs attention."""
        return not self.resolved and self.severity in ["ERROR", "CRITICAL"]


# Event type constants
class EventType:
    """Standard event types."""
    # Geofence events
    GEOFENCE_ENTRY = "GEOFENCE_ENTRY"
    GEOFENCE_EXIT = "GEOFENCE_EXIT"
    GEOFENCE_VIOLATION = "GEOFENCE_VIOLATION"
    SPEED_VIOLATION = "SPEED_VIOLATION"
    
    # Battery events
    LOW_BATTERY = "LOW_BATTERY"
    CRITICAL_BATTERY = "CRITICAL_BATTERY"
    CHARGING_STARTED = "CHARGING_STARTED"
    CHARGING_COMPLETED = "CHARGING_COMPLETED"
    
    # Maintenance events
    MAINTENANCE_DUE = "MAINTENANCE_DUE"
    MAINTENANCE_OVERDUE = "MAINTENANCE_OVERDUE"
    MAINTENANCE_COMPLETED = "MAINTENANCE_COMPLETED"
    
    # Operational events
    CART_STARTED = "CART_STARTED"
    CART_STOPPED = "CART_STOPPED"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    COLLISION_DETECTED = "COLLISION_DETECTED"
    TILT_DETECTED = "TILT_DETECTED"
    
    # System events
    CONNECTION_LOST = "CONNECTION_LOST"
    CONNECTION_RESTORED = "CONNECTION_RESTORED"
    FIRMWARE_UPDATE = "FIRMWARE_UPDATE"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    GPS_SIGNAL_LOST = "GPS_SIGNAL_LOST"
    
    # Assignment events
    ASSIGNMENT_STARTED = "ASSIGNMENT_STARTED"
    ASSIGNMENT_COMPLETED = "ASSIGNMENT_COMPLETED"
    PACE_WARNING = "PACE_WARNING"  # Playing too slow
    OFF_COURSE = "OFF_COURSE"  # Cart off designated route