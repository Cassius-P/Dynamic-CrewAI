"""
Alert management and notification system for monitoring.
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
    SUPPRESSED = "suppressed"
    ACKNOWLEDGED = "acknowledged"

class AlertChannel(Enum):
    """Alert notification channels."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    SMS = "sms"

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
    channels: List[AlertChannel] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ActiveAlert:
    """Represents an active alert."""
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
    channels_notified: Set[AlertChannel] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

class AlertManager:
    """Comprehensive alert management system."""
    
    def __init__(self):
        self._active_alerts: Dict[str, ActiveAlert] = {}
        self._alert_rules: Dict[str, AlertRule] = {}
        self._suppression_groups: Dict[str, Set[str]] = {}
        self._notification_cooldowns: Dict[str, datetime] = {}
        self._initialize_default_rules()
    
    def _map_alert_channel_to_notification_channel(self, alert_channel: AlertChannel):
        """Map AlertChannel to NotificationChannel for compatibility."""
        from .notifications import NotificationChannel
        
        mapping = {
            AlertChannel.EMAIL: NotificationChannel.EMAIL,
            AlertChannel.WEBHOOK: NotificationChannel.WEBHOOK,
            AlertChannel.SLACK: NotificationChannel.SLACK,
            AlertChannel.SMS: NotificationChannel.SMS
        }
        return mapping.get(alert_channel, NotificationChannel.EMAIL)
    
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
                duration_minutes=1,
                channels=[AlertChannel.EMAIL, AlertChannel.WEBHOOK]
            ),
            AlertRule(
                name="database_slow_queries",
                metric_name="database_query_time",
                component="database",
                threshold_value=5000,  # 5 seconds
                comparison="gt",
                severity=AlertSeverity.WARNING,
                duration_minutes=5,
                channels=[AlertChannel.EMAIL]
            ),
            
            # Redis alerts
            AlertRule(
                name="redis_connection_failure",
                metric_name="redis_health",
                component="redis",
                threshold_value=0.5,
                comparison="lt",
                severity=AlertSeverity.CRITICAL,
                duration_minutes=1,
                channels=[AlertChannel.EMAIL, AlertChannel.WEBHOOK]
            ),
            AlertRule(
                name="redis_memory_high",
                metric_name="redis_memory_usage_percent",
                component="redis",
                threshold_value=90.0,
                comparison="gt",
                severity=AlertSeverity.WARNING,
                duration_minutes=10,
                channels=[AlertChannel.EMAIL]
            ),
            
            # Celery alerts
            AlertRule(
                name="celery_no_workers",
                metric_name="celery_active_workers",
                component="celery",
                threshold_value=1,
                comparison="lt",
                severity=AlertSeverity.CRITICAL,
                duration_minutes=2,
                channels=[AlertChannel.EMAIL, AlertChannel.WEBHOOK]
            ),
            AlertRule(
                name="celery_queue_backlog",
                metric_name="celery_queue_length",
                component="celery",
                threshold_value=1000,
                comparison="gt",
                severity=AlertSeverity.WARNING,
                duration_minutes=5,
                channels=[AlertChannel.EMAIL]
            ),
            
            # API Performance alerts
            AlertRule(
                name="api_response_time_high",
                metric_name="api_response_time_p95",
                component="api",
                threshold_value=2000,  # 2 seconds
                comparison="gt",
                severity=AlertSeverity.WARNING,
                duration_minutes=5,
                channels=[AlertChannel.EMAIL]
            ),
            AlertRule(
                name="api_error_rate_high",
                metric_name="api_error_rate",
                component="api",
                threshold_value=5.0,  # 5% error rate
                comparison="gt",
                severity=AlertSeverity.WARNING,
                duration_minutes=5,
                channels=[AlertChannel.EMAIL]
            ),
            
            # CrewAI specific alerts
            AlertRule(
                name="crew_execution_failure_rate_high",
                metric_name="crew_execution_failure_rate",
                component="crew_execution",
                threshold_value=20.0,  # 20% failure rate
                comparison="gt",
                severity=AlertSeverity.WARNING,
                duration_minutes=10,
                channels=[AlertChannel.EMAIL]
            ),
            AlertRule(
                name="memory_system_failure",
                metric_name="memory_system_health",
                component="memory_system",
                threshold_value=0.5,
                comparison="lt",
                severity=AlertSeverity.CRITICAL,
                duration_minutes=2,
                channels=[AlertChannel.EMAIL, AlertChannel.WEBHOOK]
            ),
            
            # LLM Provider alerts
            AlertRule(
                name="llm_provider_failure",
                metric_name="llm_provider_health",
                component="llm_providers",
                threshold_value=0.5,
                comparison="lt",
                severity=AlertSeverity.WARNING,
                duration_minutes=5,
                channels=[AlertChannel.EMAIL]
            )
        ]
        
        for rule in default_rules:
            self._alert_rules[rule.name] = rule
    
    async def check_alert_conditions(self, metrics: Dict[str, Dict[str, Any]]):
        """Check all alert conditions against current metrics."""
        try:
            current_time = datetime.utcnow()
            alerts_to_trigger = []
            alerts_to_resolve = []
            
            # Check each alert rule
            for rule_name, rule in self._alert_rules.items():
                if not rule.enabled:
                    continue
                
                # Get metric value for this rule
                component_metrics = metrics.get(rule.component, {})
                current_value = component_metrics.get(rule.metric_name)
                
                if current_value is None:
                    continue
                
                # Check if condition is met
                condition_met = self._evaluate_condition(
                    current_value, rule.threshold_value, rule.comparison
                )
                
                alert_key = f"{rule.component}:{rule.name}"
                
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
                        alert = ActiveAlert(
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
                        
                        # Check if alert should trigger (duration requirement)
                        if self._should_trigger_alert(rule, alert):
                            alerts_to_trigger.append((rule, alert))
                else:
                    # Check if alert should be resolved
                    if alert_key in self._active_alerts:
                        alert = self._active_alerts[alert_key]
                        if alert.status == AlertStatus.ACTIVE:
                            alerts_to_resolve.append((rule, alert))
            
            # Process alert triggers and resolutions
            await self._process_alert_triggers(alerts_to_trigger)
            await self._process_alert_resolutions(alerts_to_resolve)
            
        except Exception as e:
            logger.error("Error checking alert conditions", error=str(e))
    
    def _evaluate_condition(self, current_value: float, threshold: float, comparison: str) -> bool:
        """Evaluate if alert condition is met."""
        if comparison == "gt":
            return current_value > threshold
        elif comparison == "gte":
            return current_value >= threshold
        elif comparison == "lt":
            return current_value < threshold
        elif comparison == "lte":
            return current_value <= threshold
        elif comparison == "eq":
            return current_value == threshold
        else:
            return False
    
    def _should_trigger_alert(self, rule: AlertRule, alert: ActiveAlert) -> bool:
        """Check if alert should trigger based on duration requirements."""
        if rule.duration_minutes == 0:
            return True
        
        duration_threshold = timedelta(minutes=rule.duration_minutes)
        time_since_first_trigger = datetime.utcnow() - alert.triggered_at
        
        return time_since_first_trigger >= duration_threshold
    
    def _generate_alert_message(self, rule: AlertRule, current_value: float) -> str:
        """Generate human-readable alert message."""
        comparison_text = {
            "gt": "greater than",
            "gte": "greater than or equal to",
            "lt": "less than",
            "lte": "less than or equal to",
            "eq": "equal to"
        }.get(rule.comparison, "compared to")
        
        return (
            f"{rule.component.replace('_', ' ').title()} alert: "
            f"{rule.metric_name} is {current_value} "
            f"({comparison_text} threshold {rule.threshold_value})"
        )
    
    async def _process_alert_triggers(self, alerts_to_trigger: List[tuple]):
        """Process alerts that need to be triggered."""
        for rule, alert in alerts_to_trigger:
            try:
                # Check if alert is suppressed
                if self._is_alert_suppressed(rule, alert):
                    alert.status = AlertStatus.SUPPRESSED
                    continue
                
                # Check notification cooldown
                if self._is_in_cooldown(rule, alert):
                    continue
                
                # Trigger alert
                await self._trigger_alert(rule, alert)
                
                # Store in database
                await self._store_alert_history(rule, alert, "triggered")
                
                logger.warning(
                    "Alert triggered",
                    rule=rule.name,
                    component=rule.component,
                    severity=rule.severity.value,
                    message=alert.message
                )
                
            except Exception as e:
                logger.error(
                    "Error processing alert trigger",
                    rule=rule.name,
                    error=str(e)
                )
    
    async def _process_alert_resolutions(self, alerts_to_resolve: List[tuple]):
        """Process alerts that should be resolved."""
        for rule, alert in alerts_to_resolve:
            try:
                alert.status = AlertStatus.RESOLVED
                
                # Send resolution notification
                await self._resolve_alert(rule, alert)
                
                # Store resolution in database
                await self._store_alert_history(rule, alert, "resolved")
                
                # Remove from active alerts
                alert_key = f"{rule.component}:{rule.name}"
                if alert_key in self._active_alerts:
                    del self._active_alerts[alert_key]
                
                logger.info(
                    "Alert resolved",
                    rule=rule.name,
                    component=rule.component,
                    message=alert.message
                )
                
            except Exception as e:
                logger.error(
                    "Error processing alert resolution",
                    rule=rule.name,
                    error=str(e)
                )
    
    def _is_alert_suppressed(self, rule: AlertRule, alert: ActiveAlert) -> bool:
        """Check if alert should be suppressed due to related component failures."""
        # Check suppression groups (e.g., if database is down, suppress memory alerts)
        suppression_map = {
            "database": ["memory_system", "crew_execution"],
            "redis": ["celery", "cache"],
            "celery": ["queue_system"]
        }
        
        for suppressor_component, suppressed_components in suppression_map.items():
            if rule.component in suppressed_components:
                # Check if suppressor component has active critical alerts
                for active_alert in self._active_alerts.values():
                    if (active_alert.component == suppressor_component and 
                        active_alert.severity == AlertSeverity.CRITICAL and
                        active_alert.status == AlertStatus.ACTIVE):
                        return True
        
        return False
    
    def _is_in_cooldown(self, rule: AlertRule, alert: ActiveAlert) -> bool:
        """Check if notification is in cooldown period."""
        cooldown_key = f"{rule.component}:{rule.name}"
        if cooldown_key in self._notification_cooldowns:
            cooldown_end = self._notification_cooldowns[cooldown_key]
            if datetime.utcnow() < cooldown_end:
                return True
        
        return False
    
    async def _trigger_alert(self, rule: AlertRule, alert: ActiveAlert):
        """Trigger alert notifications."""
        # Set cooldown for future notifications
        cooldown_minutes = {
            AlertSeverity.CRITICAL: 5,
            AlertSeverity.WARNING: 15,
            AlertSeverity.INFO: 60
        }.get(rule.severity, 15)
        
        cooldown_key = f"{rule.component}:{rule.name}"
        self._notification_cooldowns[cooldown_key] = (
            datetime.utcnow() + timedelta(minutes=cooldown_minutes)
        )
        
        # Send notifications to configured channels
        from .notifications import NotificationManager
        notification_manager = NotificationManager()
        
        for channel in rule.channels:
            try:
                # Map AlertChannel to NotificationChannel
                notification_channel = self._map_alert_channel_to_notification_channel(channel)
                await notification_manager.send_alert_notification(
                    channel=notification_channel,
                    rule=rule,
                    alert=alert
                )
                alert.channels_notified.add(channel)
            except Exception as e:
                logger.error(
                    "Failed to send alert notification",
                    channel=channel.value,
                    rule=rule.name,
                    error=str(e)
                )
    
    async def _resolve_alert(self, rule: AlertRule, alert: ActiveAlert):
        """Send alert resolution notifications."""
        from .notifications import NotificationManager
        notification_manager = NotificationManager()
        
        for channel in alert.channels_notified:
            try:
                # Map AlertChannel to NotificationChannel
                notification_channel = self._map_alert_channel_to_notification_channel(channel)
                await notification_manager.send_resolution_notification(
                    channel=notification_channel,
                    rule=rule,
                    alert=alert
                )
            except Exception as e:
                logger.error(
                    "Failed to send resolution notification",
                    channel=channel.value,
                    rule=rule.name,
                    error=str(e)
                )
    
    async def _store_alert_history(self, rule: AlertRule, alert: ActiveAlert, action: str):
        """Store alert history in database."""
        try:
            db = next(get_db())
            
            import json
            metadata_json = json.dumps({
                "trigger_count": alert.trigger_count,
                "channels_notified": [ch.value for ch in alert.channels_notified],
                "rule_metadata": rule.metadata
            })
            
            history_entry = AlertHistory(
                rule_name=rule.name,
                component=rule.component,
                severity=rule.severity.value,
                action=action,
                message=alert.message,
                current_value=alert.current_value,
                threshold_value=alert.threshold_value,
                alert_metadata=metadata_json
            )
            
            db.add(history_entry)
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error("Error storing alert history", error=str(e))
    
    def add_alert_rule(self, rule: AlertRule):
        """Add or update an alert rule."""
        self._alert_rules[rule.name] = rule
        logger.info("Alert rule added/updated", rule_name=rule.name)
    
    def remove_alert_rule(self, rule_name: str):
        """Remove an alert rule."""
        if rule_name in self._alert_rules:
            del self._alert_rules[rule_name]
            # Also remove any active alerts for this rule
            keys_to_remove = [
                key for key in self._active_alerts.keys()
                if key.endswith(f":{rule_name}")
            ]
            for key in keys_to_remove:
                del self._active_alerts[key]
            logger.info("Alert rule removed", rule_name=rule_name)
    
    def get_active_alerts(self) -> Dict[str, ActiveAlert]:
        """Get all currently active alerts."""
        return self._active_alerts.copy()
    
    def get_alert_rules(self) -> Dict[str, AlertRule]:
        """Get all configured alert rules."""
        return self._alert_rules.copy()
    
    async def acknowledge_alert(self, component: str, rule_name: str, acknowledged_by: str):
        """Acknowledge an active alert."""
        alert_key = f"{component}:{rule_name}"
        if alert_key in self._active_alerts:
            alert = self._active_alerts[alert_key]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.metadata["acknowledged_by"] = acknowledged_by
            alert.metadata["acknowledged_at"] = datetime.utcnow().isoformat()
            
            # Store acknowledgment in database
            await self._store_alert_history(
                self._alert_rules[rule_name], 
                alert, 
                f"acknowledged_by_{acknowledged_by}"
            )
            
            logger.info(
                "Alert acknowledged",
                rule_name=rule_name,
                component=component,
                acknowledged_by=acknowledged_by
            )
    
    async def get_alert_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert statistics for the specified time period."""
        try:
            db = next(get_db())
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Query alert history
            alert_history = db.query(AlertHistory).filter(
                AlertHistory.timestamp >= since
            ).all()
            
            db.close()
            
            # Calculate statistics
            total_alerts = len(alert_history)
            alerts_by_severity = {}
            alerts_by_component = {}
            resolution_times = []
            
            for alert in alert_history:
                # Count by severity
                severity = alert.severity
                alerts_by_severity[severity] = alerts_by_severity.get(severity, 0) + 1
                
                # Count by component
                component = alert.component
                alerts_by_component[component] = alerts_by_component.get(component, 0) + 1
            
            return {
                "period_hours": hours,
                "total_alerts": total_alerts,
                "active_alerts": len(self._active_alerts),
                "alerts_by_severity": alerts_by_severity,
                "alerts_by_component": alerts_by_component,
                "alert_rules_count": len(self._alert_rules),
                "suppressed_alerts": sum(
                    1 for alert in self._active_alerts.values() 
                    if alert.status == AlertStatus.SUPPRESSED
                )
            }
            
        except Exception as e:
            logger.error("Error getting alert statistics", error=str(e))
            return {}

# Global alert manager instance
alert_manager = AlertManager() 