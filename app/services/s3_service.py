"""
S3 Service for DY-GOLFCART Management System

Handles file storage with S3-compatible structure using local storage.
Designed for easy migration to actual S3 in the future.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image
import hashlib
import math

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Service:
    """
    S3-compatible storage service using local filesystem.
    Maintains S3 path structure for future migration.
    
    Future: Replace local storage with boto3 S3 client.
    """
    
    def __init__(self):
        # S3 configuration (ready for future use)
        self.bucket_name = getattr(settings, 'S3_BUCKET_NAME', 'dy-golfcart-maps')
        self.region = getattr(settings, 'AWS_REGION', 'us-west-2')
        
        # Local storage configuration (current implementation)
        self.local_storage_path = getattr(settings, 'UPLOAD_DIR', '/tmp/uploads')
        self.local_endpoint = getattr(settings, 'LOCAL_STORAGE_URL', 'http://localhost:8000/uploads')
        
        # Create S3-like directory structure
        self._init_storage_structure()
        
    def _init_storage_structure(self):
        """Initialize S3-like directory structure for local storage."""
        directories = [
            'maps/originals',
            'maps/tiles',
            'routes',
            'geofences',
            'documents'
        ]
        
        for directory in directories:
            path = os.path.join(self.local_storage_path, directory)
            os.makedirs(path, exist_ok=True)
            logger.debug(f"Storage directory ready: {path}")
    
    def upload_map(
        self, 
        file_data: bytes, 
        filename: str, 
        map_id: str,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload map file with S3-compatible path structure.
        
        S3 Path Format: maps/originals/{map_id}/{filename}
        
        Args:
            file_data: Raw file bytes
            filename: Original filename
            map_id: Unique map identifier
            content_type: MIME content type
            
        Returns:
            Dict with S3-compatible response
        """
        try:
            # Generate S3-compatible path
            file_extension = filename.split('.')[-1].lower()
            s3_key = f"maps/originals/{map_id}/map.{file_extension}"
            
            # Local storage path (maintains S3 structure)
            local_path = os.path.join(self.local_storage_path, s3_key)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Save file
            with open(local_path, 'wb') as f:
                f.write(file_data)
            
            # Generate response with future S3 endpoint structure
            response = {
                'url': f"{self.local_endpoint}/{s3_key}",
                's3_endpoint': f"https://s3-{self.region}.amazonaws.com/{self.bucket_name}/{s3_key}",
                'key': s3_key,
                'bucket': self.bucket_name,
                'size': len(file_data),
                'etag': self._generate_etag(file_data),
                'content_type': content_type or 'application/octet-stream',
                'uploaded_at': datetime.now(timezone.utc).isoformat(),
                'storage_type': 'local'  # Will be 's3' in production
            }
            
            logger.info(f"Map uploaded: {s3_key} ({len(file_data)} bytes)")
            return response
            
        except Exception as e:
            logger.error(f"Map upload failed: {e}")
            raise Exception(f"Storage error: {str(e)}")
    
    def generate_tiles(
        self, 
        file_data: bytes, 
        map_id: str, 
        zoom_levels: List[int]
    ) -> Dict[str, Any]:
        """
        Generate map tiles with S3-compatible path structure.
        
        S3 Path Format: maps/tiles/{map_id}/z{zoom}/x{x}_y{y}.png
        
        Args:
            file_data: Original map image data
            map_id: Map identifier
            zoom_levels: List of zoom levels to generate
            
        Returns:
            Dict with tile information and endpoints
        """
        try:
            tile_manifest = {
                'map_id': map_id,
                'tiles': [],
                'zoom_levels': zoom_levels,
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Convert bytes to PIL Image
            image = Image.open(BytesIO(file_data))
            width, height = image.size
            
            for zoom in zoom_levels:
                # Calculate tile grid
                tile_size = 256
                tiles_x = max(1, min(4, math.ceil(width / tile_size)))
                tiles_y = max(1, min(4, math.ceil(height / tile_size)))
                
                for x in range(tiles_x):
                    for y in range(tiles_y):
                        # Generate tile
                        tile_info = self._generate_tile(
                            image, map_id, zoom, x, y, tile_size
                        )
                        
                        if tile_info:
                            tile_manifest['tiles'].append(tile_info)
            
            # Save manifest
            manifest_path = os.path.join(
                self.local_storage_path, 
                f"maps/tiles/{map_id}/manifest.json"
            )
            os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
            
            with open(manifest_path, 'w') as f:
                json.dump(tile_manifest, f, indent=2)
            
            logger.info(f"Generated {len(tile_manifest['tiles'])} tiles for map {map_id}")
            
            return {
                'tiles': tile_manifest['tiles'],
                'manifest_url': f"{self.local_endpoint}/maps/tiles/{map_id}/manifest.json",
                'total_tiles': len(tile_manifest['tiles']),
                'zoom_levels': zoom_levels
            }
            
        except Exception as e:
            logger.error(f"Tile generation failed: {e}")
            return {'tiles': [], 'error': str(e)}
    
    def _generate_tile(
        self, 
        image: Image.Image, 
        map_id: str, 
        zoom: int, 
        x: int, 
        y: int,
        tile_size: int = 256
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a single tile with S3-compatible metadata.
        
        Returns:
            Tile information with paths and endpoints
        """
        try:
            # Calculate crop boundaries
            left = x * tile_size
            top = y * tile_size
            right = min(left + tile_size, image.width)
            bottom = min(top + tile_size, image.height)
            
            if left >= image.width or top >= image.height:
                return None
            
            # Crop and pad tile
            tile = image.crop((left, top, right, bottom))
            if tile.size != (tile_size, tile_size):
                padded = Image.new('RGB', (tile_size, tile_size), (255, 255, 255))
                padded.paste(tile, (0, 0))
                tile = padded
            
            # S3-compatible path
            s3_key = f"maps/tiles/{map_id}/z{zoom}/x{x}_y{y}.png"
            local_path = os.path.join(self.local_storage_path, s3_key)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Save tile
            tile.save(local_path, 'PNG', optimize=True)
            
            # Return tile information
            return {
                'zoom': zoom,
                'x': x,
                'y': y,
                'path': s3_key,
                'url': f"{self.local_endpoint}/{s3_key}",
                's3_endpoint': f"https://s3-{self.region}.amazonaws.com/{self.bucket_name}/{s3_key}",
                'size': os.path.getsize(local_path)
            }
            
        except Exception as e:
            logger.warning(f"Failed to generate tile z{zoom}/x{x}/y{y}: {e}")
            return None
    
    def save_route(
        self, 
        route_id: str, 
        route_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save route data with S3-compatible structure.
        
        Routes are saved as JSON with path coordinates and S3 endpoints.
        
        Args:
            route_id: Route identifier
            route_data: Route information including path coordinates
            
        Returns:
            Dict with route storage information
        """
        try:
            # S3-compatible path for route
            s3_key = f"routes/{route_id}/route.json"
            local_path = os.path.join(self.local_storage_path, s3_key)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Prepare route data with S3 endpoint information
            stored_route = {
                'id': route_id,
                'name': route_data.get('name'),
                'type': route_data.get('route_type'),
                'path': route_data.get('path', []),  # List of [lng, lat] coordinates
                'distance_meters': route_data.get('distance_meters'),
                'estimated_time_seconds': route_data.get('estimated_time_seconds'),
                'metadata': {
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'storage_path': s3_key,
                    'endpoint': f"{self.local_endpoint}/{s3_key}",
                    's3_endpoint': f"https://s3-{self.region}.amazonaws.com/{self.bucket_name}/{s3_key}"
                }
            }
            
            # Save route JSON
            with open(local_path, 'w') as f:
                json.dump(stored_route, f, indent=2)
            
            logger.info(f"Route saved: {s3_key}")
            
            return {
                'route_id': route_id,
                'path': s3_key,
                'url': f"{self.local_endpoint}/{s3_key}",
                's3_endpoint': stored_route['metadata']['s3_endpoint'],
                'size': os.path.getsize(local_path),
                'storage_type': 'local'
            }
            
        except Exception as e:
            logger.error(f"Failed to save route {route_id}: {e}")
            raise Exception(f"Route storage error: {str(e)}")
    
    def get_route(self, route_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve route data with path and S3 endpoint information.
        
        Args:
            route_id: Route identifier
            
        Returns:
            Route data with coordinates and endpoints
        """
        try:
            s3_key = f"routes/{route_id}/route.json"
            local_path = os.path.join(self.local_storage_path, s3_key)
            
            if not os.path.exists(local_path):
                return None
            
            with open(local_path, 'r') as f:
                route_data = json.load(f)
            
            # Add current endpoint information
            route_data['current_endpoint'] = f"{self.local_endpoint}/{s3_key}"
            
            return route_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve route {route_id}: {e}")
            return None
    
    def list_routes(self) -> List[Dict[str, Any]]:
        """
        List all stored routes with their endpoints.
        
        Returns:
            List of route summaries with path and endpoint information
        """
        try:
            routes = []
            routes_dir = os.path.join(self.local_storage_path, 'routes')
            
            if os.path.exists(routes_dir):
                for route_id in os.listdir(routes_dir):
                    route_data = self.get_route(route_id)
                    if route_data:
                        routes.append({
                            'id': route_id,
                            'name': route_data.get('name'),
                            'type': route_data.get('type'),
                            'path_count': len(route_data.get('path', [])),
                            'endpoint': route_data.get('current_endpoint'),
                            's3_endpoint': route_data.get('metadata', {}).get('s3_endpoint')
                        })
            
            return routes
            
        except Exception as e:
            logger.error(f"Failed to list routes: {e}")
            return []
    
    def get_signed_url(
        self, 
        key: str, 
        expiration: int = 3600
    ) -> str:
        """
        Generate signed URL (simulated for local storage).
        
        In production, will generate actual S3 presigned URLs.
        
        Args:
            key: Storage key/path
            expiration: URL expiration in seconds
            
        Returns:
            Signed URL (local endpoint for now)
        """
        # For local storage, return direct URL
        # In production, use boto3 to generate presigned S3 URL
        timestamp = int(datetime.now(timezone.utc).timestamp())
        return f"{self.local_endpoint}/{key}?expires={timestamp + expiration}"
    
    def _generate_etag(self, data: bytes) -> str:
        """Generate ETag (entity tag) for file data."""
        return hashlib.md5(data).hexdigest()
    
    def cleanup_old_files(self, days: int = 30) -> int:
        """
        Clean up old files (future maintenance function).
        
        Args:
            days: Delete files older than this many days
            
        Returns:
            Number of files deleted
        """
        # Placeholder for future S3 lifecycle policy implementation
        logger.info(f"Cleanup policy: Delete files older than {days} days")
        return 0


# Global service instance
s3_service = S3Service()


def get_s3_service() -> S3Service:
    """Get S3 service instance."""
    return s3_service