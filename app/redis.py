import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()

redis_pool = redis.ConnectionPool(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=True
)

def get_redis_connection():
    """Get a Redis connection from the pool."""
    return redis.Redis(connection_pool=redis_pool)
