"""
Database models for DY-GOLFCART system.
All models use SQLAlchemy with PostGIS support for geospatial data.
"""
from app.models.user import ManufacturerUser, GolfCourseUser
from app.models.golf_course import GolfCourse, GolfCourseMap, Hole, Route, Geofence
from app.models.cart import CartModel, GolfCart, CartRegistration
from app.models.operations import CartAssignment, MaintenanceLog
from app.models.telemetry import CartTelemetry, CartEvent

__all__ = [
    # Users
    "ManufacturerUser",
    "GolfCourseUser",
    # Golf Course
    "GolfCourse",
    "GolfCourseMap",
    "Hole",
    "Route",
    "Geofence",
    # Cart
    "CartModel",
    "GolfCart",
    "CartRegistration",
    # Operations
    "CartAssignment",
    "MaintenanceLog",
    # Telemetry
    "CartTelemetry",
    "CartEvent",
]