"""
Simplified alert management system for storing alert data to database.
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
import structlog
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy import desc, and_, Column, Integer, String, DateTime, Text, Float
from app.database import get_db

logger = structlog.get_logger()

# Create AlertHistory model if not exists in metrics module
Base = declarative_base()

class AlertHistory(Base):
    """Alert history model for storing alert events."""
    __tablename__ = "alert_history"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String, nullable=False)
    component = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    action = Column(String, nullable=False)
    message = Column(Text)
    current_value = Column(Float)
    threshold_value = Column(Float)
    alert_metadata = Column(Text)  # JSON stored as text - renamed from 'metadata'
    timestamp = Column(DateTime, default=datetime.utcnow)

class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

class AlertStatus(Enum):
    """Alert status states."""
    ACTIVE = "active"
    RESOLVED = "resolved"

@dataclass
class AlertRule:
    """Configuration for an alert rule."""
    name: str
    metric_name: str
    component: str
    threshold_value: float
    comparison: str  # "gt", "lt", "eq", "gte", "lte"
    severity: AlertSeverity
    duration_minutes: int = 5  # How long condition must persist
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AlertData:
    """Represents alert data for database storage."""
    rule_name: str
    component: str
    severity: AlertSeverity
    message: str
    current_value: float
    threshold_value: float
    triggered_at: datetime
    last_triggered: datetime
    trigger_count: int = 1
    status: AlertStatus = AlertStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)

class SimpleAlertManager:
    """Simplified alert management system for data storage only."""
    
    def __init__(self):
        self._active_alerts: Dict[str, AlertData] = {}
        self._alert_rules: Dict[str, AlertRule] = {}
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default alert rules for system monitoring."""
        default_rules = [
            # Database alerts
            AlertRule(
                name="database_connection_failure",
                metric_name="database_health",
                component="database",
                threshold_value=0.5,  # Health score below 0.5
                comparison="lt",
                severity=AlertSeverity.CRITICAL,
                duration_minutes=1
            ),
            AlertRule(
                name="database_slow_queries",
                metric_name="database_query_time",
                component="database",
                threshold_value=5000,  # 5 seconds
                comparison="gt",
                severity=AlertSeverity.WARNING,
                duration_minutes=5
            ),
            
            # Redis alerts
            AlertRule(
                name="redis_connection_failure",
                metric_name="redis_health",
                component="redis",
                threshold_value=0.5,
                comparison="lt",
                severity=AlertSeverity.CRITICAL,
                duration_minutes=1
            ),
            AlertRule(
                name="redis_memory_high",
                metric_name="redis_memory_usage_percent",
                component="redis",
                threshold_value=90.0,
                comparison="gt",
                severity=AlertSeverity.WARNING,
                duration_minutes=10
            ),
            
            # Celery alerts
            AlertRule(
                name="celery_no_workers",
                metric_name="celery_active_workers",
                component="celery",
                threshold_value=1,
                comparison="lt",
                severity=AlertSeverity.CRITICAL,
                duration_minutes=2
            ),
            AlertRule(
                name="celery_queue_backlog",
                metric_name="celery_queue_length",
                component="celery",
                threshold_value=1000,
                comparison="gt",
                severity=AlertSeverity.WARNING,
                duration_minutes=5
            ),
            
            # API Performance alerts
            AlertRule(
                name="api_response_time_high",
                metric_name="api_response_time_p95",
                component="api",
                threshold_value=2000,  # 2 seconds
                comparison="gt",
                severity=AlertSeverity.WARNING,
                duration_minutes=5
            ),
            AlertRule(
                name="api_error_rate_high",
                metric_name="api_error_rate",
                component="api",
                threshold_value=5.0,  # 5% error rate
                comparison="gt",
                severity=AlertSeverity.WARNING,
                duration_minutes=5
            ),
            
            # CrewAI specific alerts
            AlertRule(
                name="crew_execution_failure_rate_high",
                metric_name="crew_execution_failure_rate",
                component="crew_execution",
                threshold_value=10.0,  # 10% failure rate
                comparison="gt",
                severity=AlertSeverity.WARNING,
                duration_minutes=10
            )
        ]
        
        for rule in default_rules:
            self._alert_rules[rule.name] = rule
    
    async def check_alert_conditions_and_store(self, db: Session, metrics: Dict[str, Dict[str, Any]]):
        """Check all alert conditions against current metrics and store to database."""
        try:
            alerts_to_store = []
            alerts_to_resolve = []
            current_time = datetime.utcnow()
            
            for rule in self._alert_rules.values():
                if not rule.enabled:
                    continue
                
                # Get current metric value
                current_value = self._extract_metric_value(metrics, rule)
                if current_value is None:
                    continue
                
                # Check if condition is met
                condition_met = self._evaluate_condition(current_value, rule.threshold_value, rule.comparison)
                alert_key = f"{rule.component}_{rule.name}"
                
                if condition_met:
                    # Check if alert already exists
                    if alert_key in self._active_alerts:
                        # Update existing alert
                        alert = self._active_alerts[alert_key]
                        alert.last_triggered = current_time
                        alert.trigger_count += 1
                        alert.current_value = current_value
                    else:
                        # Create new alert
                        alert = AlertData(
                            rule_name=rule.name,
                            component=rule.component,
                            severity=rule.severity,
                            message=self._generate_alert_message(rule, current_value),
                            current_value=current_value,
                            threshold_value=rule.threshold_value,
                            triggered_at=current_time,
                            last_triggered=current_time
                        )
                        self._active_alerts[alert_key] = alert
                        
                        # Store alert trigger
                        alerts_to_store.append(("triggered", rule, alert))
                else:
                    # Check if alert should be resolved
                    if alert_key in self._active_alerts:
                        alert = self._active_alerts[alert_key]
                        if alert.status == AlertStatus.ACTIVE:
                            alerts_to_resolve.append((rule, alert))
            
            # Store alert events to database
            await self._store_alert_events(db, alerts_to_store, alerts_to_resolve)
            
        except Exception as e:
            logger.error("Error checking alert conditions and storing", error=str(e))
    
    def _extract_metric_value(self, metrics: Dict[str, Dict[str, Any]], rule: AlertRule) -> Optional[float]:
        """Extract metric value for alert rule."""
        try:
            component_metrics = metrics.get(rule.component, {})
            return component_metrics.get(rule.metric_name)
        except Exception:
            return None
    
    def _evaluate_condition(self, current_value: float, threshold: float, comparison: str) -> bool:
        """Evaluate alert condition."""
        if comparison == "gt":
            return current_value > threshold
        elif comparison == "lt":
            return current_value < threshold
        elif comparison == "eq":
            return current_value == threshold
        elif comparison == "gte":
            return current_value >= threshold
        elif comparison == "lte":
            return current_value <= threshold
        return False
    
    def _generate_alert_message(self, rule: AlertRule, current_value: float) -> str:
        """Generate alert message."""
        return f"{rule.component} {rule.metric_name} is {current_value} (threshold: {rule.threshold_value})"
    
    async def _store_alert_events(self, db: Session, alerts_to_store: List[tuple], alerts_to_resolve: List[tuple]):
        """Store alert events to database."""
        try:
            # Store triggered alerts
            for action, rule, alert in alerts_to_store:
                await self._store_alert_history(db, rule, alert, action)
            
            # Store resolved alerts
            for rule, alert in alerts_to_resolve:
                alert.status = AlertStatus.RESOLVED
                await self._store_alert_history(db, rule, alert, "resolved")
                # Remove from active alerts
                alert_key = f"{rule.component}_{rule.name}"
                self._active_alerts.pop(alert_key, None)
                
        except Exception as e:
            logger.error("Error storing alert events", error=str(e))
    
    async def _store_alert_history(self, db: Session, rule: AlertRule, alert: AlertData, action: str):
        """Store alert history to database."""
        try:
            import json
            
            alert_record = AlertHistory(
                rule_name=rule.name,
                component=rule.component,
                severity=rule.severity.value,
                action=action,
                message=alert.message,
                current_value=alert.current_value,
                threshold_value=alert.threshold_value,
                alert_metadata=json.dumps({
                    "trigger_count": alert.trigger_count,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "last_triggered": alert.last_triggered.isoformat(),
                    "metadata": alert.metadata
                }),
                timestamp=datetime.utcnow()
            )
            
            db.add(alert_record)
            db.commit()
            
            # Also store as performance metric
            from app.models.metrics import PerformanceMetric
            
            alert_metric = PerformanceMetric(
                metric_type="alert",
                metric_name=f"{rule.component}_{action}",
                value=alert.current_value,
                unit="value",
                tags={
                    "rule_name": rule.name,
                    "component": rule.component,
                    "severity": rule.severity.value,
                    "action": action
                }
            )
            
            db.add(alert_metric)
            db.commit()
            
            logger.debug(f"Stored {action} alert for {rule.component}.{rule.name}")
            
        except Exception as e:
            db.rollback()
            logger.error("Error storing alert history", error=str(e))
    
    def add_alert_rule(self, rule: AlertRule):
        """Add a new alert rule."""
        self._alert_rules[rule.name] = rule
    
    def remove_alert_rule(self, rule_name: str):
        """Remove an alert rule."""
        if rule_name in self._alert_rules:
            del self._alert_rules[rule_name]
            # Also remove any active alerts for this rule
            keys_to_remove = [key for key in self._active_alerts.keys() if rule_name in key]
            for key in keys_to_remove:
                del self._active_alerts[key]
    
    def get_active_alerts(self) -> Dict[str, AlertData]:
        """Get all active alerts (for API endpoints)."""
        return self._active_alerts.copy()
    
    def get_alert_rules(self) -> Dict[str, AlertRule]:
        """Get all alert rules (for API endpoints)."""
        return self._alert_rules.copy()
    
    async def get_alert_statistics(self, db: Session, hours: int = 24) -> Dict[str, Any]:
        """Get alert statistics from database."""
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Get alert counts by severity
            alert_counts = {}
            for severity in ["critical", "warning", "info"]:
                count = db.query(AlertHistory).filter(
                    and_(
                        AlertHistory.timestamp >= since,
                        AlertHistory.severity == severity,
                        AlertHistory.action == "triggered"
                    )
                ).count()
                alert_counts[severity] = count
            
            # Get most common alerts
            common_alerts = db.query(AlertHistory.component, AlertHistory.rule_name)\
                .filter(
                    and_(
                        AlertHistory.timestamp >= since,
                        AlertHistory.action == "triggered"
                    )
                )\
                .group_by(AlertHistory.component, AlertHistory.rule_name)\
                .limit(10).all()
            
            return {
                "period_hours": hours,
                "alert_counts": alert_counts,
                "total_alerts": sum(alert_counts.values()),
                "active_alerts_count": len(self._active_alerts),
                "common_alerts": [{"component": c, "rule": r} for c, r in common_alerts]
            }
            
        except Exception as e:
            logger.error("Error getting alert statistics", error=str(e))
            return {"error": str(e)}

# Global instance
alert_manager = SimpleAlertManager() 