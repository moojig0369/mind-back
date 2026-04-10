"""
Redis connection and queue management.
Infrastructure layer for Redis operations.
"""

import redis
from typing import Optional
from app.core.settings import get_settings


class RedisClient:
    """Redis connection manager."""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
    
    def init(self, redis_url: str):
        """Initialize Redis connection."""
        self._client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    
    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            raise RuntimeError("Redis not initialized")
        return self._client
    
    def ping(self) -> bool:
        """Check Redis connection."""
        return self.client.ping()


# Global Redis instance
_redis_client = RedisClient()


def get_redis_connection() -> redis.Redis:
    """Get Redis connection instance."""
    return _redis_client.client


def get_analysis_queue() -> str:
    """Get the name of the analysis queue."""
    return "analysis"


def get_deep_insight_queue() -> str:
    """Get the name of the deep insight queue."""
    return "deep_insight"


def init_redis(redis_url: str):
    """Initialize Redis connection from settings."""
    _redis_client.init(redis_url)
