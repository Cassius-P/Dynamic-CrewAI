"""
Simplified health check API endpoints with database storage.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Dict, Any, Optional
from app.api.deps import get_db
from app.schemas.health import (
    HealthResponse, DetailedHealthResponse, ComponentHealthResponse,
    AlertSummaryResponse, MonitoringDashboardResponse
)
from app.config import settings
from app.monitoring.health_checks import HealthChecker
from app.monitoring.alerts import alert_manager, AlertSeverity
from app.services.metrics_service import MetricsService
import structlog

logger = structlog.get_logger()
router = APIRouter()

# Global health checker instance
health_checker = HealthChecker()
metrics_service = MetricsService()

@router.get("/", response_model=HealthResponse)
async def basic_health_check(db: Session = Depends(get_db)):
    """Basic health check endpoint for load balancers and quick checks."""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        database_status = "healthy"
    except Exception as e:
        database_status = f"unhealthy: {str(e)}"
    
    overall_status = "healthy" if database_status == "healthy" else "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        database=database_status,
        timestamp=datetime.utcnow().isoformat(),
        details={
            "project_name": settings.project_name,
            "debug": settings.debug,
            "environment": getattr(settings, 'environment', 'unknown')
        }
    )

@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(
    use_cache: bool = Query(True, description="Use cached health results"),
    store_to_db: bool = Query(True, description="Store health metrics to database"),
    db: Session = Depends(get_db)
):
    """Comprehensive health check for all system components with database storage."""
    try:
        # Get health status for all components and optionally store to database
        if store_to_db:
            component_healths = await health_checker.check_all_components_and_store(db, use_cache=use_cache)
        else:
            component_healths = await health_checker.check_all_components(use_cache=use_cache)
        
        # Calculate basic overall health
        healthy_count = sum(1 for h in component_healths.values() if h.status.value == "healthy")
        total_count = len(component_healths)
        overall_status = "healthy" if healthy_count > total_count * 0.8 else "degraded"
        overall_message = f"System status: {healthy_count}/{total_count} components healthy"
        
        # Convert component healths to response format
        components = {
            name: ComponentHealthResponse(
                name=health.name,
                status=health.status.value,
                message=health.message,
                response_time_ms=health.response_time_ms,
                last_checked=health.last_checked.isoformat() if health.last_checked else None,
                details=health.details,
                dependencies=health.dependencies
            )
            for name, health in component_healths.items()
        }
        
        # Get active alerts summary
        active_alerts = alert_manager.get_active_alerts()
        alert_summary = {
            "total_active": len(active_alerts),
            "critical": sum(1 for alert in active_alerts.values() 
                          if alert.severity == AlertSeverity.CRITICAL),
            "warning": sum(1 for alert in active_alerts.values() 
                         if alert.severity == AlertSeverity.WARNING),
            "info": sum(1 for alert in active_alerts.values() 
                       if alert.severity == AlertSeverity.INFO)
        }
        
        return DetailedHealthResponse(
            overall_status=overall_status,
            overall_message=overall_message,
            timestamp=datetime.utcnow().isoformat(),
            components=components,
            alert_summary=alert_summary,
            system_info={
                "version": "1.0.0",
                "project_name": settings.project_name,
                "environment": getattr(settings, 'environment', 'unknown'),
                "debug": settings.debug,
                "uptime_seconds": 0  # Simplified - no need for precise uptime tracking
            },
            performance_summary={"healthy_ratio": healthy_count / total_count if total_count > 0 else 0}
        )
        
    except Exception as e:
        logger.error("Error in detailed health check", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )

@router.get("/component/{component_name}", response_model=ComponentHealthResponse)
async def component_health_check(
    component_name: str,
    use_cache: bool = Query(True, description="Use cached health results")
):
    """Get health status for a specific component."""
    try:
        # Get all component healths (from cache if available)
        component_healths = await health_checker.check_all_components(use_cache=use_cache)
        
        if component_name not in component_healths:
            raise HTTPException(
                status_code=404,
                detail=f"Component '{component_name}' not found"
            )
        
        health = component_healths[component_name]
        
        return ComponentHealthResponse(
            name=health.name,
            status=health.status.value,
            message=health.message,
            response_time_ms=health.response_time_ms,
            last_checked=health.last_checked.isoformat() if health.last_checked else None,
            details=health.details,
            dependencies=health.dependencies
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error checking component health", component=component_name, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Component health check failed: {str(e)}"
        )

@router.get("/dependencies", response_model=Dict[str, Any])
async def health_dependencies():
    """Get dependency health map showing component relationships."""
    try:
        # Get all component healths
        component_healths = await health_checker.check_all_components()
        
        # Build dependency map
        dependency_map = {}
        for name, health in component_healths.items():
            dependency_map[name] = {
                "status": health.status.value,
                "dependencies": health.dependencies,
                "dependent_components": []
            }
        
        # Find reverse dependencies
        for name, info in dependency_map.items():
            for dep in info["dependencies"]:
                if dep in dependency_map:
                    dependency_map[dep]["dependent_components"].append(name)
        
        # Calculate impact scores
        for name, info in dependency_map.items():
            info["impact_score"] = len(info["dependent_components"])
            info["health_score"] = 1.0 if info["status"] == "healthy" else 0.0
        
        return {
            "dependency_map": dependency_map,
            "summary": {
                "total_components": len(dependency_map),
                "healthy_components": sum(1 for info in dependency_map.values() 
                                        if info["status"] == "healthy"),
                "critical_dependencies": [name for name, info in dependency_map.items() 
                                        if info["impact_score"] > 2]
            }
        }
        
    except Exception as e:
        logger.error("Error getting health dependencies", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get health dependencies: {str(e)}"
        )

@router.get("/alerts", response_model=AlertSummaryResponse)
async def get_active_alerts(db: Session = Depends(get_db)):
    """Get summary of active alerts and alert statistics."""
    try:
        # Get active alerts
        active_alerts = alert_manager.get_active_alerts()
        
        # Get alert statistics from database
        alert_stats = await alert_manager.get_alert_statistics(db, hours=24)
        
        # Convert active alerts to response format
        alerts_list = []
        for alert_key, alert in active_alerts.items():
            alerts_list.append({
                "component": alert.component,
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "message": alert.message,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "triggered_at": alert.triggered_at.isoformat(),
                "trigger_count": alert.trigger_count
            })
        
        return AlertSummaryResponse(
            active_alerts=alerts_list,
            alert_statistics=alert_stats,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error("Error getting active alerts", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get alerts: {str(e)}"
        )

@router.get("/monitoring/dashboard", response_model=MonitoringDashboardResponse)
async def monitoring_dashboard(
    hours: int = Query(24, description="Hours of data to include", ge=1, le=168),
    db: Session = Depends(get_db)
):
    """Get comprehensive monitoring dashboard data with database storage."""
    try:
        # Get current health status and store to database
        component_healths = await health_checker.check_all_components_and_store(db, use_cache=True)
        
        # Calculate overall health score
        healthy_components = sum(1 for h in component_healths.values() 
                               if h.status.value == "healthy")
        total_components = len(component_healths)
        health_score = (healthy_components / total_components) * 100 if total_components > 0 else 0
        
        # Determine system status
        if health_score >= 90:
            system_status = "healthy"
        elif health_score >= 70:
            system_status = "degraded"
        else:
            system_status = "unhealthy"
        
        # Get performance metrics
        performance_summary = await metrics_service.get_performance_summary(db, hours=hours)
        
        # Get alert statistics  
        alert_stats = await alert_manager.get_alert_statistics(db, hours=hours)
        
        # Get cache analytics
        cache_analytics = await metrics_service.get_cache_analytics(db, hours=hours)
        
        # Get top performance issues
        performance_issues = []
        for component, health in component_healths.items():
            if health.status.value in ["unhealthy", "degraded"]:
                performance_issues.append({
                    "component": component,
                    "status": health.status.value,
                    "message": health.message,
                    "response_time_ms": health.response_time_ms
                })
        
        # Component health summary for dashboard
        component_health_summary = {
            name: {
                "status": health.status.value,
                "response_time_ms": health.response_time_ms,
                "last_checked": health.last_checked.isoformat() if health.last_checked else None
            }
            for name, health in component_healths.items()
        }
        
        return MonitoringDashboardResponse(
            overall_health_score=health_score,
            system_status=system_status,
            active_alerts_count=len(alert_manager.get_active_alerts()),
            performance_summary=performance_summary,
            alert_statistics=alert_stats,
            cache_analytics=cache_analytics,
            component_health_summary=component_health_summary,
            performance_issues=performance_issues,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error("Error getting monitoring dashboard", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Monitoring dashboard failed: {str(e)}"
        )

@router.get("/metrics/prometheus")
async def prometheus_metrics(db: Session = Depends(get_db)):
    """Prometheus-compatible metrics endpoint."""
    try:
        # Collect current metrics
        await metrics_service.collect_system_metrics(db)
        
        # Get component health for metrics
        component_healths = await health_checker.check_all_components()
        
        # Generate Prometheus format metrics
        metrics_output = []
        
        # Health status metrics (1 = healthy, 0 = unhealthy)
        for component, health in component_healths.items():
            health_value = 1 if health.status.value == "healthy" else 0
            metrics_output.append(
                f'crewai_component_health{{component="{component}"}} {health_value}'
            )
            
            # Response time metrics
            if health.response_time_ms is not None:
                metrics_output.append(
                    f'crewai_component_response_time_ms{{component="{component}"}} {health.response_time_ms}'
                )
        
        # Alert metrics
        active_alerts = alert_manager.get_active_alerts()
        metrics_output.append(f'crewai_active_alerts_total {len(active_alerts)}')
        
        # Count alerts by severity
        severity_counts = {"critical": 0, "warning": 0, "info": 0}
        for alert in active_alerts.values():
            severity_counts[alert.severity.value] += 1
        
        for severity, count in severity_counts.items():
            metrics_output.append(f'crewai_alerts_by_severity{{severity="{severity}"}} {count}')
        
        # Overall system health score
        healthy_count = sum(1 for h in component_healths.values() if h.status.value == "healthy")
        total_count = len(component_healths)
        health_score = (healthy_count / total_count) if total_count > 0 else 0
        metrics_output.append(f'crewai_system_health_score {health_score}')
        
        # Add timestamp
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        final_output = []
        for line in metrics_output:
            final_output.append(f"{line} {timestamp}")
        
        return {"metrics": "\n".join(final_output)}
        
    except Exception as e:
        logger.error("Error generating Prometheus metrics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate metrics: {str(e)}"
        )

@router.get("/readiness")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    try:
        # Check critical components only
        component_healths = await health_checker.check_all_components()
        critical_components = ['database', 'redis', 'celery']
        
        for component in critical_components:
            if component in component_healths:
                health = component_healths[component]
                if health.status.value == "unhealthy":
                    raise HTTPException(
                        status_code=503,
                        detail=f"Critical component {component} is unhealthy: {health.message}"
                    )
        
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in readiness check", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Readiness check failed: {str(e)}"
        )

@router.get("/liveness")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    try:
        # Basic application liveness check
        current_time = datetime.utcnow()
        
        return {
            "status": "alive",
            "timestamp": current_time.isoformat(),
            "uptime_seconds": (current_time - getattr(settings, 'start_time', current_time)).total_seconds()
        }
        
    except Exception as e:
        logger.error("Error in liveness check", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Liveness check failed: {str(e)}"
    )
