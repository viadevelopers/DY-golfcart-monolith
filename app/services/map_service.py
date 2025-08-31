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
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image

from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from geoalchemy2.elements import WKTElement
from shapely.geometry import Point, LineString, Polygon

from app.core.database import get_db, get_db_context
from app.services.s3_service import S3Service
from app.models.golf_course import GolfCourseMap, Route
from app.models.map import Map
from app.repositories.map_repository import MapRepository

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
        zoom_levels: Optional[List[int]] = None,
        uploaded_by_id: Optional[str] = None,
        golf_course_id: Optional[str] = None
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
            
            # Step 4: Store in maps table (MS → DB)
            map_features = self._extract_map_features(file_data, filename)
            
            # Save to database
            with get_db_context() as db:
                # Create geometry objects for PostGIS
                center_geom = None
                if center_lat and center_lng:
                    center_geom = WKTElement(f'POINT({center_lng} {center_lat})', srid=4326)
                
                bounds_geom = None
                if bounds and len(bounds) == 2:
                    # Create polygon from bounds [[min_lng, min_lat], [max_lng, max_lat]]
                    min_lng, min_lat = bounds[0]
                    max_lng, max_lat = bounds[1]
                    bounds_geom = WKTElement(
                        f'POLYGON(({min_lng} {min_lat}, {max_lng} {min_lat}, '
                        f'{max_lng} {max_lat}, {min_lng} {max_lat}, {min_lng} {min_lat}))',
                        srid=4326
                    )
                
                # Create Map record
                map_record = Map(
                    id=map_id,
                    name=name,
                    version=version,
                    storage_url=storage_url,
                    file_type=self._detect_file_type(filename),
                    file_size=len(file_data),
                    original_filename=filename,
                    bounds=bounds_geom,
                    center_point=center_geom,
                    zoom_levels=zoom_levels or [10, 12, 14, 16, 18],
                    tiles=tiles,
                    features={'extracted': map_features, 'count': len(map_features)},
                    status='active',
                    uploaded_by=uploaded_by_id,
                    golf_course_id=golf_course_id
                )
                
                db.add(map_record)
                db.commit()
                db.refresh(map_record)
                
                logger.info(f"Map {map_id} saved to database")
            
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
                'created_at': datetime.now(timezone.utc).isoformat(),
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
    
    def get_map_data(self, map_id: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve map data by ID from database.
        
        Args:
            map_id: Map identifier
            db: Database session (optional)
            
        Returns:
            Map data dictionary or None
        """
        try:
            if db:
                map_record = db.query(Map).filter(Map.id == map_id).first()
            else:
                with get_db_context() as session:
                    map_record = session.query(Map).filter(Map.id == map_id).first()
            
            if map_record:
                return map_record.to_dict()
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve map {map_id}: {e}")
            return None
    
    def list_maps(
        self, 
        filters: Dict[str, Any], 
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[Map]:
        """
        List maps with optional filters.
        
        Args:
            filters: Filter criteria
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Map records
        """
        query = db.query(Map)
        
        if filters.get('status'):
            query = query.filter(Map.status == filters['status'])
        if filters.get('golf_course_id'):
            query = query.filter(Map.golf_course_id == filters['golf_course_id'])
        if filters.get('file_type'):
            query = query.filter(Map.file_type == filters['file_type'])
            
        return query.order_by(Map.created_at.desc()).offset(skip).limit(limit).all()
    
    def update_map_status(self, map_id: str, status: str, db: Session) -> bool:
        """
        Update map status.
        
        Args:
            map_id: Map identifier
            status: New status (active, archived, processing, failed)
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            map_record = db.query(Map).filter(Map.id == map_id).first()
            if map_record:
                map_record.status = status
                map_record.updated_at = datetime.now(timezone.utc)
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update map {map_id} status: {e}")
            db.rollback()
            return False
    
    def archive_map(self, map_id: str, db: Session) -> bool:
        """
        Archive a map (soft delete).
        
        Args:
            map_id: Map identifier
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        return self.update_map_status(map_id, 'archived', db)
    
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
    
    def _detect_file_type(self, filename: str) -> str:
        """
        Detect file type from filename extension.
        
        Args:
            filename: Original filename
            
        Returns:
            File type string
        """
        ext = filename.lower().split('.')[-1] if '.' in filename else 'unknown'
        type_map = {
            'geojson': 'geojson',
            'json': 'geojson',
            'kml': 'kml',
            'kmz': 'kmz',
            'png': 'image',
            'jpg': 'image',
            'jpeg': 'image',
            'tiff': 'image',
            'tif': 'image'
        }
        return type_map.get(ext, 'unknown')


# Global service instance
map_service = MapService()


def get_map_service() -> MapService:
    """Get map service instance."""
    return map_service