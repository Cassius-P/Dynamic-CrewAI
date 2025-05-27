"""
Performance metrics and cache management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional
import structlog
from app.database import get_db
from app.utils.performance import performance_monitor, resource_manager, connection_manager
from app.utils.cache import cache_manager

logger = structlog.get_logger()
router = APIRouter()

@router.get("/performance")
async def get_performance_metrics(
    hours: int = Query(default=24, ge=1, le=168, description="Hours to look back"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get comprehensive performance metrics."""
    try:
        # Get current performance data
        performance_summary = performance_monitor.get_metrics_summary()
        api_performance = performance_monitor.get_api_performance()
        resource_status = resource_manager.get_resource_status()
        pool_stats = connection_manager.get_pool_stats()
        
        return {
            "timestamp": performance_summary.get("uptime_seconds", 0),
            "period_hours": hours,
            "metrics_summary": performance_summary,
            "api_performance": api_performance,
            "resource_status": resource_status,
            "connection_pools": pool_stats
        }
        
    except Exception as e:
        logger.error("Error getting performance metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cache")
async def get_cache_statistics() -> Dict[str, Any]:
    """Get cache hit/miss statistics and performance."""
    try:
        cache_stats = cache_manager.get_stats()
        
        # Calculate additional metrics
        total_operations = cache_stats.get('hits', 0) + cache_stats.get('misses', 0)
        hit_rate = cache_stats.get('hit_rate_percent', 0)
        
        return {
            "cache_statistics": cache_stats,
            "performance_indicators": {
                "total_operations": total_operations,
                "hit_rate_percent": hit_rate,
                "l1_utilization_percent": round(
                    (cache_stats.get('l1_size', 0) / cache_stats.get('l1_max_size', 1000)) * 100, 2
                ),
                "performance_rating": (
                    "excellent" if hit_rate > 80 
                    else "good" if hit_rate > 60 
                    else "fair" if hit_rate > 40 
                    else "poor"
                )
            },
            "recommendations": _generate_cache_recommendations(cache_stats)
        }
        
    except Exception as e:
        logger.error("Error getting cache statistics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/database")
async def get_database_metrics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get database performance metrics."""
    try:
        pool_stats = connection_manager.get_pool_stats()
        
        # Basic database health check
        try:
            result = db.execute(text("SELECT 1")).scalar()
            db_healthy = result == 1
            db_response_time = 0  # Would measure actual response time
        except Exception:
            db_healthy = False
            db_response_time = -1
        
        return {
            "database_health": {
                "is_healthy": db_healthy,
                "response_time_ms": db_response_time
            },
            "connection_pool": pool_stats,
            "performance_indicators": {
                "pool_utilization": _calculate_pool_utilization(pool_stats),
                "health_status": "healthy" if db_healthy else "unhealthy"
            }
        }
        
    except Exception as e:
        logger.error("Error getting database metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue")
async def get_queue_metrics() -> Dict[str, Any]:
    """Get queue performance statistics."""
    try:
        resource_status = resource_manager.get_resource_status()
        
        return {
            "queue_status": {
                "active_executions": resource_status.get("active_executions", 0),
                "max_concurrent": resource_status.get("max_concurrent_executions", 10),
                "can_accept_new": resource_status.get("can_accept_new", True)
            },
            "performance_indicators": {
                "utilization_percent": round(
                    (resource_status.get("active_executions", 0) / 
                     resource_status.get("max_concurrent_executions", 10)) * 100, 2
                ),
                "queue_health": (
                    "optimal" if resource_status.get("active_executions", 0) < 
                    resource_status.get("max_concurrent_executions", 10) * 0.7
                    else "busy" if resource_status.get("can_accept_new", True)
                    else "overloaded"
                )
            }
        }
        
    except Exception as e:
        logger.error("Error getting queue metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cache/clear")
async def clear_cache(
    cache_type: Optional[str] = Query(
        default=None, 
        description="Specific cache type to clear (l1, l2) or all if not specified"
    )
) -> Dict[str, Any]:
    """Clear cache with admin controls."""
    try:
        if cache_type == "l1":
            # Clear only L1 cache
            cache_manager._l1_cache.clear()
            cache_manager._l1_access_order.clear()
            logger.info("L1 cache cleared")
            return {"message": "L1 cache cleared", "cache_type": "l1"}
        
        elif cache_type == "l2":
            # Clear only Redis (L2) cache
            await cache_manager.clear_all()
            logger.info("L2 (Redis) cache cleared")
            return {"message": "L2 (Redis) cache cleared", "cache_type": "l2"}
        
        else:
            # Clear all cache levels
            await cache_manager.clear_all()
            logger.warning("All cache levels cleared")
            return {"message": "All cache levels cleared", "cache_type": "all"}
        
    except Exception as e:
        logger.error("Error clearing cache", cache_type=cache_type, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/resources/usage")
async def get_resource_utilization() -> Dict[str, Any]:
    """Get current resource utilization."""
    try:
        resource_usage = performance_monitor.get_resource_usage()
        resource_status = resource_manager.get_resource_status()
        
        # Calculate health indicators
        health_score = 100
        issues = []
        
        if resource_usage.cpu_percent > 90:
            health_score -= 30
            issues.append("Critical CPU usage")
        elif resource_usage.cpu_percent > 80:
            health_score -= 15
            issues.append("High CPU usage")
        
        if resource_usage.memory_percent > 95:
            health_score -= 30
            issues.append("Critical memory usage")
        elif resource_usage.memory_percent > 85:
            health_score -= 15
            issues.append("High memory usage")
        
        if not resource_status.get("can_accept_new", True):
            health_score -= 25
            issues.append("Cannot accept new executions")
        
        health_score = max(0, health_score)
        
        return {
            "resource_usage": {
                "timestamp": resource_usage.timestamp.isoformat(),
                "cpu_percent": resource_usage.cpu_percent,
                "memory_percent": resource_usage.memory_percent,
                "memory_used_mb": resource_usage.memory_used_mb,
                "memory_available_mb": resource_usage.memory_available_mb,
                "disk_usage_percent": resource_usage.disk_usage_percent
            },
            "execution_status": resource_status,
            "health_indicators": {
                "health_score": health_score,
                "status": (
                    "healthy" if health_score > 80
                    else "warning" if health_score > 50
                    else "critical"
                ),
                "issues": issues
            },
            "thresholds": {
                "cpu_warning": 80,
                "cpu_critical": 90,
                "memory_warning": 85,
                "memory_critical": 95
            }
        }
        
    except Exception as e:
        logger.error("Error getting resource utilization", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def get_system_health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Comprehensive system health check."""
    try:
        # Get all component statuses
        cache_stats = cache_manager.get_stats()
        resource_usage = performance_monitor.get_resource_usage()
        resource_status = resource_manager.get_resource_status()
        pool_stats = connection_manager.get_pool_stats()
        
        # Test database connectivity
        try:
            db.execute(text("SELECT 1")).scalar()
            db_healthy = True
        except Exception:
            db_healthy = False
        
        # Calculate overall health
        health_checks = {
            "database": db_healthy,
            "cache": cache_stats.get('errors', 0) < cache_stats.get('total_requests', 1) * 0.1,
            "memory": resource_usage.memory_percent < 95,
            "cpu": resource_usage.cpu_percent < 95,
            "executions": resource_status.get("can_accept_new", True)
        }
        
        overall_healthy = all(health_checks.values())
        health_score = sum(health_checks.values()) / len(health_checks) * 100
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "health_score": round(health_score, 1),
            "timestamp": resource_usage.timestamp.isoformat(),
            "components": {
                "database": {
                    "healthy": health_checks["database"],
                    "details": pool_stats
                },
                "cache": {
                    "healthy": health_checks["cache"],
                    "details": cache_stats
                },
                "resources": {
                    "healthy": health_checks["memory"] and health_checks["cpu"],
                    "details": {
                        "cpu_percent": resource_usage.cpu_percent,
                        "memory_percent": resource_usage.memory_percent
                    }
                },
                "execution_engine": {
                    "healthy": health_checks["executions"],
                    "details": resource_status
                }
            }
        }
        
    except Exception as e:
        logger.error("Error getting system health", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

def _generate_cache_recommendations(cache_stats: Dict[str, Any]) -> list[str]:
    """Generate cache optimization recommendations."""
    recommendations = []
    
    hit_rate = cache_stats.get('hit_rate_percent', 0)
    if hit_rate < 60:
        recommendations.append("Consider increasing cache TTL for frequently accessed data")
    
    l1_usage = cache_stats.get('l1_size', 0) / cache_stats.get('l1_max_size', 1000)
    if l1_usage > 0.9:
        recommendations.append("L1 cache is nearly full - consider increasing max size")
    
    error_rate = cache_stats.get('errors', 0) / max(cache_stats.get('total_requests', 1), 1)
    if error_rate > 0.05:
        recommendations.append("High cache error rate - check Redis connectivity")
    
    if not recommendations:
        recommendations.append("Cache performance is optimal")
    
    return recommendations

def _calculate_pool_utilization(pool_stats: Dict[str, Any]) -> float:
    """Calculate database pool utilization percentage."""
    pool_size = pool_stats.get('db_pool_size', 0)
    checked_out = pool_stats.get('db_checked_out', 0)
    
    if pool_size > 0:
        return round((checked_out / pool_size) * 100, 2)
    return 0.0 