"""
Operational models for cart assignments and maintenance.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Float, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class CartAssignment(Base):
    """Cart assignment to players/reservations."""
    
    __tablename__ = "cart_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    golf_course_id = Column(UUID(as_uuid=True), ForeignKey("golf_courses.id"), nullable=False)
    cart_id = Column(UUID(as_uuid=True), ForeignKey("golf_carts.id"), nullable=False)
    
    # Reservation details
    reservation_code = Column(String(20), unique=True, index=True)
    reservation_type = Column(String(20), default="REGULAR")  # REGULAR, TOURNAMENT, MEMBER, GUEST
    
    # Player information
    player_name = Column(String(100))
    player_email = Column(String(100))
    player_phone = Column(String(20))
    player_count = Column(Integer, default=1)
    member_id = Column(String(50))  # Golf course member ID if applicable
    
    # Schedule
    start_hole = Column(Integer, default=1)
    current_hole = Column(Integer)
    scheduled_start = Column(DateTime, nullable=False)
    scheduled_end = Column(DateTime)
    actual_start = Column(DateTime)
    actual_end = Column(DateTime)
    
    # Status
    status = Column(String(20), default="RESERVED")  # RESERVED, CHECKED_IN, ACTIVE, COMPLETED, CANCELLED, NO_SHOW
    
    # Tracking
    total_distance_km = Column(Float)
    pace_of_play_minutes = Column(Integer)  # Minutes per hole
    
    # Payment
    payment_status = Column(String(20))  # PENDING, PAID, REFUNDED
    payment_amount = Column(Float)
    payment_method = Column(String(20))  # CREDIT_CARD, CASH, MEMBER_ACCOUNT
    
    # Notes
    special_requests = Column(Text)
    notes = Column(Text)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("golf_course_users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    golf_course = relationship("GolfCourse", back_populates="cart_assignments")
    cart = relationship("GolfCart", back_populates="assignments")
    created_by_user = relationship("GolfCourseUser", back_populates="created_assignments")
    
    def __repr__(self):
        return f"<CartAssignment {self.reservation_code} Status:{self.status}>"
    
    @property
    def is_active(self):
        """Check if assignment is currently active."""
        return self.status == "ACTIVE"
    
    @property
    def duration_minutes(self):
        """Calculate actual duration in minutes."""
        if self.actual_start and self.actual_end:
            return int((self.actual_end - self.actual_start).total_seconds() / 60)
        return None


class MaintenanceLog(Base):
    """Cart maintenance records."""
    
    __tablename__ = "maintenance_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    cart_id = Column(UUID(as_uuid=True), ForeignKey("golf_carts.id"), nullable=False)
    
    # Maintenance details
    maintenance_type = Column(String(50), nullable=False)  # ROUTINE, REPAIR, INSPECTION, CLEANING, BATTERY, TIRE
    priority = Column(String(20), default="NORMAL")  # LOW, NORMAL, HIGH, URGENT
    status = Column(String(20), default="SCHEDULED")  # SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED
    
    # Description
    description = Column(Text)
    issues_found = Column(Text)
    actions_taken = Column(Text)
    parts_replaced = Column(JSON)  # Array of parts with costs
    
    # Schedule
    scheduled_date = Column(DateTime)
    performed_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    duration_hours = Column(Float)
    
    # Personnel
    performed_by = Column(String(100))
    technician_notes = Column(Text)
    
    # Costs
    labor_cost = Column(Float)
    parts_cost = Column(Float)
    total_cost = Column(Float)
    
    # Next maintenance
    next_maintenance_date = Column(DateTime)
    next_maintenance_type = Column(String(50))
    
    # Mileage/hours at maintenance
    odometer_km = Column(Float)
    runtime_hours = Column(Float)
    
    # Attachments
    invoice_number = Column(String(50))
    attachments = Column(JSON)  # Array of file URLs
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("golf_course_users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cart = relationship("GolfCart", back_populates="maintenance_logs")
    created_by_user = relationship("GolfCourseUser", back_populates="maintenance_logs")
    
    def __repr__(self):
        return f"<MaintenanceLog {self.maintenance_type} Cart:{self.cart_id}>"
    
    @property
    def is_overdue(self):
        """Check if maintenance is overdue."""
        if self.status == "SCHEDULED" and self.scheduled_date:
            return datetime.utcnow() > self.scheduled_date
        return False