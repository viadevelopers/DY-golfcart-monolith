"""Position value object for golf cart location."""

from typing import Any
from math import radians, sin, cos, sqrt, atan2

from app.domain.shared import ValueObject
from app.domain.shared.exceptions import InvalidValueException


class Position(ValueObject):
    """Represents a geographic position with latitude and longitude."""
    
    def __init__(self, latitude: float, longitude: float):
        if not -90 <= latitude <= 90:
            raise InvalidValueException(f"Invalid latitude: {latitude}. Must be between -90 and 90.")
        if not -180 <= longitude <= 180:
            raise InvalidValueException(f"Invalid longitude: {longitude}. Must be between -180 and 180.")
        
        self._latitude = latitude
        self._longitude = longitude
    
    @property
    def latitude(self) -> float:
        """Get latitude."""
        return self._latitude
    
    @property
    def longitude(self) -> float:
        """Get longitude."""
        return self._longitude
    
    @property
    def lat(self) -> float:
        """Alias for latitude (backward compatibility)."""
        return self._latitude
    
    @property
    def lng(self) -> float:
        """Alias for longitude (backward compatibility)."""
        return self._longitude
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate distance to another position in meters using Haversine formula."""
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = radians(self._latitude)
        lat2_rad = radians(other._latitude)
        delta_lat = radians(other._latitude - self._latitude)
        delta_lon = radians(other._longitude - self._longitude)
        
        a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def is_within_bounds(self, min_lat: float, max_lat: float, min_lng: float, max_lng: float) -> bool:
        """Check if position is within given bounds."""
        return (min_lat <= self._latitude <= max_lat and 
                min_lng <= self._longitude <= max_lng)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "lat": self._latitude,
            "lng": self._longitude
        }
    
    def __eq__(self, other: Any) -> bool:
        """Check equality."""
        if not isinstance(other, Position):
            return False
        return (self._latitude == other._latitude and 
                self._longitude == other._longitude)
    
    def __hash__(self) -> int:
        """Get hash."""
        return hash((self._latitude, self._longitude))
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Position(lat={self._latitude}, lng={self._longitude})"