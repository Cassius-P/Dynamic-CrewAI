"""
Enhanced health check API endpoints with comprehensive monitoring.
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
    db: Session = Depends(get_db)
):
    """Comprehensive health check for all system components."""
    try:
        # Get health status for all components
        component_healths = await health_checker.check_all_components(use_cache=use_cache)
        
        # Calculate overall health
        overall_health = health_checker.get_overall_health(component_healths)
        
        # Get system metrics
        system_metrics = await metrics_service.collect_system_metrics(db)
        
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
            overall_status=overall_health.status.value,
            overall_message=overall_health.message,
            timestamp=datetime.utcnow().isoformat(),
            components=components,
            alert_summary=alert_summary,
            system_info={
                "version": "1.0.0",
                "project_name": settings.project_name,
                "environment": getattr(settings, 'environment', 'unknown'),
                "debug": settings.debug,
                "uptime_seconds": (datetime.utcnow() - getattr(settings, 'start_time', datetime.utcnow())).total_seconds()
            },
            performance_summary=overall_health.details
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
async def get_active_alerts():
    """Get summary of active alerts and alert statistics."""
    try:
        # Get active alerts
        active_alerts = alert_manager.get_active_alerts()
        
        # Get alert statistics
        alert_stats = await alert_manager.get_alert_statistics(hours=24)
        
        # Format active alerts for response
        formatted_alerts = []
        for alert_key, alert in active_alerts.items():
            formatted_alerts.append({
                "component": alert.component,
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "message": alert.message,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "triggered_at": alert.triggered_at.isoformat(),
                "trigger_count": alert.trigger_count,
                "channels_notified": [ch.value for ch in alert.channels_notified]
            })
        
        return AlertSummaryResponse(
            active_alerts=formatted_alerts,
            alert_statistics=alert_stats,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error("Error getting alert summary", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get alert summary: {str(e)}"
        )

@router.post("/alerts/{component}/{rule_name}/acknowledge")
async def acknowledge_alert(
    component: str,
    rule_name: str,
    acknowledged_by: str = Query(..., description="User acknowledging the alert")
):
    """Acknowledge an active alert."""
    try:
        await alert_manager.acknowledge_alert(component, rule_name, acknowledged_by)
        
        return {
            "status": "acknowledged",
            "component": component,
            "rule_name": rule_name,
            "acknowledged_by": acknowledged_by,
            "acknowledged_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Error acknowledging alert", component=component, rule=rule_name, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to acknowledge alert: {str(e)}"
        )

@router.get("/monitoring/dashboard", response_model=MonitoringDashboardResponse)
async def monitoring_dashboard(
    hours: int = Query(24, description="Hours of data to include", ge=1, le=168),
    db: Session = Depends(get_db)
):
    """Get comprehensive monitoring dashboard data."""
    try:
        # Get current health status
        component_healths = await health_checker.check_all_components()
        overall_health = health_checker.get_overall_health(component_healths)
        
        # Get performance metrics
        performance_summary = await metrics_service.get_performance_summary(db, hours=hours)
        
        # Get alert statistics
        alert_stats = await alert_manager.get_alert_statistics(hours=hours)
        
        # Get cache analytics
        cache_analytics = await metrics_service.get_cache_analytics(db, hours=hours)
        
        # Calculate system health score
        healthy_components = sum(1 for h in component_healths.values() 
                               if h.status.value == "healthy")
        total_components = len(component_healths)
        health_score = (healthy_components / total_components) * 100 if total_components > 0 else 0
        
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
        
        return MonitoringDashboardResponse(
            overall_health_score=health_score,
            system_status=overall_health.status.value,
            active_alerts_count=len(alert_manager.get_active_alerts()),
            performance_summary=performance_summary,
            alert_statistics=alert_stats,
            cache_analytics=cache_analytics,
            component_health_summary={
                name: {
                    "status": health.status.value,
                    "response_time_ms": health.response_time_ms,
                    "last_checked": health.last_checked.isoformat() if health.last_checked else None
                }
                for name, health in component_healths.items()
            },
            performance_issues=performance_issues,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error("Error generating monitoring dashboard", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate monitoring dashboard: {str(e)}"
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
