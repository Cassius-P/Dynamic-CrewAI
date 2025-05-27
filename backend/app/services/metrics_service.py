"""
Enhanced metrics service for performance monitoring and cache statistics.
"""
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
import structlog
from app.utils.performance import performance_monitor, resource_manager, connection_manager
from app.utils.cache import cache_manager, CacheTTL
from app.models.metrics import (
    PerformanceMetric, CacheStatistic, ResourceUsageMetric,
    QueryPerformance, ExecutionProfile, AlertThreshold
)
from app.database import get_db

logger = structlog.get_logger()

class MetricsService:
    """Enhanced metrics collection and analysis service."""
    
    def __init__(self):
        self._last_resource_collection = None
        self._collection_interval = 60  # seconds
    
    async def collect_system_metrics(self, db: Session):
        """Collect current system resource metrics."""
        try:
            resource_usage = performance_monitor.get_resource_usage()
            
            # Store in database
            metric = ResourceUsageMetric(
                cpu_percent=resource_usage.cpu_percent,
                memory_percent=resource_usage.memory_percent,
                memory_used_mb=resource_usage.memory_used_mb,
                memory_available_mb=resource_usage.memory_available_mb,
                disk_usage_percent=resource_usage.disk_usage_percent,
                active_connections=resource_usage.active_connections,
                queue_size=resource_usage.queue_size,
                active_executions=resource_manager._active_executions
            )
            
            db.add(metric)
            db.commit()
            
            # Also record as performance metrics
            metrics_to_record = [
                ("system", "cpu_percent", resource_usage.cpu_percent, "percent"),
                ("system", "memory_percent", resource_usage.memory_percent, "percent"),
                ("system", "memory_used_mb", resource_usage.memory_used_mb, "megabytes"),
                ("system", "disk_usage_percent", resource_usage.disk_usage_percent, "percent"),
                ("system", "active_executions", resource_manager._active_executions, "count")
            ]
            
            for metric_type, metric_name, value, unit in metrics_to_record:
                performance_monitor.record_metric(metric_type, metric_name, value, unit)
            
            self._last_resource_collection = datetime.utcnow()
            logger.debug("System metrics collected")
            
        except Exception as e:
            logger.error("Error collecting system metrics", error=str(e))
    
    async def record_cache_operation(self, db: Session, cache_type: str, 
                                   operation: str, key_pattern: Optional[str] = None,
                                   duration_ms: Optional[float] = None, data_size_bytes: Optional[int] = None,
                                   ttl_seconds: Optional[int] = None):
        """Record cache operation statistics."""
        try:
            stat = CacheStatistic(
                cache_type=cache_type,
                operation=operation,
                key_pattern=key_pattern,
                duration_ms=duration_ms,
                data_size_bytes=data_size_bytes,
                ttl_seconds=ttl_seconds
            )
            
            db.add(stat)
            db.commit()
            
            # Also record as performance metric
            performance_monitor.record_metric(
                metric_type="cache",
                metric_name=f"{cache_type}_{operation}",
                value=duration_ms if duration_ms else 1,
                unit="milliseconds" if duration_ms else "count",
                tags={"cache_type": cache_type, "operation": operation}
            )
            
        except Exception as e:
            logger.error("Error recording cache operation", error=str(e))
    
    async def record_query_performance(self, db: Session, query_type: str,
                                     table_name: str, duration_ms: float,
                                     rows_affected: Optional[int] = None, query_hash: Optional[str] = None,
                                     was_cached: bool = False, cache_hit: bool = False):
        """Record database query performance."""
        try:
            query_perf = QueryPerformance(
                query_type=query_type,
                table_name=table_name,
                duration_ms=duration_ms,
                rows_affected=rows_affected,
                query_hash=query_hash,
                was_cached=was_cached,
                cache_hit=cache_hit
            )
            
            db.add(query_perf)
            db.commit()
            
            # Record as performance metric
            performance_monitor.record_metric(
                metric_type="database",
                metric_name="query_duration",
                value=duration_ms,
                unit="milliseconds",
                tags={
                    "query_type": query_type,
                    "table_name": table_name,
                    "cached": str(was_cached)
                }
            )
            
        except Exception as e:
            logger.error("Error recording query performance", error=str(e))
    
    async def record_execution_profile(self, db: Session, execution_id: str,
                                     stage: str, agent_id: Optional[str] = None,
                                     task_type: Optional[str] = None, duration_ms: Optional[float] = None,
                                     memory_used_mb: Optional[float] = None, cpu_percent: Optional[float] = None,
                                     cache_hits: int = 0, cache_misses: int = 0,
                                     llm_calls: int = 0, tool_calls: int = 0,
                                     metadata: Optional[Dict[str, Any]] = None):
        """Record execution-specific performance profile."""
        try:
            profile = ExecutionProfile(
                execution_id=execution_id,
                stage=stage,
                agent_id=agent_id,
                task_type=task_type,
                duration_ms=duration_ms,
                memory_used_mb=memory_used_mb,
                cpu_percent=cpu_percent,
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                llm_calls=llm_calls,
                tool_calls=tool_calls,
                execution_metadata=metadata or {}
            )
            
            db.add(profile)
            db.commit()
            
            # Record as performance metrics
            if duration_ms:
                performance_monitor.record_metric(
                    metric_type="execution",
                    metric_name=f"{stage}_duration",
                    value=duration_ms,
                    unit="milliseconds",
                    tags={"execution_id": execution_id, "stage": stage}
                )
            
        except Exception as e:
            logger.error("Error recording execution profile", error=str(e))
    
    async def get_performance_summary(self, db: Session, 
                                    hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Cache statistics
            cache_stats = cache_manager.get_stats()
            
            # API performance
            api_performance = performance_monitor.get_api_performance()
            
            # Resource usage trends
            resource_metrics = db.query(ResourceUsageMetric).filter(
                ResourceUsageMetric.timestamp >= since
            ).order_by(desc(ResourceUsageMetric.timestamp)).limit(100).all()
            
            # Query performance
            slow_queries = db.query(QueryPerformance).filter(
                and_(
                    QueryPerformance.timestamp >= since,
                    QueryPerformance.duration_ms > 1000  # Slower than 1 second
                )
            ).order_by(desc(QueryPerformance.duration_ms)).limit(10).all()
            
            # Execution profiles
            recent_executions = db.query(ExecutionProfile).filter(
                ExecutionProfile.timestamp >= since
            ).order_by(desc(ExecutionProfile.timestamp)).limit(20).all()
            
            # Connection pool stats
            pool_stats = connection_manager.get_pool_stats()
            
            # Resource status
            resource_status = resource_manager.get_resource_status()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "period_hours": hours,
                "cache_statistics": cache_stats,
                "api_performance": api_performance,
                "resource_trends": [metric.to_dict() for metric in resource_metrics],
                "slow_queries": [query.to_dict() for query in slow_queries],
                "recent_executions": [exec.to_dict() for exec in recent_executions],
                "connection_pools": pool_stats,
                "current_resources": resource_status,
                "health_indicators": await self._calculate_health_indicators(db, since)
            }
            
        except Exception as e:
            logger.error("Error getting performance summary", error=str(e))
            return {"error": str(e)}
    
    async def _calculate_health_indicators(self, db: Session, 
                                         since: datetime) -> Dict[str, Any]:
        """Calculate system health indicators."""
        try:
            # Average response times
            avg_api_duration = db.query(func.avg(PerformanceMetric.value)).filter(
                and_(
                    PerformanceMetric.timestamp >= since,
                    PerformanceMetric.metric_type == "api",
                    PerformanceMetric.metric_name == "request_duration"
                )
            ).scalar() or 0
            
            # Cache hit rate
            cache_stats = cache_manager.get_stats()
            cache_hit_rate = cache_stats.get('hit_rate_percent', 0)
            
            # Error rate
            error_count = db.query(func.count(PerformanceMetric.id)).filter(
                and_(
                    PerformanceMetric.timestamp >= since,
                    PerformanceMetric.metric_type == "function_error"
                )
            ).scalar() or 0
            
            total_requests = db.query(func.count(PerformanceMetric.id)).filter(
                and_(
                    PerformanceMetric.timestamp >= since,
                    PerformanceMetric.metric_type.in_(["api", "function"])
                )
            ).scalar() or 1
            
            error_rate = (error_count / total_requests) * 100
            
            # Resource utilization
            recent_resources = db.query(ResourceUsageMetric).filter(
                ResourceUsageMetric.timestamp >= since
            ).order_by(desc(ResourceUsageMetric.timestamp)).limit(10).all()
            
            if recent_resources:
                # Safely extract actual values from SQLAlchemy model instances
                cpu_values = []
                memory_values = []
                for r in recent_resources:
                    try:
                        cpu_val = getattr(r, 'cpu_percent', 0)
                        memory_val = getattr(r, 'memory_percent', 0)
                        cpu_values.append(float(cpu_val))
                        memory_values.append(float(memory_val))
                    except (ValueError, TypeError, AttributeError):
                        continue
                
                if cpu_values:
                    avg_cpu = sum(cpu_values) / len(cpu_values)
                    avg_memory = sum(memory_values) / len(memory_values)
                else:
                    avg_cpu = 0.0
                    avg_memory = 0.0
            else:
                avg_cpu = 0.0
                avg_memory = 0.0
            
            # Calculate health score (0-100)
            health_score = 100
            
            # Deduct points for issues
            if avg_api_duration > 2.0:  # > 2 seconds
                health_score -= 20
            if cache_hit_rate < 50:  # < 50% cache hit rate
                health_score -= 15
            if error_rate > 5:  # > 5% error rate
                health_score -= 25
            if float(avg_cpu) > 80:  # > 80% CPU
                health_score -= 20
            if float(avg_memory) > 85:  # > 85% memory
                health_score -= 20
            
            health_score = max(0, health_score)
            
            return {
                "health_score": health_score,
                "avg_api_response_time": round(avg_api_duration, 3),
                "cache_hit_rate": round(cache_hit_rate, 2),
                "error_rate": round(error_rate, 2),
                "avg_cpu_percent": round(avg_cpu, 2),
                "avg_memory_percent": round(avg_memory, 2),
                "indicators": {
                    "api_performance": "good" if avg_api_duration < 1.0 else "warning" if avg_api_duration < 2.0 else "critical",
                    "cache_efficiency": "good" if cache_hit_rate > 70 else "warning" if cache_hit_rate > 40 else "critical",
                    "error_rate": "good" if error_rate < 1 else "warning" if error_rate < 5 else "critical",
                    "resource_usage": "good" if avg_cpu < 70 and avg_memory < 75 else "warning" if avg_cpu < 85 and avg_memory < 85 else "critical"
                }
            }
            
        except Exception as e:
            logger.error("Error calculating health indicators", error=str(e))
            return {"error": str(e)}
    
    async def get_cache_analytics(self, db: Session, hours: int = 24) -> Dict[str, Any]:
        """Get detailed cache analytics."""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Cache operation statistics
            cache_stats = db.query(
                CacheStatistic.cache_type,
                CacheStatistic.operation,
                func.count(CacheStatistic.id).label('count'),
                func.avg(CacheStatistic.duration_ms).label('avg_duration'),
                func.sum(CacheStatistic.data_size_bytes).label('total_bytes')
            ).filter(
                CacheStatistic.timestamp >= since
            ).group_by(
                CacheStatistic.cache_type,
                CacheStatistic.operation
            ).all()
            
            # Current cache status
            current_stats = cache_manager.get_stats()
            
            # Cache efficiency by type
            cache_efficiency = {}
            for cache_type in ['l1', 'l2', 'crew_config', 'memory_query']:
                hits = db.query(func.count(CacheStatistic.id)).filter(
                    and_(
                        CacheStatistic.timestamp >= since,
                        CacheStatistic.cache_type == cache_type,
                        CacheStatistic.operation == 'hit'
                    )
                ).scalar() or 0
                
                total_ops = db.query(func.count(CacheStatistic.id)).filter(
                    and_(
                        CacheStatistic.timestamp >= since,
                        CacheStatistic.cache_type == cache_type,
                        CacheStatistic.operation.in_(['hit', 'miss'])
                    )
                ).scalar() or 1
                
                cache_efficiency[cache_type] = {
                    'hits': hits,
                    'total_operations': total_ops,
                    'hit_rate': round((hits / total_ops) * 100, 2)
                }
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "period_hours": hours,
                "current_stats": current_stats,
                "operation_stats": [
                    {
                        "cache_type": stat.cache_type,
                        "operation": stat.operation,
                        "count": stat.count,
                        "avg_duration_ms": round(stat.avg_duration or 0, 3),
                        "total_bytes": stat.total_bytes or 0
                    }
                    for stat in cache_stats
                ],
                "efficiency_by_type": cache_efficiency,
                "recommendations": await self._generate_cache_recommendations(current_stats, cache_efficiency)
            }
            
        except Exception as e:
            logger.error("Error getting cache analytics", error=str(e))
            return {"error": str(e)}
    
    async def _generate_cache_recommendations(self, current_stats: Dict[str, Any],
                                            efficiency: Dict[str, Any]) -> List[str]:
        """Generate cache optimization recommendations."""
        recommendations = []
        
        # Check hit rate
        if current_stats.get('hit_rate_percent', 0) < 60:
            recommendations.append("Consider increasing cache TTL for frequently accessed data")
        
        # Check L1 cache size
        l1_usage = current_stats.get('l1_size', 0) / current_stats.get('l1_max_size', 1000)
        if l1_usage > 0.9:
            recommendations.append("L1 cache is nearly full - consider increasing max size")
        
        # Check efficiency by type
        for cache_type, stats in efficiency.items():
            if stats['hit_rate'] < 40 and stats['total_operations'] > 100:
                recommendations.append(f"Low hit rate for {cache_type} cache - review caching strategy")
        
        # Check error rate
        if current_stats.get('errors', 0) > current_stats.get('total_requests', 1) * 0.05:
            recommendations.append("High cache error rate - check Redis connectivity and configuration")
        
        if not recommendations:
            recommendations.append("Cache performance is optimal")
        
        return recommendations

# Global metrics service instance
metrics_service = MetricsService() 