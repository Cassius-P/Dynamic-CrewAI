"""
Tests for performance metrics API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.main import app
from app.utils.cache import cache_manager
from app.utils.performance import performance_monitor, resource_manager, connection_manager

client = TestClient(app)

class TestPerformanceMetricsAPI:
    """Test performance metrics API endpoints."""
    
    def setup_method(self):
        """Setup for each test."""
        # Clear performance data
        performance_monitor._metrics.clear()
        performance_monitor._request_times.clear()
        cache_manager._cache_stats = {
            'hits': 0,
            'misses': 0,
            'l1_hits': 0,
            'l2_hits': 0,
            'invalidations': 0,
            'errors': 0
        }
    
    def test_get_performance_metrics(self):
        """Test GET /api/v1/metrics/performance endpoint."""
        # Add some test metrics
        performance_monitor.record_metric("api", "request_duration", 0.5)
        performance_monitor.record_request_time("/api/test", 0.3)
        
        response = client.get("/api/v1/metrics/performance")
        assert response.status_code == 200
        
        data = response.json()
        assert "timestamp" in data
        assert "period_hours" in data
        assert "metrics_summary" in data
        assert "api_performance" in data
        assert "resource_status" in data
        assert "connection_pools" in data
        
        # Check that metrics are included
        assert data["metrics_summary"]["count"] > 0
        assert data["api_performance"]["request_count"] > 0
    
    def test_get_performance_metrics_with_hours_param(self):
        """Test performance metrics with custom hours parameter."""
        response = client.get("/api/v1/metrics/performance?hours=48")
        assert response.status_code == 200
        
        data = response.json()
        assert data["period_hours"] == 48
    
    def test_get_cache_statistics(self):
        """Test GET /api/v1/metrics/cache endpoint."""
        # Simulate some cache operations
        cache_manager._cache_stats['hits'] = 80
        cache_manager._cache_stats['misses'] = 20
        cache_manager._l1_cache['test_key'] = {'data': 'test_value'}
        
        response = client.get("/api/v1/metrics/cache")
        assert response.status_code == 200
        
        data = response.json()
        assert "cache_statistics" in data
        assert "performance_indicators" in data
        assert "recommendations" in data
        
        # Check performance indicators
        indicators = data["performance_indicators"]
        assert indicators["total_operations"] == 100
        assert indicators["hit_rate_percent"] == 80.0
        assert "performance_rating" in indicators
        
        # Check that recommendations are provided
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) > 0
    
    def test_get_database_metrics(self):
        """Test GET /api/v1/metrics/database endpoint."""
        response = client.get("/api/v1/metrics/database")
        assert response.status_code == 200
        
        data = response.json()
        assert "database_health" in data
        assert "connection_pool" in data
        assert "performance_indicators" in data
        
        # Check database health structure
        health = data["database_health"]
        assert "is_healthy" in health
        assert "response_time_ms" in health
        assert isinstance(health["is_healthy"], bool)
        
        # Check performance indicators
        indicators = data["performance_indicators"]
        assert "pool_utilization" in indicators
        assert "health_status" in indicators
    
    def test_get_queue_metrics(self):
        """Test GET /api/v1/metrics/queue endpoint."""
        # Set some active executions
        resource_manager._active_executions = 3
        
        response = client.get("/api/v1/metrics/queue")
        assert response.status_code == 200
        
        data = response.json()
        assert "queue_status" in data
        assert "performance_indicators" in data
        
        # Check queue status
        queue_status = data["queue_status"]
        assert queue_status["active_executions"] == 3
        assert "max_concurrent" in queue_status
        assert "can_accept_new" in queue_status
        
        # Check performance indicators
        indicators = data["performance_indicators"]
        assert "utilization_percent" in indicators
        assert "queue_health" in indicators
        assert indicators["utilization_percent"] >= 0
    
    def test_get_resource_utilization(self):
        """Test GET /api/v1/metrics/resources/usage endpoint."""
        response = client.get("/api/v1/metrics/resources/usage")
        assert response.status_code == 200
        
        data = response.json()
        assert "resource_usage" in data
        assert "execution_status" in data
        assert "health_indicators" in data
        assert "thresholds" in data
        
        # Check resource usage structure
        usage = data["resource_usage"]
        assert "timestamp" in usage
        assert "cpu_percent" in usage
        assert "memory_percent" in usage
        assert "memory_used_mb" in usage
        assert "memory_available_mb" in usage
        assert "disk_usage_percent" in usage
        
        # Check health indicators
        health = data["health_indicators"]
        assert "health_score" in health
        assert "status" in health
        assert "issues" in health
        assert 0 <= health["health_score"] <= 100
        assert health["status"] in ["healthy", "warning", "critical"]
        
        # Check thresholds
        thresholds = data["thresholds"]
        assert "cpu_warning" in thresholds
        assert "cpu_critical" in thresholds
        assert "memory_warning" in thresholds
        assert "memory_critical" in thresholds
    
    def test_get_system_health(self):
        """Test GET /api/v1/metrics/health endpoint."""
        response = client.get("/api/v1/metrics/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "health_score" in data
        assert "timestamp" in data
        assert "components" in data
        
        # Check overall status
        assert data["status"] in ["healthy", "unhealthy"]
        assert 0 <= data["health_score"] <= 100
        
        # Check components
        components = data["components"]
        assert "database" in components
        assert "cache" in components
        assert "resources" in components
        assert "execution_engine" in components
        
        # Each component should have health status and details
        for component_name, component in components.items():
            assert "healthy" in component
            assert "details" in component
            assert isinstance(component["healthy"], bool)
    
    @pytest.mark.asyncio
    async def test_clear_cache_l1(self):
        """Test POST /api/v1/metrics/cache/clear with L1 cache type."""
        # Add some data to L1 cache
        cache_manager._l1_cache['test_key'] = {'data': 'test_value'}
        cache_manager._l1_access_order.append('test_key')
        
        response = client.post("/api/v1/metrics/cache/clear?cache_type=l1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "L1 cache cleared"
        assert data["cache_type"] == "l1"
        
        # Verify L1 cache is cleared
        assert len(cache_manager._l1_cache) == 0
        assert len(cache_manager._l1_access_order) == 0
    
    @pytest.mark.asyncio
    async def test_clear_cache_all(self):
        """Test POST /api/v1/metrics/cache/clear without cache type (clear all)."""
        # Add some data to L1 cache
        cache_manager._l1_cache['test_key'] = {'data': 'test_value'}
        
        with patch.object(cache_manager, 'clear_all') as mock_clear_all:
            mock_clear_all.return_value = True
            
            response = client.post("/api/v1/metrics/cache/clear")
            assert response.status_code == 200
            
            data = response.json()
            assert data["message"] == "All cache levels cleared"
            assert data["cache_type"] == "all"
            
            # Verify clear_all was called
            mock_clear_all.assert_called_once()

class TestPerformanceMetricsValidation:
    """Test performance metrics validation and edge cases."""
    
    def test_performance_metrics_invalid_hours(self):
        """Test performance metrics with invalid hours parameter."""
        # Test hours too low
        response = client.get("/api/v1/metrics/performance?hours=0")
        assert response.status_code == 422  # Validation error
        
        # Test hours too high
        response = client.get("/api/v1/metrics/performance?hours=200")
        assert response.status_code == 422  # Validation error
    
    def test_cache_clear_invalid_type(self):
        """Test cache clear with invalid cache type."""
        response = client.post("/api/v1/metrics/cache/clear?cache_type=invalid")
        assert response.status_code == 200  # Should default to clearing all
        
        data = response.json()
        assert data["cache_type"] == "all"
    
    def test_metrics_with_empty_data(self):
        """Test metrics endpoints with no data."""
        # Clear all data
        performance_monitor._metrics.clear()
        performance_monitor._request_times.clear()
        cache_manager._cache_stats = {
            'hits': 0,
            'misses': 0,
            'l1_hits': 0,
            'l2_hits': 0,
            'invalidations': 0,
            'errors': 0
        }
        
        # All endpoints should still work with empty data
        response = client.get("/api/v1/metrics/performance")
        assert response.status_code == 200
        
        response = client.get("/api/v1/metrics/cache")
        assert response.status_code == 200
        
        response = client.get("/api/v1/metrics/queue")
        assert response.status_code == 200
        
        response = client.get("/api/v1/metrics/resources/usage")
        assert response.status_code == 200
        
        response = client.get("/api/v1/metrics/health")
        assert response.status_code == 200

class TestCacheRecommendations:
    """Test cache recommendation generation."""
    
    def setup_method(self):
        """Setup for each test."""
        # Reset cache state
        cache_manager._l1_cache.clear()
        cache_manager._cache_stats = {
            'hits': 0,
            'misses': 0,
            'l1_hits': 0,
            'l2_hits': 0,
            'invalidations': 0,
            'errors': 0
        }
    
    def test_cache_recommendations_low_hit_rate(self):
        """Test recommendations for low cache hit rate."""
        # Set low hit rate
        cache_manager._cache_stats['hits'] = 30
        cache_manager._cache_stats['misses'] = 70
        
        response = client.get("/api/v1/metrics/cache")
        assert response.status_code == 200
        
        data = response.json()
        recommendations = data["recommendations"]
        
        # Should recommend increasing TTL
        assert any("TTL" in rec for rec in recommendations)
    
    def test_cache_recommendations_high_l1_usage(self):
        """Test recommendations for high L1 cache usage."""
        # Fill L1 cache near capacity
        for i in range(950):  # Near the 1000 limit
            cache_manager._l1_cache[f'key_{i}'] = {'data': f'value_{i}'}
        
        response = client.get("/api/v1/metrics/cache")
        assert response.status_code == 200
        
        data = response.json()
        recommendations = data["recommendations"]
        
        # Should recommend increasing L1 cache size
        assert any("L1 cache" in rec and "full" in rec for rec in recommendations)
    
    def test_cache_recommendations_high_error_rate(self):
        """Test recommendations for high cache error rate."""
        # Set high error rate
        cache_manager._cache_stats['errors'] = 10
        cache_manager._cache_stats['hits'] = 90
        cache_manager._cache_stats['misses'] = 0
        
        response = client.get("/api/v1/metrics/cache")
        assert response.status_code == 200
        
        data = response.json()
        recommendations = data["recommendations"]
        
        # Should recommend checking Redis connectivity
        assert any("Redis" in rec for rec in recommendations)
    
    def test_cache_recommendations_optimal(self):
        """Test recommendations when cache is performing optimally."""
        # Set good performance metrics
        cache_manager._cache_stats['hits'] = 85
        cache_manager._cache_stats['misses'] = 15
        cache_manager._cache_stats['errors'] = 0
        
        # Set reasonable L1 usage
        for i in range(500):  # Half capacity
            cache_manager._l1_cache[f'key_{i}'] = {'data': f'value_{i}'}
        
        response = client.get("/api/v1/metrics/cache")
        assert response.status_code == 200
        
        data = response.json()
        recommendations = data["recommendations"]
        
        # Should indicate optimal performance
        assert any("optimal" in rec.lower() for rec in recommendations)

class TestResourceHealthScoring:
    """Test resource health scoring logic."""
    
    @patch('app.utils.performance.psutil.virtual_memory')
    @patch('app.utils.performance.psutil.cpu_percent')
    def test_health_score_calculation(self, mock_cpu, mock_memory):
        """Test health score calculation with different resource levels."""
        # Mock normal resource usage
        mock_memory.return_value.percent = 70
        mock_cpu.return_value = 60
        
        response = client.get("/api/v1/metrics/resources/usage")
        assert response.status_code == 200
        
        data = response.json()
        health = data["health_indicators"]
        
        # Should have high health score with normal usage
        assert health["health_score"] >= 80
        assert health["status"] == "healthy"
        assert len(health["issues"]) == 0
    
    @patch('app.utils.performance.psutil.virtual_memory')
    @patch('app.utils.performance.psutil.cpu_percent')
    def test_health_score_high_usage(self, mock_cpu, mock_memory):
        """Test health score with high resource usage."""
        # Mock high resource usage
        mock_memory.return_value.percent = 90
        mock_cpu.return_value = 85
        
        response = client.get("/api/v1/metrics/resources/usage")
        assert response.status_code == 200
        
        data = response.json()
        health = data["health_indicators"]
        
        # Should have lower health score with high usage
        assert health["health_score"] < 80
        assert health["status"] in ["warning", "critical"]
        assert len(health["issues"]) > 0
    
    @patch('app.utils.performance.psutil.virtual_memory')
    @patch('app.utils.performance.psutil.cpu_percent')
    def test_health_score_critical_usage(self, mock_cpu, mock_memory):
        """Test health score with critical resource usage."""
        # Mock critical resource usage
        mock_memory.return_value.percent = 98
        mock_cpu.return_value = 95
        
        response = client.get("/api/v1/metrics/resources/usage")
        assert response.status_code == 200
        
        data = response.json()
        health = data["health_indicators"]
        
        # Should have critical health score
        assert health["health_score"] <= 50
        assert health["status"] == "critical"
        assert "Critical" in " ".join(health["issues"])

class TestPerformanceIntegration:
    """Test integration between performance monitoring and caching."""
    
    def test_performance_tracking_with_cache_operations(self):
        """Test that cache operations are tracked in performance metrics."""
        # Perform some cache operations
        cache_manager._cache_stats['hits'] = 50
        cache_manager._cache_stats['misses'] = 10
        cache_manager._cache_stats['l1_hits'] = 30
        cache_manager._cache_stats['l2_hits'] = 20
        
        # Record some performance metrics
        performance_monitor.record_metric("cache", "l1_hit", 1, "count")
        performance_monitor.record_metric("cache", "l2_hit", 1, "count")
        performance_monitor.record_metric("cache", "miss", 1, "count")
        
        # Get performance summary
        response = client.get("/api/v1/metrics/performance")
        assert response.status_code == 200
        
        data = response.json()
        
        # Should include cache metrics in performance summary
        assert data["metrics_summary"]["count"] > 0
        
        # Get cache statistics
        response = client.get("/api/v1/metrics/cache")
        assert response.status_code == 200
        
        cache_data = response.json()
        
        # Should show good performance
        assert cache_data["performance_indicators"]["hit_rate_percent"] > 80
        assert cache_data["performance_indicators"]["performance_rating"] in ["excellent", "good"] 