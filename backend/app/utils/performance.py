"""
Performance monitoring and connection pooling core functionality.
"""
import time
import psutil
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from sqlalchemy.pool import QueuePool
from sqlalchemy import create_engine, text
import structlog
from app.config import settings

logger = structlog.get_logger()

@dataclass
class PerformanceMetric:
    """Performance metric data point."""
    timestamp: datetime
    metric_type: str
    metric_name: str
    value: float
    unit: str
    tags: Dict[str, str]

@dataclass
class ResourceUsage:
    """System resource utilization snapshot."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    active_connections: int
    queue_size: int

class ConnectionPoolManager:
    """Enhanced connection pool management."""
    
    def __init__(self):
        self._db_pool = None
        self._redis_pool = None
        self._pool_stats = {
            'db_connections_created': 0,
            'db_connections_closed': 0,
            'redis_connections_created': 0,
            'redis_connections_closed': 0
        }
    
    def get_database_engine(self):
        """Get database engine with connection pooling."""
        if self._db_pool is None:
            self._db_pool = create_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=20,
                max_overflow=30,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
        return self._db_pool
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        stats = dict(self._pool_stats)
        
        if self._db_pool:
            pool = self._db_pool.pool
            try:
                stats.update({
                    'db_pool_size': getattr(pool, 'size', lambda: 0)(),
                    'db_checked_in': getattr(pool, 'checkedin', lambda: 0)(),
                    'db_checked_out': getattr(pool, 'checkedout', lambda: 0)(),
                    'db_overflow': getattr(pool, 'overflow', lambda: 0)(),
                    'db_invalid': getattr(pool, 'invalid', lambda: 0)()
                })
            except Exception as e:
                logger.warning("Could not get pool stats", error=str(e))
                stats.update({
                    'db_pool_size': 0,
                    'db_checked_in': 0,
                    'db_checked_out': 0,
                    'db_overflow': 0,
                    'db_invalid': 0
                })
        
        return stats

class PerformanceMonitor:
    """Real-time performance monitoring."""
    
    def __init__(self):
        self._metrics = []
        self._max_metrics = 10000
        self._start_time = time.time()
        self._request_times = []
        self._max_request_times = 1000
    
    def record_metric(self, metric_type: str, metric_name: str, value: float, 
                     unit: str = "count", tags: Optional[Dict[str, str]] = None):
        """Record a performance metric."""
        metric = PerformanceMetric(
            timestamp=datetime.utcnow(),
            metric_type=metric_type,
            metric_name=metric_name,
            value=value,
            unit=unit,
            tags=tags or {}
        )
        
        self._metrics.append(metric)
        
        # Keep only recent metrics
        if len(self._metrics) > self._max_metrics:
            self._metrics = self._metrics[-self._max_metrics//2:]
    
    def record_request_time(self, endpoint: str, duration: float):
        """Record API request timing."""
        self._request_times.append({
            'timestamp': datetime.utcnow(),
            'endpoint': endpoint,
            'duration': duration
        })
        
        # Keep only recent request times
        if len(self._request_times) > self._max_request_times:
            self._request_times = self._request_times[-self._max_request_times//2:]
        
        # Record as metric
        self.record_metric(
            metric_type="api",
            metric_name="request_duration",
            value=duration,
            unit="seconds",
            tags={"endpoint": endpoint}
        )
    
    def get_resource_usage(self) -> ResourceUsage:
        """Get current system resource usage."""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_percent=memory.percent,
            memory_used_mb=memory.used / 1024 / 1024,
            memory_available_mb=memory.available / 1024 / 1024,
            disk_usage_percent=disk.percent,
            active_connections=0,  # Would be populated from actual sources
            queue_size=0  # Would be populated from queue system
        )
    
    def get_metrics_summary(self, metric_type: Optional[str] = None,
                           since: Optional[datetime] = None) -> Dict[str, Any]:
        """Get summary of recorded metrics."""
        filtered_metrics = self._metrics
        
        if metric_type:
            filtered_metrics = [m for m in filtered_metrics if m.metric_type == metric_type]
        
        if since:
            filtered_metrics = [m for m in filtered_metrics if m.timestamp >= since]
        
        if not filtered_metrics:
            return {"count": 0, "metrics": []}
        
        # Group by metric name
        grouped = {}
        for metric in filtered_metrics:
            if metric.metric_name not in grouped:
                grouped[metric.metric_name] = []
            grouped[metric.metric_name].append(metric.value)
        
        # Calculate statistics
        summary = {}
        for name, values in grouped.items():
            summary[name] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1]
            }
        
        return {
            "count": len(filtered_metrics),
            "metrics": summary,
            "uptime_seconds": time.time() - self._start_time
        }
    
    def get_api_performance(self) -> Dict[str, Any]:
        """Get API performance statistics."""
        if not self._request_times:
            return {"request_count": 0}
        
        # Group by endpoint
        endpoint_stats = {}
        for req in self._request_times:
            endpoint = req['endpoint']
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = []
            endpoint_stats[endpoint].append(req['duration'])
        
        # Calculate stats per endpoint
        stats = {}
        for endpoint, durations in endpoint_stats.items():
            stats[endpoint] = {
                "request_count": len(durations),
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "p95_duration": sorted(durations)[int(len(durations) * 0.95)]
            }
        
        return {
            "request_count": len(self._request_times),
            "endpoints": stats,
            "overall_avg": sum(req['duration'] for req in self._request_times) / len(self._request_times)
        }

class ResourceManager:
    """Resource usage monitoring and throttling."""
    
    def __init__(self):
        self.max_concurrent_executions = 10
        self.max_memory_percent = 85
        self.max_cpu_percent = 90
        self._active_executions = 0
        self._execution_queue = []
    
    async def can_start_execution(self) -> bool:
        """Check if we can start a new execution."""
        # Check concurrent executions
        if self._active_executions >= self.max_concurrent_executions:
            return False
        
        # Check system resources
        memory = psutil.virtual_memory()
        if memory.percent > self.max_memory_percent:
            logger.warning("Memory usage too high", memory_percent=memory.percent)
            return False
        
        cpu_percent = psutil.cpu_percent(interval=0.1)
        if cpu_percent > self.max_cpu_percent:
            logger.warning("CPU usage too high", cpu_percent=cpu_percent)
            return False
        
        return True
    
    async def start_execution(self, execution_id: str):
        """Register start of execution."""
        self._active_executions += 1
        logger.info("Execution started", execution_id=execution_id, 
                   active_count=self._active_executions)
    
    async def end_execution(self, execution_id: str):
        """Register end of execution."""
        self._active_executions = max(0, self._active_executions - 1)
        logger.info("Execution ended", execution_id=execution_id,
                   active_count=self._active_executions)
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get current resource status."""
        memory = psutil.virtual_memory()
        return {
            "active_executions": self._active_executions,
            "max_concurrent_executions": self.max_concurrent_executions,
            "memory_percent": memory.percent,
            "max_memory_percent": self.max_memory_percent,
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "max_cpu_percent": self.max_cpu_percent,
            "can_accept_new": self._active_executions < self.max_concurrent_executions
        }

# Global instances
connection_manager = ConnectionPoolManager()
performance_monitor = PerformanceMonitor()
resource_manager = ResourceManager()

def performance_metrics(func):
    """Decorator to automatically track function performance."""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            performance_monitor.record_metric(
                metric_type="function",
                metric_name=func.__name__,
                value=duration,
                unit="seconds"
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            performance_monitor.record_metric(
                metric_type="function_error",
                metric_name=func.__name__,
                value=duration,
                unit="seconds"
            )
            raise
    return wrapper

async def health_check() -> Dict[str, Any]:
    """Comprehensive system health check."""
    resource_usage = performance_monitor.get_resource_usage()
    pool_stats = connection_manager.get_pool_stats()
    resource_status = resource_manager.get_resource_status()
    
    # Determine overall health
    health_status = "healthy"
    issues = []
    
    if resource_usage.memory_percent > 90:
        health_status = "warning"
        issues.append("High memory usage")
    
    if resource_usage.cpu_percent > 95:
        health_status = "critical"
        issues.append("Critical CPU usage")
    
    if resource_status["active_executions"] >= resource_status["max_concurrent_executions"]:
        health_status = "warning"
        issues.append("At maximum concurrent executions")
    
    return {
        "status": health_status,
        "timestamp": datetime.utcnow().isoformat(),
        "issues": issues,
        "resource_usage": asdict(resource_usage),
        "pool_stats": pool_stats,
        "resource_status": resource_status
    } 