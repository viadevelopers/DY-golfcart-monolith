"""
Map Service for DY-GOLFCART Management System

Handles map processing, tile generation, and geospatial data management.
Independent lifecycle from golf courses as specified in sequence diagrams.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4
from datetime import datetime
from io import BytesIO
from PIL import Image

from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, LineString, Polygon

from app.core.database import get_db
from app.services.s3_service import S3Service
from app.models.golf_course import GolfCourseMap, Route

logger = logging.getLogger(__name__)


class MapService:
    """
    Map processing service for golf course maps and routing.
    Handles independent map lifecycle as per sequence diagrams.
    """
    
    def __init__(self):
        self.s3_service = S3Service()
        
    def process_map_upload(
        self, 
        file_data: bytes, 
        filename: str,
        name: str,
        version: str,
        center_lat: Optional[float] = None,
        center_lng: Optional[float] = None,
        zoom_levels: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Process uploaded map file according to Title 1 sequence.
        
        Flow: Upload → S3 Storage → Tile Generation → map_features table
        
        Args:
            file_data: Raw file data
            filename: Original filename
            name: Map display name
            version: Map version
            center_lat: Map center latitude
            center_lng: Map center longitude  
            zoom_levels: Supported zoom levels
            
        Returns:
            Dict with map_id, storage_url, tiles, and bounds
        """
        try:
            map_id = str(uuid4())
            
            # Step 1: Store in S3 (MS → S3)
            logger.info(f"Uploading map {name} to S3 storage")
            s3_result = self.s3_service.upload_map(
                file_data, 
                filename, 
                map_id=map_id
            )
            
            storage_url = s3_result['url']
            logger.info(f"Map uploaded to S3: {storage_url}")
            
            # Step 2: Generate tiles if zoom levels provided (S3 tile generation)
            tiles = []
            if zoom_levels:
                logger.info(f"Generating tiles for zoom levels: {zoom_levels}")
                tile_result = self.s3_service.generate_tiles(
                    file_data, 
                    map_id, 
                    zoom_levels
                )
                tiles = tile_result.get('tiles', [])
                logger.info(f"Generated {len(tiles)} tile URLs")
            
            # Step 3: Process map features and bounds
            bounds = self._calculate_map_bounds(
                file_data, 
                center_lat, 
                center_lng
            )
            
            # Step 4: Store in map_features table (MS → DB)
            map_features = self._extract_map_features(file_data, filename)
            
            # Save to database (simulated - in real implementation would use map_features table)
            map_record = {
                'id': map_id,
                'name': name,
                'version': version,
                'storage_url': storage_url,
                'tiles': tiles,
                'bounds': bounds,
                'features': map_features,
                'center_point': [center_lng, center_lat] if center_lat and center_lng else None,
                'zoom_levels': zoom_levels or [10, 12, 14, 16, 18],
                'created_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Map processing completed for {map_id}")
            
            # Return response matching Title 1 sequence requirements
            return {
                'map_id': map_id,
                'storage_url': storage_url,
                'tiles': tiles,
                'bounds': bounds,
                'features_count': len(map_features),
                'status': 'processed'
            }
            
        except Exception as e:
            logger.error(f"Map processing failed: {e}")
            raise Exception(f"Map processing error: {str(e)}")
    
    def create_route(
        self,
        name: str,
        route_type: str,
        path: List[List[float]],
        map_id: str,
        distance_meters: Optional[float] = None,
        estimated_time_seconds: Optional[int] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Create route as per Title 1 sequence.
        
        Flow: Route data → PostGIS LINESTRING → routes table
        
        Args:
            name: Route name
            route_type: Route type (FULL_COURSE, HOLE_TO_HOLE, etc.)
            path: Array of [lng, lat] coordinates
            map_id: Reference map ID
            distance_meters: Route distance
            estimated_time_seconds: Estimated travel time
            db: Database session
            
        Returns:
            Dict with route details
        """
        try:
            if not path or len(path) < 2:
                raise ValueError("Route path must contain at least 2 coordinates")
            
            # Validate coordinates
            for coord in path:
                if len(coord) != 2:
                    raise ValueError("Each coordinate must have exactly 2 values [lng, lat]")
                lng, lat = coord
                if not (-180 <= lng <= 180) or not (-90 <= lat <= 90):
                    raise ValueError(f"Invalid coordinates: [{lng}, {lat}]")
            
            # Calculate distance if not provided
            if distance_meters is None:
                distance_meters = self._calculate_route_distance(path)
            
            # Estimate time if not provided (assuming 20 km/h average speed)
            if estimated_time_seconds is None:
                estimated_time_seconds = int((distance_meters / 1000) * 3.6 * 20)  # meters to hours * 3600
            
            route_id = str(uuid4())
            
            # Create route record (would normally use database session)
            route_data = {
                'id': route_id,
                'name': name,
                'route_type': route_type,
                'path': path,  # Would be converted to PostGIS LINESTRING
                'map_id': map_id,
                'distance_meters': distance_meters,
                'estimated_time_seconds': estimated_time_seconds,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'active'
            }
            
            logger.info(f"Route created: {route_id} ({route_type})")
            
            # Return response matching Title 1 sequence requirements
            return {
                'route_id': route_id,
                'name': name,
                'route_type': route_type,
                'distance_meters': distance_meters,
                'estimated_time_seconds': estimated_time_seconds,
                'coordinates_count': len(path),
                'status': 'created'
            }
            
        except Exception as e:
            logger.error(f"Route creation failed: {e}")
            raise Exception(f"Route creation error: {str(e)}")
    
    def get_map_data(self, map_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve map data by ID.
        
        Args:
            map_id: Map identifier
            
        Returns:
            Map data dictionary or None
        """
        try:
            # In real implementation, would query map_features table
            # For now, return basic structure
            return {
                'id': map_id,
                'status': 'active',
                'available': True
            }
        except Exception as e:
            logger.error(f"Failed to retrieve map {map_id}: {e}")
            return None
    
    def _calculate_map_bounds(
        self, 
        file_data: bytes, 
        center_lat: Optional[float], 
        center_lng: Optional[float]
    ) -> List[List[float]]:
        """
        Calculate map bounds from file data or center point.
        
        Returns:
            Bounds as [[min_lng, min_lat], [max_lng, max_lat]]
        """
        try:
            if center_lat and center_lng:
                # Create approximate bounds around center point (roughly 1km radius)
                offset = 0.009  # Approximately 1km in degrees
                return [
                    [center_lng - offset, center_lat - offset],  # Southwest
                    [center_lng + offset, center_lat + offset]   # Northeast
                ]
            else:
                # Default bounds (can be improved with actual file analysis)
                return [
                    [-122.5, 37.7],   # Southwest (San Francisco area default)
                    [-122.3, 37.8]    # Northeast
                ]
        except Exception as e:
            logger.warning(f"Could not calculate bounds: {e}")
            return [[-122.5, 37.7], [-122.3, 37.8]]
    
    def _extract_map_features(self, file_data: bytes, filename: str) -> List[Dict[str, Any]]:
        """
        Extract geographic features from map file.
        
        In production, this would parse GeoJSON, KML, or analyze image files.
        """
        try:
            features = []
            
            # Basic feature extraction based on file type
            if filename.lower().endswith(('.geojson', '.json')):
                # Would parse GeoJSON features
                features.append({
                    'type': 'geojson_features',
                    'count': 0,
                    'parsed': False
                })
            elif filename.lower().endswith(('.kml', '.kmz')):
                # Would parse KML features
                features.append({
                    'type': 'kml_features', 
                    'count': 0,
                    'parsed': False
                })
            elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff')):
                # Would analyze image features
                features.append({
                    'type': 'raster_image',
                    'format': filename.split('.')[-1].lower(),
                    'analyzed': False
                })
            
            return features
            
        except Exception as e:
            logger.warning(f"Feature extraction failed: {e}")
            return []
    
    def _calculate_route_distance(self, path: List[List[float]]) -> float:
        """
        Calculate route distance using Haversine formula.
        
        Args:
            path: List of [lng, lat] coordinates
            
        Returns:
            Distance in meters
        """
        from math import radians, sin, cos, sqrt, atan2
        
        total_distance = 0.0
        
        for i in range(len(path) - 1):
            lng1, lat1 = path[i]
            lng2, lat2 = path[i + 1]
            
            # Haversine formula
            R = 6371000  # Earth's radius in meters
            
            lat1_rad = radians(lat1)
            lat2_rad = radians(lat2)
            delta_lat = radians(lat2 - lat1)
            delta_lng = radians(lng2 - lng1)
            
            a = (sin(delta_lat / 2) ** 2 + 
                 cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng / 2) ** 2)
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            
            distance = R * c
            total_distance += distance
        
        return total_distance


# Global service instance
map_service = MapService()


def get_map_service() -> MapService:
    """Get map service instance."""
    return map_service