"""
Redis cache wrapper with safe JSON serialization and connection management.
"""
import json
import logging
import pickle
from typing import Any, Optional, Union, Dict
from datetime import datetime, timedelta
import redis
from flask import current_app
import functools

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis cache manager with JSON serialization and connection pooling."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self._redis_client = None
        self._connection_pool = None
    
    @property
    def redis_client(self) -> redis.Redis:
        """Get Redis client with connection pooling."""
        if self._redis_client is None:
            redis_url = self.redis_url or current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
            
            # Create connection pool
            self._connection_pool = redis.ConnectionPool.from_url(
                redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            self._redis_client = redis.Redis(
                connection_pool=self._connection_pool,
                decode_responses=True
            )
        
        return self._redis_client
    
    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        try:
            if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
                return json.dumps(value, default=str)
            else:
                # For complex objects, use pickle as fallback
                return pickle.dumps(value).hex()
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize value: {e}")
            raise
    
    def _deserialize(self, value: str) -> Any:
        """Deserialize JSON string to value."""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            try:
                # Try pickle deserialization for complex objects
                return pickle.loads(bytes.fromhex(value))
            except (ValueError, pickle.PickleError) as e:
                logger.error(f"Failed to deserialize value: {e}")
                return None
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        try:
            value = self.redis_client.get(key)
            if value is None:
                return default
            return self._deserialize(value)
        except redis.RedisError as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL in seconds."""
        try:
            serialized_value = self._serialize(value)
            return self.redis_client.set(key, serialized_value, ex=ttl)
        except (redis.RedisError, Exception) as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            return bool(self.redis_client.delete(key))
        except redis.RedisError as e:
            logger.error(f"Redis DELETE error for key '{key}': {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(self.redis_client.exists(key))
        except redis.RedisError as e:
            logger.error(f"Redis EXISTS error for key '{key}': {e}")
            return False
    
    def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key."""
        try:
            return bool(self.redis_client.expire(key, ttl))
        except redis.RedisError as e:
            logger.error(f"Redis EXPIRE error for key '{key}': {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment numeric value in cache."""
        try:
            return self.redis_client.incr(key, amount)
        except redis.RedisError as e:
            logger.error(f"Redis INCR error for key '{key}': {e}")
            return None
    
    def hash_get(self, name: str, key: str, default: Any = None) -> Any:
        """Get value from Redis hash."""
        try:
            value = self.redis_client.hget(name, key)
            if value is None:
                return default
            return self._deserialize(value)
        except redis.RedisError as e:
            logger.error(f"Redis HGET error for hash '{name}', key '{key}': {e}")
            return default
    
    def hash_set(self, name: str, key: str, value: Any) -> bool:
        """Set value in Redis hash."""
        try:
            serialized_value = self._serialize(value)
            return bool(self.redis_client.hset(name, key, serialized_value))
        except (redis.RedisError, Exception) as e:
            logger.error(f"Redis HSET error for hash '{name}', key '{key}': {e}")
            return False
    
    def hash_get_all(self, name: str) -> Dict[str, Any]:
        """Get all values from Redis hash."""
        try:
            hash_data = self.redis_client.hgetall(name)
            return {k: self._deserialize(v) for k, v in hash_data.items()}
        except redis.RedisError as e:
            logger.error(f"Redis HGETALL error for hash '{name}': {e}")
            return {}
    
    def list_push(self, key: str, *values) -> Optional[int]:
        """Push values to Redis list."""
        try:
            serialized_values = [self._serialize(v) for v in values]
            return self.redis_client.lpush(key, *serialized_values)
        except (redis.RedisError, Exception) as e:
            logger.error(f"Redis LPUSH error for key '{key}': {e}")
            return None
    
    def list_pop(self, key: str) -> Any:
        """Pop value from Redis list."""
        try:
            value = self.redis_client.rpop(key)
            if value is None:
                return None
            return self._deserialize(value)
        except redis.RedisError as e:
            logger.error(f"Redis RPOP error for key '{key}': {e}")
            return None
    
    def flush_db(self) -> bool:
        """Flush current database (use with caution)."""
        try:
            return self.redis_client.flushdb()
        except redis.RedisError as e:
            logger.error(f"Redis FLUSHDB error: {e}")
            return False
    
    def ping(self) -> bool:
        """Check Redis connection."""
        try:
            return self.redis_client.ping()
        except redis.RedisError as e:
            logger.error(f"Redis PING error: {e}")
            return False


# Global cache instance
cache = CacheManager()


def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator to cache function results."""
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cache set for key: {cache_key}")
            
            return result
        
        return wrapper
    return decorator


def cache_key(*parts) -> str:
    """Generate cache key from parts."""
    return ":".join(str(part) for part in parts)


def init_cache(app):
    """Initialize cache with Flask app."""
    cache.redis_url = app.config.get('REDIS_URL')
    
    # Test connection
    if not cache.ping():
        logger.warning("Redis connection failed during initialization")
    else:
        logger.info("Redis cache initialized successfully")

