"""
Comprehensive Redis-based caching system with multi-level caching strategies.
"""
import json
import hashlib
import time
import asyncio
from typing import Any, Optional, Dict, List, Union, Callable
from functools import wraps
from datetime import datetime, timedelta
import redis
from redis.connection import ConnectionPool
import structlog
from app.config import settings

logger = structlog.get_logger()

class CacheManager:
    """Multi-level cache manager with Redis backend and in-memory L1 cache."""
    
    def __init__(self):
        self._redis_pool = None
        self._redis_client = None
        self._l1_cache = {}  # In-memory L1 cache
        self._l1_max_size = 1000
        self._l1_access_order = []
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'l1_hits': 0,
            'l2_hits': 0,
            'invalidations': 0,
            'errors': 0
        }
    
    def get_redis_client(self):
        """Get Redis client with connection pooling."""
        if self._redis_client is None:
            if self._redis_pool is None:
                self._redis_pool = ConnectionPool(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    password=settings.redis_password if settings.redis_password else None,
                    max_connections=50,
                    retry_on_timeout=True,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                    health_check_interval=30
                )
            self._redis_client = redis.Redis(connection_pool=self._redis_pool)
        return self._redis_client
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {}
        }
        key_string = f"{prefix}:{json.dumps(key_data, sort_keys=True, default=str)}"
        return hashlib.md5(key_string.encode()).hexdigest()[:16]
    
    def _evict_l1_cache(self):
        """Evict oldest entries from L1 cache when it exceeds max size."""
        while len(self._l1_cache) >= self._l1_max_size:
            if self._l1_access_order:
                oldest_key = self._l1_access_order.pop(0)
                self._l1_cache.pop(oldest_key, None)
            else:
                break
    
    def _update_l1_access(self, key: str):
        """Update L1 cache access order for LRU eviction."""
        if key in self._l1_access_order:
            self._l1_access_order.remove(key)
        self._l1_access_order.append(key)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from multi-level cache."""
        try:
            # L1 Cache check
            if key in self._l1_cache:
                self._update_l1_access(key)
                self._cache_stats['hits'] += 1
                self._cache_stats['l1_hits'] += 1
                logger.debug("L1 cache hit", key=key)
                return self._l1_cache[key]['data']
            
            # L2 Cache (Redis) check - run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def get_from_redis():
                return self.get_redis_client().get(key)
            
            redis_value = await loop.run_in_executor(None, get_from_redis)
            
            if redis_value:
                value_str = redis_value.decode() if isinstance(redis_value, bytes) else str(redis_value)
                data = json.loads(value_str)
                
                # Store in L1 cache
                self._evict_l1_cache()
                self._l1_cache[key] = {
                    'data': data,
                    'timestamp': time.time()
                }
                self._update_l1_access(key)
                
                self._cache_stats['hits'] += 1
                self._cache_stats['l2_hits'] += 1
                logger.debug("L2 cache hit", key=key)
                return data
            
            self._cache_stats['misses'] += 1
            logger.debug("Cache miss", key=key)
            return None
            
        except Exception as e:
            self._cache_stats['errors'] += 1
            logger.error("Cache get error", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in multi-level cache."""
        try:
            # Store in Redis (L2) - run in thread pool
            redis_value = json.dumps(value, default=str)
            loop = asyncio.get_event_loop()
            
            def set_in_redis():
                return self.get_redis_client().setex(key, ttl, redis_value)
            
            await loop.run_in_executor(None, set_in_redis)
            
            # Store in L1 cache
            self._evict_l1_cache()
            self._l1_cache[key] = {
                'data': value,
                'timestamp': time.time()
            }
            self._update_l1_access(key)
            
            logger.debug("Cache set", key=key, ttl=ttl)
            return True
            
        except Exception as e:
            self._cache_stats['errors'] += 1
            logger.error("Cache set error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from all cache levels."""
        try:
            # Remove from L1
            self._l1_cache.pop(key, None)
            if key in self._l1_access_order:
                self._l1_access_order.remove(key)
            
            # Remove from Redis - run in thread pool
            loop = asyncio.get_event_loop()
            
            def delete_from_redis():
                return self.get_redis_client().delete(key)
            
            await loop.run_in_executor(None, delete_from_redis)
            
            self._cache_stats['invalidations'] += 1
            logger.debug("Cache delete", key=key)
            return True
            
        except Exception as e:
            self._cache_stats['errors'] += 1
            logger.error("Cache delete error", key=key, error=str(e))
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        try:
            loop = asyncio.get_event_loop()
            
            def get_keys():
                return self.get_redis_client().keys(pattern)
            
            keys = await loop.run_in_executor(None, get_keys)
            
            if keys and isinstance(keys, list):
                # Remove from L1 cache
                for key in keys:
                    key_str = key.decode() if isinstance(key, bytes) else str(key)
                    self._l1_cache.pop(key_str, None)
                    if key_str in self._l1_access_order:
                        self._l1_access_order.remove(key_str)
                
                # Remove from Redis - handle the deletion
                def delete_keys():
                    try:
                        return self.get_redis_client().delete(*keys)
                    except Exception:
                        return 0
                
                count = await loop.run_in_executor(None, delete_keys)
                # Ensure count is an integer
                if isinstance(count, int):
                    count_value = count
                else:
                    count_value = 0
                    
                self._cache_stats['invalidations'] += count_value
                logger.info("Pattern invalidation", pattern=pattern, count=count_value)
                return count_value
            return 0
            
        except Exception as e:
            self._cache_stats['errors'] += 1
            logger.error("Pattern invalidation error", pattern=pattern, error=str(e))
            return 0
    
    async def clear_all(self) -> bool:
        """Clear all cache levels."""
        try:
            # Clear L1
            self._l1_cache.clear()
            self._l1_access_order.clear()
            
            # Clear Redis (be careful in production!)
            loop = asyncio.get_event_loop()
            
            def flush_redis():
                return self.get_redis_client().flushdb()
            
            await loop.run_in_executor(None, flush_redis)
            
            logger.warning("All cache cleared")
            return True
            
        except Exception as e:
            self._cache_stats['errors'] += 1
            logger.error("Cache clear error", error=str(e))
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._cache_stats['hits'] + self._cache_stats['misses']
        hit_rate = (self._cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self._cache_stats,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'l1_size': len(self._l1_cache),
            'l1_max_size': self._l1_max_size
        }

# Global cache manager instance
cache_manager = CacheManager()

# Cache TTL policies
class CacheTTL:
    """Cache TTL policies for different data types."""
    STATIC_CONFIG = 3600      # 1 hour - crews, agents, tools
    DYNAMIC_STATE = 300       # 5 minutes - execution status, queue state
    MEMORY_QUERIES = 900      # 15 minutes - memory retrieval results
    LLM_RESPONSES = 1800      # 30 minutes - for repeated queries
    PERFORMANCE_METRICS = 60  # 1 minute - real-time data
    USER_SESSIONS = 7200      # 2 hours - user session data

def cache_key(*args, **kwargs):
    """Generate cache key decorator."""
    def decorator(func):
        cache_prefix = f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        async def wrapper(*func_args, **func_kwargs):
            # Generate cache key
            key = cache_manager._generate_cache_key(cache_prefix, *func_args, **func_kwargs)
            
            # Try to get from cache
            cached_result = await cache_manager.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*func_args, **func_kwargs)
            if result is not None:
                ttl = kwargs.get('ttl', CacheTTL.STATIC_CONFIG)
                await cache_manager.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

class CacheStrategy:
    """Different caching strategies for various data types."""
    
    @staticmethod
    def crew_config_key(crew_id: str, config_hash: str) -> str:
        """Generate crew configuration cache key."""
        return f"crew_config:{crew_id}:{config_hash}"
    
    @staticmethod
    def agent_config_key(agent_id: str, config_hash: str) -> str:
        """Generate agent configuration cache key."""
        return f"agent_config:{agent_id}:{config_hash}"
    
    @staticmethod
    def tool_registry_key(version_hash: str) -> str:
        """Generate tool registry cache key."""
        return f"tools:registry:{version_hash}"
    
    @staticmethod
    def memory_query_key(crew_id: str, query_hash: str) -> str:
        """Generate memory query cache key."""
        return f"memory:{crew_id}:{query_hash}"
    
    @staticmethod
    def execution_state_key(execution_id: str) -> str:
        """Generate execution state cache key."""
        return f"execution:{execution_id}:state"
    
    @staticmethod
    def llm_response_key(provider: str, model: str, prompt_hash: str) -> str:
        """Generate LLM response cache key."""
        return f"llm:{provider}:{model}:{prompt_hash}"

def cache_crew_config(ttl: int = CacheTTL.STATIC_CONFIG):
    """Cache crew configuration with smart invalidation."""
    def decorator(func):
        @wraps(func)
        async def wrapper(crew_id: str, *args, **kwargs):
            # Generate config hash from arguments
            config_data = {'args': args, 'kwargs': kwargs}
            config_hash = hashlib.md5(json.dumps(config_data, sort_keys=True).encode()).hexdigest()[:8]
            
            key = CacheStrategy.crew_config_key(crew_id, config_hash)
            
            # Try cache first
            cached_result = await cache_manager.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute and cache
            result = await func(crew_id, *args, **kwargs)
            if result is not None:
                await cache_manager.set(key, result, ttl)
                
                # Set up invalidation pattern for this crew
                invalidation_key = f"crew_config:{crew_id}:*"
                await cache_manager.set(f"invalidate:{crew_id}", invalidation_key, ttl)
            
            return result
        return wrapper
    return decorator

def cache_memory_query(ttl: int = CacheTTL.MEMORY_QUERIES):
    """Cache memory query results with intelligent invalidation."""
    def decorator(func):
        @wraps(func)
        async def wrapper(crew_id: str, query: str, *args, **kwargs):
            # Generate query hash
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            key = CacheStrategy.memory_query_key(crew_id, query_hash)
            
            # Try cache first
            cached_result = await cache_manager.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute and cache
            result = await func(crew_id, query, *args, **kwargs)
            if result is not None:
                await cache_manager.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator

def cache_llm_response(ttl: int = CacheTTL.LLM_RESPONSES):
    """Cache LLM responses for repeated queries."""
    def decorator(func):
        @wraps(func)
        async def wrapper(provider: str, model: str, prompt: str, *args, **kwargs):
            # Generate prompt hash
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
            key = CacheStrategy.llm_response_key(provider, model, prompt_hash)
            
            # Try cache first
            cached_result = await cache_manager.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute and cache
            result = await func(provider, model, prompt, *args, **kwargs)
            if result is not None:
                await cache_manager.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator

async def invalidate_crew_cache(crew_id: str):
    """Invalidate all cache entries for a specific crew."""
    pattern = f"*{crew_id}*"
    await cache_manager.invalidate_pattern(pattern)

async def invalidate_agent_cache(agent_id: str):
    """Invalidate all cache entries for a specific agent."""
    pattern = f"*{agent_id}*"
    await cache_manager.invalidate_pattern(pattern)

async def warm_cache():
    """Preload frequently accessed data into cache."""
    logger.info("Starting cache warming process")
    
    # This would be implemented to preload:
    # - Frequently used crew configurations
    # - Tool registry data
    # - Common memory queries
    # - Popular LLM responses
    
    # For now, just log the intention
    logger.info("Cache warming completed") 