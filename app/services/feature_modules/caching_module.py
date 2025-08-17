"""
Caching Feature Module

Provides Redis-based caching capabilities with decorators,
cache invalidation, and performance monitoring.
"""

from typing import List, Optional, Dict, Any
from app.services.feature_modules import BaseFeatureModule, FeatureModule, FeatureModuleFactory


class CachingFeatureModule(BaseFeatureModule):
    """Caching feature module implementation"""
    
    def get_dependencies(self) -> List[str]:
        return [
            "redis==5.0.1",
            "aioredis==2.0.1",
            "python-json-logger==2.0.7"
        ]
    
    def get_environment_vars(self) -> List[str]:
        return [
            "REDIS_URL",
            "CACHE_TTL",
            "CACHE_PREFIX",
            "REDIS_MAX_CONNECTIONS"
        ]
    
    def generate_service_code(self) -> str:
        return '''"""
Cache Service

Provides Redis-based caching with decorators and utilities.
"""

import json
import pickle
import hashlib
from functools import wraps
from typing import Any, Optional, Union, Callable
import aioredis
from app.core.config import settings

class CacheService:
    """Redis-based cache service"""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.default_ttl = settings.CACHE_TTL
        self.prefix = settings.CACHE_PREFIX
        self.redis_pool = None
    
    async def init_redis(self):
        """Initialize Redis connection pool"""
        if not self.redis_pool:
            self.redis_pool = aioredis.from_url(
                self.redis_url,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True
            )
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_pool:
            await self.redis_pool.close()
    
    def _make_key(self, key: str) -> str:
        """Create prefixed cache key"""
        return f"{self.prefix}:{key}"
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for storage"""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps(value)
        else:
            # Use pickle for complex objects
            return pickle.dumps(value).hex()
    
    def _deserialize_value(self, value: str) -> Any:
        """Deserialize value from storage"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            # Try pickle deserialization
            try:
                return pickle.loads(bytes.fromhex(value))
            except (ValueError, pickle.UnpicklingError):
                return value
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        await self.init_redis()
        cache_key = self._make_key(key)
        
        try:
            value = await self.redis_pool.get(cache_key)
            if value is not None:
                return self._deserialize_value(value)
            return None
        except Exception:
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache"""
        await self.init_redis()
        cache_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        
        try:
            serialized_value = self._serialize_value(value)
            await self.redis_pool.setex(cache_key, ttl, serialized_value)
            return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        await self.init_redis()
        cache_key = self._make_key(key)
        
        try:
            result = await self.redis_pool.delete(cache_key)
            return result > 0
        except Exception:
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        await self.init_redis()
        pattern_key = self._make_key(pattern)
        
        try:
            keys = await self.redis_pool.keys(pattern_key)
            if keys:
                return await self.redis_pool.delete(*keys)
            return 0
        except Exception:
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        await self.init_redis()
        cache_key = self._make_key(key)
        
        try:
            return await self.redis_pool.exists(cache_key) > 0
        except Exception:
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key"""
        await self.init_redis()
        cache_key = self._make_key(key)
        
        try:
            return await self.redis_pool.expire(cache_key, ttl)
        except Exception:
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter"""
        await self.init_redis()
        cache_key = self._make_key(key)
        
        try:
            return await self.redis_pool.incrby(cache_key, amount)
        except Exception:
            return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        await self.init_redis()
        
        try:
            info = await self.redis_pool.info()
            pattern_key = self._make_key("*")
            keys = await self.redis_pool.keys(pattern_key)
            
            return {
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_keys": len(keys)
            }
        except Exception:
            return {}
    
    async def clear_all(self) -> bool:
        """Clear all cache keys with prefix"""
        pattern_key = self._make_key("*")
        deleted = await self.delete_pattern(pattern_key.replace(f"{self.prefix}:", ""))
        return deleted > 0

# Cache decorators
def cache_result(ttl: int = 300, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, ttl)
            return result
            
        return wrapper
    return decorator

def invalidate_cache(key_pattern: str):
    """Decorator to invalidate cache after function execution"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            await cache_service.delete_pattern(key_pattern)
            return result
        return wrapper
    return decorator

# Global cache service instance
cache_service = CacheService()
'''
    
    def generate_router_code(self) -> str:
        return '''"""
Cache Router

Provides endpoints for cache management and statistics.
"""

from fastapi import APIRouter, HTTPException, status
from app.services.cache_service import cache_service
from app.schemas.cache import CacheStats, CacheSetRequest, CacheResponse

router = APIRouter(prefix="/cache", tags=["cache"])

@router.get("/stats", response_model=CacheStats)
async def get_cache_stats():
    """Get cache statistics"""
    stats = await cache_service.get_stats()
    return CacheStats(**stats)

@router.get("/get/{key}")
async def get_cache_value(key: str):
    """Get value from cache"""
    value = await cache_service.get(key)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found in cache"
        )
    return {"key": key, "value": value}

@router.post("/set", response_model=CacheResponse)
async def set_cache_value(request: CacheSetRequest):
    """Set value in cache"""
    success = await cache_service.set(
        request.key, 
        request.value, 
        request.ttl
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set cache value"
        )
    
    return CacheResponse(
        success=True,
        message=f"Key '{request.key}' set successfully"
    )

@router.delete("/delete/{key}")
async def delete_cache_key(key: str):
    """Delete key from cache"""
    success = await cache_service.delete(key)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found in cache"
        )
    
    return {"message": f"Key '{key}' deleted successfully"}

@router.delete("/clear-pattern/{pattern}")
async def clear_cache_pattern(pattern: str):
    """Clear cache keys matching pattern"""
    deleted_count = await cache_service.delete_pattern(pattern)
    return {
        "message": f"Deleted {deleted_count} keys matching pattern '{pattern}'"
    }

@router.delete("/clear-all")
async def clear_all_cache():
    """Clear all cache"""
    success = await cache_service.clear_all()
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )
    
    return {"message": "All cache cleared successfully"}

@router.post("/increment/{key}")
async def increment_counter(key: str, amount: int = 1):
    """Increment counter in cache"""
    new_value = await cache_service.increment(key, amount)
    
    if new_value is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to increment counter"
        )
    
    return {"key": key, "value": new_value}
'''
    
    def generate_middleware_code(self) -> Optional[str]:
        return '''"""
Cache Middleware

Provides caching middleware for HTTP responses.
"""

from fastapi import Request, Response
from app.services.cache_service import cache_service
import hashlib
import json

class CacheMiddleware:
    """Middleware for HTTP response caching"""
    
    def __init__(self, cache_ttl: int = 300):
        self.cache_ttl = cache_ttl
    
    def _should_cache(self, request: Request) -> bool:
        """Determine if request should be cached"""
        # Only cache GET requests
        if request.method != "GET":
            return False
        
        # Don't cache admin or auth endpoints
        excluded_paths = ["/admin/", "/auth/", "/cache/"]
        if any(request.url.path.startswith(path) for path in excluded_paths):
            return False
        
        # Don't cache if query params include no-cache
        if "no-cache" in request.query_params:
            return False
        
        return True
    
    def _make_cache_key(self, request: Request) -> str:
        """Generate cache key for request"""
        key_parts = [
            request.method,
            str(request.url),
            json.dumps(dict(request.query_params), sort_keys=True)
        ]
        return hashlib.md5(":".join(key_parts).encode()).hexdigest()
    
    async def __call__(self, request: Request, call_next):
        if not self._should_cache(request):
            return await call_next(request)
        
        cache_key = f"http_cache:{self._make_cache_key(request)}"
        
        # Try to get cached response
        cached_response = await cache_service.get(cache_key)
        if cached_response:
            return Response(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers=cached_response["headers"],
                media_type=cached_response["media_type"]
            )
        
        # Process request
        response = await call_next(request)
        
        # Cache successful responses
        if 200 <= response.status_code < 300:
            # Read response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            cached_data = {
                "content": response_body.decode(),
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "media_type": response.media_type
            }
            
            await cache_service.set(cache_key, cached_data, self.cache_ttl)
            
            # Return new response with body
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=response.headers,
                media_type=response.media_type
            )
        
        return response
'''
    
    def generate_schema_code(self) -> Optional[str]:
        return '''"""
Cache Schemas

Pydantic models for cache requests and responses.
"""

from pydantic import BaseModel
from typing import Any, Optional

class CacheStats(BaseModel):
    """Cache statistics schema"""
    redis_version: Optional[str] = None
    connected_clients: Optional[int] = None
    used_memory: Optional[int] = None
    used_memory_human: Optional[str] = None
    keyspace_hits: int = 0
    keyspace_misses: int = 0
    total_keys: int = 0

class CacheSetRequest(BaseModel):
    """Cache set request schema"""
    key: str
    value: Any
    ttl: Optional[int] = None

class CacheResponse(BaseModel):
    """Cache operation response schema"""
    success: bool
    message: str

class CacheKeyInfo(BaseModel):
    """Cache key information schema"""
    key: str
    exists: bool
    ttl: Optional[int] = None
'''
    
    def get_models(self) -> List[Dict[str, Any]]:
        return [{
            "name": "CacheEntry",
            "fields": [
                {"name": "id", "type": "String", "constraints": ["primary_key"]},
                {"name": "cache_key", "type": "String(255)", "constraints": ["unique", "required"]},
                {"name": "value", "type": "Text", "constraints": ["required"]},
                {"name": "ttl", "type": "Integer", "constraints": []},
                {"name": "created_at", "type": "DateTime", "constraints": []},
                {"name": "expires_at", "type": "DateTime", "constraints": []},
                {"name": "hit_count", "type": "Integer", "constraints": [], "default": 0}
            ]
        }]
    
    def get_endpoints(self) -> List[Dict[str, Any]]:
        return [
            {"path": "/cache/stats", "method": "GET", "description": "Get cache statistics"},
            {"path": "/cache/get/{key}", "method": "GET", "description": "Get cache value"},
            {"path": "/cache/set", "method": "POST", "description": "Set cache value"},
            {"path": "/cache/delete/{key}", "method": "DELETE", "description": "Delete cache key"},
            {"path": "/cache/clear-pattern/{pattern}", "method": "DELETE", "description": "Clear cache pattern"},
            {"path": "/cache/clear-all", "method": "DELETE", "description": "Clear all cache"},
            {"path": "/cache/increment/{key}", "method": "POST", "description": "Increment counter"}
        ]


# Register the module
FeatureModuleFactory.register(FeatureModule.CACHING, CachingFeatureModule)
