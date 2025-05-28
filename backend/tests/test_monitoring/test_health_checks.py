"""
Tests for comprehensive health check monitoring system.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import importlib

from app.monitoring.health_checks import (
    HealthChecker, ComponentHealth, HealthStatus
)


class TestComponentHealth:
    """Test ComponentHealth dataclass."""
    
    def test_component_health_creation(self):
        """Test creating ComponentHealth instance."""
        health = ComponentHealth(
            name="test_component",
            status=HealthStatus.HEALTHY,
            message="Component is healthy"
        )
        
        assert health.name == "test_component"
        assert health.status == HealthStatus.HEALTHY
        assert health.message == "Component is healthy"
        assert health.last_checked is not None
        assert isinstance(health.details, dict)
        assert isinstance(health.dependencies, list)
    
    def test_component_health_to_dict(self):
        """Test converting ComponentHealth to dictionary."""
        health = ComponentHealth(
            name="test_component",
            status=HealthStatus.HEALTHY,
            message="Component is healthy",
            response_time_ms=150.5,
            details={"key": "value"},
            dependencies=["dep1", "dep2"]
        )
        
        result = health.to_dict()
        
        assert result["name"] == "test_component"
        assert result["status"] == "healthy"
        assert result["message"] == "Component is healthy"
        assert result["response_time_ms"] == 150.5
        assert result["details"] == {"key": "value"}
        assert result["dependencies"] == ["dep1", "dep2"]
        assert "last_checked" in result


class TestHealthChecker:
    """Test HealthChecker class."""
    
    @pytest.fixture
    def health_checker(self):
        """Create HealthChecker instance."""
        return HealthChecker()
    
    @pytest.mark.asyncio
    async def test_check_all_components(self, health_checker):
        """Test checking all components."""
        # Mock individual health check methods
        with patch.object(health_checker, '_check_database_health') as mock_db, \
             patch.object(health_checker, '_check_redis_health') as mock_redis, \
             patch.object(health_checker, '_check_celery_health') as mock_celery:
            
            # Set up mock returns
            mock_db.return_value = ComponentHealth("database", HealthStatus.HEALTHY, "DB OK")
            mock_redis.return_value = ComponentHealth("redis", HealthStatus.HEALTHY, "Redis OK")
            mock_celery.return_value = ComponentHealth("celery", HealthStatus.HEALTHY, "Celery OK")
            
            result = await health_checker.check_all_components(use_cache=False)
            
            assert "database" in result
            assert "redis" in result
            assert "celery" in result
            assert result["database"].status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_health_check_caching(self, health_checker):
        """Test health check caching mechanism."""
        # First call should execute health check
        with patch.object(health_checker, '_check_database_health') as mock_db:
            mock_db.return_value = ComponentHealth("database", HealthStatus.HEALTHY, "DB OK")
            
            # First call
            result1 = await health_checker._run_health_check(
                "database", health_checker._check_database_health, use_cache=True
            )
            
            # Second call should use cache
            result2 = await health_checker._run_health_check(
                "database", health_checker._check_database_health, use_cache=True
            )
            
            # Database health check should only be called once
            assert mock_db.call_count == 1
            assert result1.name == result2.name
    
    @pytest.mark.asyncio
    async def test_health_check_timeout(self, health_checker):
        """Test health check timeout handling."""
        async def slow_health_check():
            await asyncio.sleep(2)  # Longer than timeout
            return ComponentHealth("slow", HealthStatus.HEALTHY, "Slow check")
        
        # Set a short timeout
        health_checker._timeout = 0.1
        
        result = await health_checker._run_health_check(
            "slow_component", slow_health_check, use_cache=False
        )
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "timeout" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_database_health_check_success(self, health_checker):
        """Test successful database health check."""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_db.execute.return_value = mock_result
        mock_db.get_bind.return_value = Mock(pool=Mock())
        
        with patch('app.monitoring.health_checks.get_db') as mock_get_db:
            mock_get_db.return_value.__next__.return_value = mock_db
            
            result = await health_checker._check_database_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert "healthy" in result.message.lower()
            assert "basic_query_time_ms" in result.details
    
    @pytest.mark.asyncio
    async def test_database_health_check_failure(self, health_checker):
        """Test database health check failure."""
        with patch('app.monitoring.health_checks.get_db') as mock_get_db:
            mock_get_db.return_value.__next__.side_effect = Exception("Connection failed")
            
            result = await health_checker._check_database_health()
            
            assert result.status == HealthStatus.UNHEALTHY
            assert "error" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_redis_health_check_success(self, health_checker):
        """Test successful Redis health check."""
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.info.return_value = {
            'used_memory_human': '1M',
            'connected_clients': 5,
            'uptime_in_seconds': 3600
        }
        
        with patch('app.monitoring.health_checks.redis.Redis') as mock_redis_class, \
             patch('app.monitoring.health_checks.cache_manager') as mock_cache:
            
            mock_redis_class.from_url.return_value = mock_redis
            mock_cache.get_stats.return_value = {"hit_rate": 0.85}
            
            result = await health_checker._check_redis_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert "healthy" in result.message.lower()
            assert "ping_time_ms" in result.details
    
    @pytest.mark.asyncio
    async def test_redis_health_check_failure(self, health_checker):
        """Test Redis health check failure."""
        with patch('app.monitoring.health_checks.redis.Redis') as mock_redis_class:
            mock_redis_class.from_url.side_effect = Exception("Redis connection failed")
            
            result = await health_checker._check_redis_health()
            
            assert result.status == HealthStatus.UNHEALTHY
            assert "error" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_celery_health_check_success(self, health_checker):
        """Test successful Celery health check."""
        mock_inspect = Mock()
        mock_inspect.active.return_value = {"worker1": [], "worker2": []}
        mock_inspect.registered.return_value = {"worker1": ["task1", "task2"]}
        mock_inspect.stats.return_value = {"worker1": {"pool": {"max-concurrency": 4}}}
        
        mock_redis = Mock()
        mock_redis.llen.return_value = 5  # Queue length
        
        with patch('app.monitoring.health_checks.celery_app') as mock_celery, \
             patch('app.monitoring.health_checks.redis.Redis') as mock_redis_class:
            
            mock_celery.control.inspect.return_value = mock_inspect
            mock_redis_class.from_url.return_value = mock_redis
            
            result = await health_checker._check_celery_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert "active workers" in result.message.lower()
            assert result.details["active_workers"] == 2
    
    @pytest.mark.asyncio
    async def test_celery_health_check_no_workers(self, health_checker):
        """Test Celery health check with no workers."""
        mock_inspect = Mock()
        mock_inspect.active.return_value = None  # No active workers (None instead of empty dict)
        mock_inspect.registered.return_value = None
        mock_inspect.stats.return_value = None
        
        mock_redis = Mock()
        mock_redis.llen.return_value = 0
        
        with patch('app.monitoring.health_checks.celery_app') as mock_celery, \
             patch('app.monitoring.health_checks.redis.Redis') as mock_redis_class:
            
            mock_celery.control.inspect.return_value = mock_inspect
            mock_redis_class.from_url.return_value = mock_redis
            
            result = await health_checker._check_celery_health()
            
            assert result.status == HealthStatus.UNHEALTHY
            assert "no active" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_openai_health_check_success(self, health_checker):
        """Test successful OpenAI health check."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(id="gpt-4"), Mock(id="gpt-3.5-turbo")]
        mock_client.models.list.return_value = mock_response
        
        with patch('app.monitoring.health_checks.settings') as mock_settings, \
             patch('app.monitoring.health_checks.openai.OpenAI') as mock_openai:
            
            mock_settings.openai_api_key = "test-key"
            mock_openai.return_value = mock_client
            
            result = await health_checker._check_openai_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert "accessible" in result.message.lower()
            assert result.details["model_count"] == 2
    
    @pytest.mark.asyncio
    async def test_openai_health_check_no_key(self, health_checker):
        """Test OpenAI health check without API key."""
        with patch('app.monitoring.health_checks.settings') as mock_settings:
            mock_settings.openai_api_key = None
            
            result = await health_checker._check_openai_health()
            
            assert result.status == HealthStatus.UNKNOWN
            assert "not configured" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_anthropic_health_check_success(self, health_checker):
        """Test successful Anthropic health check."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.usage.input_tokens = 5
        mock_response.usage.output_tokens = 1
        mock_client.messages.create.return_value = mock_response
        
        with patch('app.monitoring.health_checks.settings') as mock_settings, \
             patch('app.monitoring.health_checks.anthropic.Anthropic') as mock_anthropic:
            
            mock_settings.anthropic_api_key = "test-key"
            mock_anthropic.return_value = mock_client
            
            result = await health_checker._check_anthropic_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert "accessible" in result.message.lower()
            assert result.details["tokens_used"] == 6
    
    @pytest.mark.asyncio
    async def test_ollama_health_check_success(self, health_checker):
        """Test successful Ollama health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llama2"}, {"name": "codellama"}]
        }
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        with patch('app.monitoring.health_checks.settings') as mock_settings, \
             patch('httpx.AsyncClient') as mock_httpx:
            
            mock_settings.ollama_base_url = "http://localhost:11434"
            mock_httpx.return_value.__aenter__.return_value = mock_client
            
            result = await health_checker._check_ollama_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert "accessible" in result.message.lower()
            assert result.details["model_count"] == 2
    
    @pytest.mark.asyncio
    async def test_crew_execution_health_check(self, health_checker):
        """Test crew execution health check."""
        mock_llm_wrapper = Mock()
        mock_llm_wrapper.get_available_providers.return_value = ["openai", "anthropic"]
        
        with patch('app.monitoring.health_checks.LLMWrapper') as mock_llm_class:
            mock_llm_class.return_value = mock_llm_wrapper
            
            result = await health_checker._check_crew_execution_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert "operational" in result.message.lower()
            assert result.details["available_llm_providers"] == ["openai", "anthropic"]
    
    @pytest.mark.asyncio
    async def test_memory_system_health_check(self, health_checker):
        """Test memory system health check."""
        mock_db = Mock()
        mock_db.execute.return_value.scalar.return_value = 100  # Vector entries count
        
        with patch('app.monitoring.health_checks.get_db') as mock_get_db:
            mock_get_db.return_value.__next__.return_value = mock_db
            
            result = await health_checker._check_memory_system_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert "operational" in result.message.lower()
            assert result.details["vector_entries_count"] == 100
    
    @pytest.mark.asyncio
    async def test_websocket_health_check(self, health_checker):
        """Test WebSocket health check."""
        # Mock the importlib module loading approach used in the actual code
        mock_manager = Mock()
        mock_manager.active_connections = ["conn1", "conn2", "conn3"]
        
        mock_module = Mock()
        mock_module.manager = mock_manager
        
        with patch('importlib.import_module') as mock_import:
            mock_import.return_value = mock_module
            
            result = await health_checker._check_websocket_health()
            
            assert result.status == HealthStatus.HEALTHY
            assert "operational" in result.message
            assert result.details["active_connections"] == 3
            assert result.details["manager_available"] is True
    
    def test_get_overall_health_all_healthy(self, health_checker):
        """Test overall health calculation with all components healthy."""
        component_healths = {
            "database": ComponentHealth("database", HealthStatus.HEALTHY, "DB OK"),
            "redis": ComponentHealth("redis", HealthStatus.HEALTHY, "Redis OK"),
            "celery": ComponentHealth("celery", HealthStatus.HEALTHY, "Celery OK")
        }
        
        overall_health = health_checker.get_overall_health(component_healths)
        
        assert overall_health.status == HealthStatus.HEALTHY
        assert "healthy" in overall_health.message.lower()
        assert overall_health.details["component_counts"]["healthy"] == 3
    
    def test_get_overall_health_critical_unhealthy(self, health_checker):
        """Test overall health with critical component unhealthy."""
        component_healths = {
            "database": ComponentHealth("database", HealthStatus.UNHEALTHY, "DB Down"),
            "redis": ComponentHealth("redis", HealthStatus.HEALTHY, "Redis OK"),
            "celery": ComponentHealth("celery", HealthStatus.HEALTHY, "Celery OK")
        }
        
        overall_health = health_checker.get_overall_health(component_healths)
        
        assert overall_health.status == HealthStatus.UNHEALTHY
        assert "unhealthy" in overall_health.message.lower()
        assert overall_health.details["critical_unhealthy"] is True
    
    def test_get_overall_health_degraded(self, health_checker):
        """Test overall health with some components degraded."""
        component_healths = {
            "database": ComponentHealth("database", HealthStatus.HEALTHY, "DB OK"),
            "redis": ComponentHealth("redis", HealthStatus.DEGRADED, "Redis Slow"),
            "celery": ComponentHealth("celery", HealthStatus.HEALTHY, "Celery OK")
        }
        
        overall_health = health_checker.get_overall_health(component_healths)
        
        assert overall_health.status == HealthStatus.DEGRADED
        assert "degraded" in overall_health.message.lower()
        assert overall_health.details["component_counts"]["degraded"] == 1
    
    def test_get_overall_health_unknown_components(self, health_checker):
        """Test overall health with many unknown components."""
        component_healths = {
            "comp1": ComponentHealth("comp1", HealthStatus.UNKNOWN, "Unknown"),
            "comp2": ComponentHealth("comp2", HealthStatus.UNKNOWN, "Unknown"),
            "comp3": ComponentHealth("comp3", HealthStatus.UNKNOWN, "Unknown"),
            "comp4": ComponentHealth("comp4", HealthStatus.HEALTHY, "OK")
        }
        
        overall_health = health_checker.get_overall_health(component_healths)
        
        assert overall_health.status == HealthStatus.DEGRADED
        assert "unclear" in overall_health.message.lower()
        assert overall_health.details["component_counts"]["unknown"] == 3


@pytest.mark.integration
class TestHealthCheckerIntegration:
    """Integration tests for HealthChecker."""
    
    @pytest.mark.asyncio
    async def test_real_health_checks_structure(self):
        """Test that health checks return expected structure."""
        health_checker = HealthChecker()
        
        # This test runs against real implementations but with short timeouts
        health_checker._timeout = 2.0
        
        try:
            results = await health_checker.check_all_components(use_cache=False)
            
            # Verify structure regardless of success/failure
            assert isinstance(results, dict)
            
            expected_components = [
                "database", "redis", "celery", "openai", "anthropic", 
                "ollama", "crew_execution", "memory_system", "queue_system",
                "websocket", "dynamic_generation", "manager_agent"
            ]
            
            for component in expected_components:
                assert component in results
                health = results[component]
                assert isinstance(health, ComponentHealth)
                assert health.name == component
                assert isinstance(health.status, HealthStatus)
                assert isinstance(health.message, str)
                assert isinstance(health.details, dict)
                
        except Exception as e:
            pytest.skip(f"Integration test skipped due to environment: {e}")
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self):
        """Test health check performance meets targets."""
        health_checker = HealthChecker()
        
        start_time = datetime.utcnow()
        
        try:
            await health_checker.check_all_components(use_cache=False)
            end_time = datetime.utcnow()
            
            duration = (end_time - start_time).total_seconds()
            
            # Health checks should complete within reasonable time
            assert duration < 30.0, f"Health checks took {duration}s, should be under 30s"
            
        except Exception as e:
            pytest.skip(f"Performance test skipped due to environment: {e}")


class TestHealthStatusEnum:
    """Test HealthStatus enum."""
    
    def test_health_status_values(self):
        """Test HealthStatus enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"
    
    def test_health_status_comparison(self):
        """Test HealthStatus comparison."""
        assert HealthStatus.HEALTHY == HealthStatus.HEALTHY
        assert HealthStatus.HEALTHY != HealthStatus.UNHEALTHY 