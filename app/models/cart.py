"""
Golf cart and cart model entities.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Float, JSON, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class CartModel(Base):
    """Golf cart model/type definition."""
    
    __tablename__ = "cart_models"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    manufacturer = Column(String(50), nullable=False)
    model_name = Column(String(50), nullable=False)
    model_code = Column(String(30), unique=True, nullable=False, index=True)
    year = Column(Integer)
    
    # Specifications
    capacity = Column(Integer, default=2)  # Number of passengers
    max_speed = Column(Float, default=20.0)  # km/h
    range_km = Column(Float)  # Battery range in km
    charge_time_hours = Column(Float)  # Full charge time
    
    # Features (JSON for flexibility)
    features = Column(JSON)  # e.g., {"gps": true, "autonomous": true, "usb_charging": true}
    
    # Images
    image_url = Column(String(500))
    manual_url = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    golf_carts = relationship("GolfCart", back_populates="cart_model")
    
    def __repr__(self):
        return f"<CartModel {self.manufacturer} {self.model_name}>"


class GolfCart(Base):
    """Individual golf cart instance."""
    
    __tablename__ = "golf_carts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    serial_number = Column(String(50), unique=True, nullable=False, index=True)
    cart_model_id = Column(UUID(as_uuid=True), ForeignKey("cart_models.id"))
    golf_course_id = Column(UUID(as_uuid=True), ForeignKey("golf_courses.id"))
    
    # Cart identification
    cart_number = Column(String(20))  # Display number on the cart
    qr_code = Column(String(100))  # QR code for mobile app
    
    # Status and mode
    status = Column(String(20), default="IDLE")  # IDLE, RUNNING, CHARGING, MAINTENANCE, OFFLINE, ERROR
    mode = Column(String(20), default="MANUAL")  # MANUAL, AUTONOMOUS, FOLLOW, RETURN
    
    # Connectivity
    mqtt_client_id = Column(String(100), unique=True)
    last_ping = Column(DateTime)
    ip_address = Column(String(45))  # Last known IP
    
    # Firmware
    firmware_version = Column(String(20))
    last_update = Column(DateTime)
    auto_update_enabled = Column(Boolean, default=True)
    
    # Operational data
    total_distance_km = Column(Float, default=0.0)
    total_runtime_hours = Column(Float, default=0.0)
    last_maintenance_date = Column(DateTime)
    next_maintenance_date = Column(DateTime)
    
    # Settings
    speed_limit_override = Column(Float)  # Cart-specific speed limit
    features_enabled = Column(JSON)  # Feature flags
    
    # Metadata
    purchase_date = Column(DateTime)
    warranty_expiry = Column(DateTime)
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint for golf_course_id + cart_number
    __table_args__ = (
        UniqueConstraint('golf_course_id', 'cart_number', name='_golf_course_cart_number_uc'),
    )
    
    # Relationships
    cart_model = relationship("CartModel", back_populates="golf_carts")
    golf_course = relationship("GolfCourse", back_populates="golf_carts")
    registrations = relationship("CartRegistration", back_populates="cart", cascade="all, delete-orphan")
    assignments = relationship("CartAssignment", back_populates="cart")
    maintenance_logs = relationship("MaintenanceLog", back_populates="cart", cascade="all, delete-orphan")
    telemetry = relationship("CartTelemetry", back_populates="cart", cascade="all, delete-orphan")
    events = relationship("CartEvent", back_populates="cart", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<GolfCart {self.serial_number} #{self.cart_number}>"
    
    @property
    def is_online(self):
        """Check if cart is online based on last ping."""
        if not self.last_ping:
            return False
        time_diff = datetime.utcnow() - self.last_ping
        return time_diff.total_seconds() < 120  # Consider online if pinged within 2 minutes


class CartRegistration(Base):
    """Cart registration history - tracks cart assignments to golf courses."""
    
    __tablename__ = "cart_registrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    cart_id = Column(UUID(as_uuid=True), ForeignKey("golf_carts.id"), nullable=False)
    golf_course_id = Column(UUID(as_uuid=True), ForeignKey("golf_courses.id"), nullable=False)
    registered_by = Column(UUID(as_uuid=True), ForeignKey("manufacturer_users.id"), nullable=False)
    
    registration_type = Column(String(30), nullable=False)  # NEW, TRANSFER, RETURN, TEMPORARY
    cart_number = Column(String(20))  # Assigned cart number at this course
    
    # Registration period
    start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_date = Column(DateTime)  # Null means active registration
    
    # Registration details
    contract_number = Column(String(50))
    notes = Column(Text)
    
    registered_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    cart = relationship("GolfCart", back_populates="registrations")
    registered_by_user = relationship("ManufacturerUser", back_populates="cart_registrations")
    
    def __repr__(self):
        return f"<CartRegistration {self.registration_type} Cart:{self.cart_id}>"