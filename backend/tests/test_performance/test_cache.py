"""
Tests for cache functionality and strategies.
"""
import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from app.utils.cache import (
    CacheManager, cache_manager, CacheTTL, CacheStrategy,
    cache_key, cache_crew_config, cache_memory_query, cache_llm_response
)

class TestCacheManager:
    """Test the CacheManager class."""
    
    def setup_method(self):
        """Setup for each test."""
        # Create a fresh cache manager for each test
        self.cache = CacheManager()
        # Clear any existing data
        self.cache._l1_cache.clear()
        self.cache._l1_access_order.clear()
        self.cache._cache_stats = {
            'hits': 0,
            'misses': 0,
            'l1_hits': 0,
            'l2_hits': 0,
            'invalidations': 0,
            'errors': 0
        }
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        key1 = self.cache._generate_cache_key("test", "arg1", "arg2", kwarg1="value1")
        key2 = self.cache._generate_cache_key("test", "arg1", "arg2", kwarg1="value1")
        key3 = self.cache._generate_cache_key("test", "arg1", "arg3", kwarg1="value1")
        
        # Same arguments should generate same key
        assert key1 == key2
        # Different arguments should generate different key
        assert key1 != key3
        # Keys should be reasonable length (MD5 hash truncated)
        assert len(key1) == 16
    
    def test_l1_cache_operations(self):
        """Test L1 cache operations."""
        # Test setting and getting from L1 cache
        self.cache._l1_cache['test_key'] = {'data': 'test_value', 'timestamp': time.time()}
        self.cache._l1_access_order.append('test_key')
        
        # Update access order
        self.cache._update_l1_access('test_key')
        
        # Key should be moved to end of access order
        assert self.cache._l1_access_order[-1] == 'test_key'
    
    def test_l1_cache_eviction(self):
        """Test L1 cache LRU eviction."""
        # Fill cache to max capacity
        for i in range(1000):
            self.cache._l1_cache[f'key_{i}'] = {'data': f'value_{i}', 'timestamp': time.time()}
            self.cache._l1_access_order.append(f'key_{i}')
        
        # Add one more item to trigger eviction
        self.cache._evict_l1_cache()
        self.cache._l1_cache['new_key'] = {'data': 'new_value', 'timestamp': time.time()}
        self.cache._l1_access_order.append('new_key')
        
        # Cache should not exceed max size
        assert len(self.cache._l1_cache) <= 1000
        # First item should be evicted
        assert 'key_0' not in self.cache._l1_cache
        # New item should be present
        assert 'new_key' in self.cache._l1_cache
    
    @pytest.mark.asyncio
    async def test_cache_get_l1_hit(self):
        """Test cache get with L1 hit."""
        # Set up L1 cache
        test_data = {'test': 'value'}
        self.cache._l1_cache['test_key'] = {'data': test_data, 'timestamp': time.time()}
        self.cache._l1_access_order.append('test_key')
        
        result = await self.cache.get('test_key')
        
        assert result == test_data
        assert self.cache._cache_stats['hits'] == 1
        assert self.cache._cache_stats['l1_hits'] == 1
        assert self.cache._cache_stats['misses'] == 0
    
    @pytest.mark.asyncio
    async def test_cache_get_l2_hit(self):
        """Test cache get with L2 (Redis) hit."""
        test_data = {'test': 'value'}
        
        # Mock Redis to return data
        with patch.object(self.cache, 'get_redis_client') as mock_redis:
            mock_redis.return_value.get.return_value = json.dumps(test_data).encode()
            
            result = await self.cache.get('test_key')
            
            assert result == test_data
            assert self.cache._cache_stats['hits'] == 1
            assert self.cache._cache_stats['l2_hits'] == 1
            assert self.cache._cache_stats['l1_hits'] == 0
            # Data should now be in L1 cache too
            assert 'test_key' in self.cache._l1_cache
    
    @pytest.mark.asyncio
    async def test_cache_get_miss(self):
        """Test cache get with complete miss."""
        # Mock Redis to return None
        with patch.object(self.cache, 'get_redis_client') as mock_redis:
            mock_redis.return_value.get.return_value = None
            
            result = await self.cache.get('nonexistent_key')
            
            assert result is None
            assert self.cache._cache_stats['misses'] == 1
            assert self.cache._cache_stats['hits'] == 0
    
    @pytest.mark.asyncio
    async def test_cache_set(self):
        """Test cache set operation."""
        test_data = {'test': 'value'}
        
        # Mock Redis
        with patch.object(self.cache, 'get_redis_client') as mock_redis:
            mock_redis.return_value.setex.return_value = True
            
            result = await self.cache.set('test_key', test_data, 3600)
            
            assert result is True
            # Data should be in L1 cache
            assert 'test_key' in self.cache._l1_cache
            assert self.cache._l1_cache['test_key']['data'] == test_data
            # Redis should have been called
            mock_redis.return_value.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """Test cache delete operation."""
        # Set up cache with data
        self.cache._l1_cache['test_key'] = {'data': 'test_value', 'timestamp': time.time()}
        self.cache._l1_access_order.append('test_key')
        
        # Mock Redis
        with patch.object(self.cache, 'get_redis_client') as mock_redis:
            mock_redis.return_value.delete.return_value = 1
            
            result = await self.cache.delete('test_key')
            
            assert result is True
            # Data should be removed from L1 cache
            assert 'test_key' not in self.cache._l1_cache
            assert 'test_key' not in self.cache._l1_access_order
            assert self.cache._cache_stats['invalidations'] == 1
    
    @pytest.mark.asyncio
    async def test_cache_invalidate_pattern(self):
        """Test cache pattern invalidation."""
        # Set up L1 cache with matching keys
        self.cache._l1_cache['crew_123_config'] = {'data': 'value1', 'timestamp': time.time()}
        self.cache._l1_cache['crew_123_status'] = {'data': 'value2', 'timestamp': time.time()}
        self.cache._l1_cache['crew_456_config'] = {'data': 'value3', 'timestamp': time.time()}
        self.cache._l1_access_order.extend(['crew_123_config', 'crew_123_status', 'crew_456_config'])
        
        # Mock Redis
        with patch.object(self.cache, 'get_redis_client') as mock_redis:
            mock_redis.return_value.keys.return_value = [b'crew_123_config', b'crew_123_status']
            mock_redis.return_value.delete.return_value = 2
            
            count = await self.cache.invalidate_pattern('crew_123*')
            
            assert count == 2
            # Matching keys should be removed from L1
            assert 'crew_123_config' not in self.cache._l1_cache
            assert 'crew_123_status' not in self.cache._l1_cache
            # Non-matching key should remain
            assert 'crew_456_config' in self.cache._l1_cache
    
    @pytest.mark.asyncio
    async def test_cache_clear_all(self):
        """Test clearing all cache levels."""
        # Set up L1 cache with data
        self.cache._l1_cache['test_key'] = {'data': 'test_value', 'timestamp': time.time()}
        self.cache._l1_access_order.append('test_key')
        
        # Mock Redis
        with patch.object(self.cache, 'get_redis_client') as mock_redis:
            mock_redis.return_value.flushdb.return_value = True
            
            result = await self.cache.clear_all()
            
            assert result is True
            # L1 cache should be empty
            assert len(self.cache._l1_cache) == 0
            assert len(self.cache._l1_access_order) == 0
            # Redis flushdb should have been called
            mock_redis.return_value.flushdb.assert_called_once()
    
    def test_cache_stats(self):
        """Test cache statistics."""
        # Set up some stats
        self.cache._cache_stats['hits'] = 80
        self.cache._cache_stats['misses'] = 20
        self.cache._cache_stats['l1_hits'] = 50
        self.cache._cache_stats['l2_hits'] = 30
        
        stats = self.cache.get_stats()
        
        assert stats['hits'] == 80
        assert stats['misses'] == 20
        assert stats['total_requests'] == 100
        assert stats['hit_rate_percent'] == 80.0
        assert 'l1_size' in stats
        assert 'l1_max_size' in stats
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in cache operations."""
        # Mock Redis to raise exception
        with patch.object(self.cache, 'get_redis_client') as mock_redis:
            mock_redis.return_value.get.side_effect = Exception("Redis error")
            
            result = await self.cache.get('test_key')
            
            assert result is None
            assert self.cache._cache_stats['errors'] == 1

class TestCacheStrategies:
    """Test cache strategy functions."""
    
    def test_cache_strategy_keys(self):
        """Test cache strategy key generation."""
        crew_key = CacheStrategy.crew_config_key("crew_123", "abc123")
        agent_key = CacheStrategy.agent_config_key("agent_456", "def456")
        tool_key = CacheStrategy.tool_registry_key("ver123")
        memory_key = CacheStrategy.memory_query_key("crew_123", "query456")
        execution_key = CacheStrategy.execution_state_key("exec_789")
        llm_key = CacheStrategy.llm_response_key("openai", "gpt-4", "prompt123")
        
        assert crew_key == "crew_config:crew_123:abc123"
        assert agent_key == "agent_config:agent_456:def456"
        assert tool_key == "tools:registry:ver123"
        assert memory_key == "memory:crew_123:query456"
        assert execution_key == "execution:exec_789:state"
        assert llm_key == "llm:openai:gpt-4:prompt123"

class TestCacheDecorators:
    """Test cache decorator functions."""
    
    @pytest.mark.asyncio
    async def test_cache_key_decorator(self):
        """Test cache_key decorator."""
        # Mock cache manager with async methods
        with patch('app.utils.cache.cache_manager') as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock(return_value=True)
            mock_cache._generate_cache_key.return_value = "test_key"
            
            @cache_key(ttl=3600)
            async def test_function(arg1, arg2, kwarg1=None):
                return {"result": f"{arg1}_{arg2}_{kwarg1}"}
            
            result = await test_function("a", "b", kwarg1="c")
            
            assert result == {"result": "a_b_c"}
            mock_cache.get.assert_called_once_with("test_key")
            mock_cache.set.assert_called_once_with("test_key", {"result": "a_b_c"}, 3600)
    
    @pytest.mark.asyncio
    async def test_cache_crew_config_decorator(self):
        """Test cache_crew_config decorator."""
        with patch('app.utils.cache.cache_manager') as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock(return_value=True)
            
            @cache_crew_config()
            async def get_crew_config(crew_id, config_param=None):
                return {"crew_id": crew_id, "config": config_param}
            
            result = await get_crew_config("crew_123", config_param="test")
            
            assert result == {"crew_id": "crew_123", "config": "test"}
            # Should have called cache operations
            assert mock_cache.get.called
            assert mock_cache.set.called
    
    @pytest.mark.asyncio
    async def test_cache_memory_query_decorator(self):
        """Test cache_memory_query decorator."""
        with patch('app.utils.cache.cache_manager') as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock(return_value=True)
            
            @cache_memory_query()
            async def query_memory(crew_id, query, context=None):
                return {"crew_id": crew_id, "query": query, "results": ["result1", "result2"]}
            
            result = await query_memory("crew_123", "test query", context="test")
            
            assert result["query"] == "test query"
            assert result["results"] == ["result1", "result2"]
            # Should have called cache operations
            assert mock_cache.get.called
            assert mock_cache.set.called
    
    @pytest.mark.asyncio
    async def test_cache_llm_response_decorator(self):
        """Test cache_llm_response decorator."""
        with patch('app.utils.cache.cache_manager') as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock(return_value=True)
            
            @cache_llm_response()
            async def call_llm(provider, model, prompt, temperature=0.7):
                return {"response": f"Generated response for: {prompt}"}
            
            result = await call_llm("openai", "gpt-4", "Test prompt", temperature=0.8)
            
            assert "Generated response for: Test prompt" in result["response"]
            # Should have called cache operations
            assert mock_cache.get.called
            assert mock_cache.set.called

class TestCacheTTLPolicies:
    """Test cache TTL policies."""
    
    def test_cache_ttl_values(self):
        """Test TTL policy values."""
        assert CacheTTL.STATIC_CONFIG == 3600      # 1 hour
        assert CacheTTL.DYNAMIC_STATE == 300       # 5 minutes
        assert CacheTTL.MEMORY_QUERIES == 900      # 15 minutes
        assert CacheTTL.LLM_RESPONSES == 1800      # 30 minutes
        assert CacheTTL.PERFORMANCE_METRICS == 60  # 1 minute
        assert CacheTTL.USER_SESSIONS == 7200      # 2 hours

class TestCacheIntegration:
    """Integration tests for cache system."""
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_functions(self):
        """Test cache invalidation helper functions."""
        from app.utils.cache import invalidate_crew_cache, invalidate_agent_cache
        
        with patch('app.utils.cache.cache_manager') as mock_cache:
            mock_cache.invalidate_pattern = AsyncMock(return_value=5)
            
            # Test crew cache invalidation
            await invalidate_crew_cache("crew_123")
            mock_cache.invalidate_pattern.assert_called_with("*crew_123*")
            
            # Test agent cache invalidation
            await invalidate_agent_cache("agent_456")
            mock_cache.invalidate_pattern.assert_called_with("*agent_456*")
    
    @pytest.mark.asyncio
    async def test_cache_warming(self):
        """Test cache warming functionality."""
        from app.utils.cache import warm_cache
        
        # Should not raise any exceptions
        await warm_cache()
    
    def test_global_cache_manager(self):
        """Test global cache manager instance."""
        from app.utils.cache import cache_manager
        
        assert cache_manager is not None
        assert isinstance(cache_manager, CacheManager)
        assert hasattr(cache_manager, '_l1_cache')
        assert hasattr(cache_manager, '_cache_stats')

class TestCacheEdgeCases:
    """Test edge cases and error scenarios."""
    
    def setup_method(self):
        """Setup for each test."""
        self.cache = CacheManager()
    
    @pytest.mark.asyncio
    async def test_cache_with_none_values(self):
        """Test caching None values."""
        with patch.object(self.cache, 'get_redis_client') as mock_redis:
            mock_redis.return_value.setex.return_value = True
            
            # Should not cache None values
            result = await self.cache.set('test_key', None, 3600)
            
            assert result is True
            # None should be cached (might be valid result)
            assert 'test_key' in self.cache._l1_cache
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure(self):
        """Test handling Redis connection failures."""
        with patch.object(self.cache, 'get_redis_client') as mock_redis:
            mock_redis.side_effect = Exception("Connection failed")
            
            # Operations should handle exceptions gracefully
            result_get = await self.cache.get('test_key')
            result_set = await self.cache.set('test_key', 'value', 3600)
            result_delete = await self.cache.delete('test_key')
            
            assert result_get is None
            assert result_set is False
            assert result_delete is False
            assert self.cache._cache_stats['errors'] > 0
    
    def test_invalid_key_generation(self):
        """Test key generation with various input types."""
        # Should handle different data types
        key1 = self.cache._generate_cache_key("test", 123, [1, 2, 3], {"a": "b"})
        key2 = self.cache._generate_cache_key("test", 123, [1, 2, 3], {"a": "b"})
        
        assert key1 == key2
        assert len(key1) == 16
    
    def test_cache_stats_edge_cases(self):
        """Test cache statistics with edge cases."""
        # Test with zero requests
        stats = self.cache.get_stats()
        assert stats['hit_rate_percent'] == 0
        assert stats['total_requests'] == 0
        
        # Test with only misses
        self.cache._cache_stats['misses'] = 10
        stats = self.cache.get_stats()
        assert stats['hit_rate_percent'] == 0
        assert stats['total_requests'] == 10 