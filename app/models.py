from sqlalchemy import (
    Column,
    String,
    DateTime,
    Float,
    Integer,
    Boolean,
    ForeignKey,
    Enum as SQLAlchemyEnum,
    JSON,
    ARRAY
)
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime
from .core.enums import Role, UserStatus, GolfCourseStatus, CartStatus, MapType

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(SQLAlchemyEnum(Role), default=Role.USER)
    status = Column(SQLAlchemyEnum(UserStatus), default=UserStatus.ACTIVE)
    phone = Column(String)
    department = Column(String)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    golf_course_id = Column(String, ForeignKey("golf_courses.id"))
    golf_course = relationship("GolfCourse", back_populates="users")


class GolfCourse(Base):
    __tablename__ = "golf_courses"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    address = Column(String, nullable=False)
    detail_address = Column(String)
    postal_code = Column(String)
    phone = Column(String)
    fax = Column(String)
    email = Column(String, unique=True)
    website = Column(String)
    status = Column(SQLAlchemyEnum(GolfCourseStatus), default=GolfCourseStatus.ACTIVE)
    location = Column(JSON, nullable=False)  # For Location schema
    operating_hours = Column(JSON)          # For OperatingHours schema
    facilities = Column(ARRAY(String))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="golf_course")
    carts = relationship("Cart", back_populates="golf_course")
    maps = relationship("Map", back_populates="golf_course")
    courses = relationship("Course", back_populates="golf_course")


class Cart(Base):
    __tablename__ = "carts"
    id = Column(String, primary_key=True, index=True)
    cart_number = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    manufacturer = Column(String)
    manufacturing_date = Column(DateTime)
    purchase_date = Column(DateTime)
    status = Column(SQLAlchemyEnum(CartStatus), default=CartStatus.AVAILABLE)
    specifications = Column(JSON)
    battery = Column(JSON)
    maintenance_info = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    golf_course_id = Column(String, ForeignKey("golf_courses.id"), nullable=False)
    golf_course = relationship("GolfCourse", back_populates="carts")


class Map(Base):
    __tablename__ = "maps"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    type = Column(SQLAlchemyEnum(MapType))
    version = Column(String)
    image_url = Column(String)
    metadata_url = Column(String)
    bounds = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    golf_course_id = Column(String, ForeignKey("golf_courses.id"), nullable=False)
    golf_course = relationship("GolfCourse", back_populates="maps")


class Course(Base):
    __tablename__ = "courses"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    holes = Column(Integer, nullable=False)
    par = Column(Integer, nullable=False)
    length = Column(Float)

    golf_course_id = Column(String, ForeignKey("golf_courses.id"), nullable=False)
    golf_course = relationship("GolfCourse", back_populates="courses")
