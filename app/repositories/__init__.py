"""
Repository layer for data access abstraction.

Provides clean interfaces for database operations with:
- CRUD operations
- Complex queries
- Business logic separation
- Transaction management
"""
from app.repositories.map_repository import MapRepository

__all__ = [
    "MapRepository",
]