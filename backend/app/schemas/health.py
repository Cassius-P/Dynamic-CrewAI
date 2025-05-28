"""
Enhanced health check schemas for comprehensive monitoring.
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime


class HealthResponse(BaseModel):
    """Schema for basic health check response."""
    status: str
    version: str
    database: str
    timestamp: str
    details: Dict[str, Any] = {}


class ComponentHealthResponse(BaseModel):
    """Schema for individual component health response."""
    name: str
    status: str
    message: str
    response_time_ms: Optional[float] = None
    last_checked: Optional[str] = None
    details: Dict[str, Any] = {}
    dependencies: List[str] = []


class AlertSummaryResponse(BaseModel):
    """Schema for alert summary response."""
    active_alerts: List[Dict[str, Any]]
    alert_statistics: Dict[str, Any]
    timestamp: str


class DetailedHealthResponse(BaseModel):
    """Schema for comprehensive health check response."""
    overall_status: str
    overall_message: str
    timestamp: str
    components: Dict[str, ComponentHealthResponse]
    alert_summary: Dict[str, Any]
    system_info: Dict[str, Any]
    performance_summary: Dict[str, Any]


class MonitoringDashboardResponse(BaseModel):
    """Schema for monitoring dashboard data."""
    overall_health_score: float = Field(..., ge=0, le=100, description="Overall system health percentage")
    system_status: str
    active_alerts_count: int = Field(..., ge=0)
    performance_summary: Dict[str, Any]
    alert_statistics: Dict[str, Any]
    cache_analytics: Dict[str, Any]
    component_health_summary: Dict[str, Dict[str, Any]]
    performance_issues: List[Dict[str, Any]]
    timestamp: str


class SystemMetricsResponse(BaseModel):
    """Schema for system metrics response."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    active_connections: int
    queue_size: int
    active_executions: int
    timestamp: str


class PerformanceMetricsResponse(BaseModel):
    """Schema for performance metrics response."""
    api_response_times: Dict[str, float]
    database_query_times: Dict[str, float]
    cache_hit_rates: Dict[str, float]
    crew_execution_times: Dict[str, float]
    error_rates: Dict[str, float]
    throughput_metrics: Dict[str, float]
    timestamp: str


class AlertConfigurationRequest(BaseModel):
    """Schema for alert configuration requests."""
    name: str
    metric_name: str
    component: str
    threshold_value: float
    comparison: str = Field(..., description="Comparison operator: gt, gte, lt, lte, eq")
    severity: str = Field(..., description="Alert severity: critical, warning, info")
    duration_minutes: int = Field(5, ge=0, le=1440)
    channels: List[str] = []
    enabled: bool = True
    metadata: Dict[str, Any] = {}


class AlertConfigurationResponse(BaseModel):
    """Schema for alert configuration response."""
    name: str
    metric_name: str
    component: str
    threshold_value: float
    comparison: str
    severity: str
    duration_minutes: int
    channels: List[str]
    enabled: bool
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


class NotificationTestRequest(BaseModel):
    """Schema for notification channel test requests."""
    channel: str = Field(..., description="Notification channel: email, webhook, slack, sms")
    test_message: Optional[str] = "Test notification from CrewAI Backend"


class NotificationTestResponse(BaseModel):
    """Schema for notification test response."""
    channel: str
    success: bool
    message: str
    timestamp: str


class HealthCheckConfigRequest(BaseModel):
    """Schema for health check configuration."""
    component: str
    enabled: bool = True
    timeout_seconds: int = Field(10, ge=1, le=60)
    cache_ttl_seconds: int = Field(30, ge=0, le=300)
    custom_checks: Dict[str, Any] = {}


class BenchmarkResult(BaseModel):
    """Schema for performance benchmark results."""
    benchmark_name: str
    target_value: float
    actual_value: float
    unit: str
    status: str  # "pass", "fail", "warning"
    description: str
    timestamp: str


class SystemBenchmarkResponse(BaseModel):
    """Schema for comprehensive system benchmark response."""
    overall_score: float = Field(..., ge=0, le=100)
    benchmark_results: List[BenchmarkResult]
    performance_grade: str  # "A", "B", "C", "D", "F"
    recommendations: List[str]
    timestamp: str


class MaintenanceWindowRequest(BaseModel):
    """Schema for maintenance window configuration."""
    start_time: str  # ISO format datetime
    end_time: str    # ISO format datetime
    description: str
    affected_components: List[str] = []
    suppress_alerts: bool = True
    notification_channels: List[str] = []


class MaintenanceWindowResponse(BaseModel):
    """Schema for maintenance window response."""
    id: str
    start_time: str
    end_time: str
    description: str
    affected_components: List[str]
    suppress_alerts: bool
    status: str  # "scheduled", "active", "completed", "cancelled"
    created_by: str
    created_at: str


class HealthTrendResponse(BaseModel):
    """Schema for health trend analysis."""
    component: str
    time_period_hours: int
    trend_data: List[Dict[str, Any]]  # Time series data
    trend_direction: str  # "improving", "stable", "degrading"
    average_health_score: float
    health_volatility: float
    incidents_count: int
    timestamp: str


class ComplianceCheckResponse(BaseModel):
    """Schema for compliance and security health checks."""
    security_score: float = Field(..., ge=0, le=100)
    compliance_checks: List[Dict[str, Any]]
    vulnerabilities: List[Dict[str, Any]]
    recommendations: List[str]
    last_scan: str
    next_scan: str


class ResourceUsageResponse(BaseModel):
    """Schema for detailed resource usage metrics."""
    cpu_usage: Dict[str, float]
    memory_usage: Dict[str, float]
    disk_usage: Dict[str, float]
    network_usage: Dict[str, float]
    database_connections: Dict[str, int]
    cache_usage: Dict[str, float]
    queue_metrics: Dict[str, int]
    predictions: Dict[str, Any]  # Resource usage predictions
    timestamp: str
