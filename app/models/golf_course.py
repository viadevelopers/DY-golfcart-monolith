"""
Golf course related models with geospatial support.
Uses PostGIS for map data, routes, and geofences.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Float, JSON, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.core.database import Base


class GolfCourse(Base):
    """Golf course entity."""
    
    __tablename__ = "golf_courses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=False, index=True)
    address = Column(Text)
    phone = Column(String(20))
    email = Column(String(100))
    hole_count = Column(Integer, default=18)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, INACTIVE, MAINTENANCE
    timezone = Column(String(50), default="UTC")
    
    # Operating hours
    opening_time = Column(String(5))  # HH:MM format
    closing_time = Column(String(5))  # HH:MM format
    
    # Settings
    cart_speed_limit = Column(Float, default=20.0)  # km/h
    auto_return_enabled = Column(Boolean, default=False)
    geofence_alerts_enabled = Column(Boolean, default=True)
    
    metadata_json = Column(JSON)  # Additional flexible data
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("manufacturer_users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_by_user = relationship("ManufacturerUser", back_populates="created_golf_courses")
    users = relationship("GolfCourseUser", back_populates="golf_course", cascade="all, delete-orphan")
    maps = relationship("GolfCourseMap", back_populates="golf_course", cascade="all, delete-orphan")
    holes = relationship("Hole", back_populates="golf_course", cascade="all, delete-orphan")
    routes = relationship("Route", back_populates="golf_course", cascade="all, delete-orphan")
    geofences = relationship("Geofence", back_populates="golf_course", cascade="all, delete-orphan")
    golf_carts = relationship("GolfCart", back_populates="golf_course")
    cart_assignments = relationship("CartAssignment", back_populates="golf_course")
    
    def __repr__(self):
        return f"<GolfCourse {self.code}: {self.name}>"


class GolfCourseMap(Base):
    """Golf course map data with tiles."""
    
    __tablename__ = "golf_course_maps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    golf_course_id = Column(UUID(as_uuid=True), ForeignKey("golf_courses.id"), nullable=False)
    name = Column(String(100), nullable=False)
    version = Column(String(20), nullable=False)
    
    # Map data
    tile_url = Column(String(500))  # URL pattern for map tiles
    static_image_url = Column(String(500))  # Full map image URL
    
    # Geospatial bounds (PostGIS)
    bounds = Column(Geometry("POLYGON", srid=4326))  # Map boundary
    center_point = Column(Geometry("POINT", srid=4326))  # Map center
    
    # Map configuration
    min_zoom = Column(Integer, default=10)
    max_zoom = Column(Integer, default=19)
    default_zoom = Column(Integer, default=15)
    
    is_active = Column(Boolean, default=True)
    metadata_json = Column(JSON)  # Additional map metadata
    
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("manufacturer_users.id"))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    golf_course = relationship("GolfCourse", back_populates="maps")
    uploaded_by_user = relationship("ManufacturerUser", back_populates="uploaded_maps")
    
    def __repr__(self):
        return f"<GolfCourseMap {self.name} v{self.version}>"


class Hole(Base):
    """Golf course hole information."""
    
    __tablename__ = "holes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    golf_course_id = Column(UUID(as_uuid=True), ForeignKey("golf_courses.id"), nullable=False)
    hole_number = Column(Integer, nullable=False)
    par = Column(Integer, nullable=False)
    
    # Distances in meters
    distance_red = Column(Integer)  # Red tee
    distance_white = Column(Integer)  # White tee
    distance_blue = Column(Integer)  # Blue tee
    distance_black = Column(Integer)  # Black tee
    
    # Geospatial positions (PostGIS)
    tee_position = Column(Geometry("POINT", srid=4326))
    green_position = Column(Geometry("POINT", srid=4326))
    pin_position = Column(Geometry("POINT", srid=4326))  # Current pin position
    
    # Hazards and features
    hazards = Column(JSON)  # Array of hazard polygons
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    golf_course = relationship("GolfCourse", back_populates="holes")
    
    def __repr__(self):
        return f"<Hole {self.hole_number} Par {self.par}>"


class Route(Base):
    """Cart navigation routes."""
    
    __tablename__ = "routes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    golf_course_id = Column(UUID(as_uuid=True), ForeignKey("golf_courses.id"), nullable=False)
    name = Column(String(100), nullable=False)
    route_type = Column(String(30), nullable=False)  # HOLE_TO_HOLE, RETURN_TO_BASE, CHARGING, CUSTOM
    
    # Route geometry (PostGIS)
    path = Column(Geometry("LINESTRING", srid=4326), nullable=False)
    distance_meters = Column(Float)
    estimated_time_seconds = Column(Integer)
    
    # Route metadata
    from_hole = Column(Integer)  # Starting hole number
    to_hole = Column(Integer)  # Destination hole number
    waypoints = Column(JSON)  # Additional waypoint information
    speed_limit = Column(Float)  # Route-specific speed limit
    
    is_active = Column(Boolean, default=True)
    is_preferred = Column(Boolean, default=False)  # Preferred route for navigation
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("manufacturer_users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    golf_course = relationship("GolfCourse", back_populates="routes")
    created_by_user = relationship("ManufacturerUser", back_populates="created_routes")
    
    def __repr__(self):
        return f"<Route {self.name} ({self.route_type})>"


class Geofence(Base):
    """Restricted areas and zones."""
    
    __tablename__ = "geofences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    golf_course_id = Column(UUID(as_uuid=True), ForeignKey("golf_courses.id"), nullable=False)
    name = Column(String(100), nullable=False)
    fence_type = Column(String(30), nullable=False)  # RESTRICTED, SLOW_ZONE, NO_ENTRY, HAZARD, PARKING
    
    # Geofence geometry (PostGIS)
    geometry = Column(Geometry("POLYGON", srid=4326), nullable=False)
    
    # Rules
    speed_limit = Column(Float)  # km/h, null means use default
    alert_on_entry = Column(Boolean, default=False)
    alert_on_exit = Column(Boolean, default=False)
    auto_stop = Column(Boolean, default=False)  # Stop cart automatically
    
    # Schedule (JSON array of time ranges)
    schedule = Column(JSON)  # e.g., [{"start": "08:00", "end": "18:00", "days": ["MON", "TUE"]}]
    
    is_active = Column(Boolean, default=True)
    severity = Column(String(20), default="WARNING")  # INFO, WARNING, CRITICAL
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    golf_course = relationship("GolfCourse", back_populates="geofences")
    
    def __repr__(self):
        return f"<Geofence {self.name} ({self.fence_type})>"