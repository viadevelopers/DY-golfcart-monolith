"""
User models for manufacturer and golf course users.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ManufacturerUser(Base):
    """Manufacturer system administrator users."""
    
    __tablename__ = "manufacturer_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    department = Column(String(50))
    password_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_golf_courses = relationship("GolfCourse", back_populates="created_by_user")
    uploaded_maps = relationship("GolfCourseMap", back_populates="uploaded_by_user")
    created_routes = relationship("Route", back_populates="created_by_user")
    cart_registrations = relationship("CartRegistration", back_populates="registered_by_user")
    
    def __repr__(self):
        return f"<ManufacturerUser {self.email}>"
    
    @property
    def full_name(self):
        return self.name


class GolfCourseUser(Base):
    """Golf course operational users."""
    
    __tablename__ = "golf_course_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    golf_course_id = Column(UUID(as_uuid=True), ForeignKey("golf_courses.id"), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    position = Column(String(50))
    password_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)  # Golf course admin
    permissions = Column(Text)  # JSON string of permissions
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    golf_course = relationship("GolfCourse", back_populates="users")
    created_assignments = relationship("CartAssignment", back_populates="created_by_user")
    maintenance_logs = relationship("MaintenanceLog", back_populates="created_by_user")
    
    def __repr__(self):
        return f"<GolfCourseUser {self.email}>"
    
    @property
    def full_name(self):
        return self.name