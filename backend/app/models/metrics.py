"""
Performance metrics and cache statistics models.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON
from sqlalchemy.orm import declarative_base
from datetime import datetime
from typing import Dict, Any

Base = declarative_base()

class PerformanceMetric(Base):
    """Performance metric data points."""
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    metric_type = Column(String(50), nullable=False, index=True)  # api, function, system, cache
    metric_name = Column(String(100), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)  # seconds, count, percent, bytes
    tags = Column(JSON, default={})  # Additional metadata
    
    def to_dict(self) -> Dict[str, Any]:
        # Handle timestamp safely for model instances
        timestamp_str = None
        try:
            if self.timestamp is not None and hasattr(self.timestamp, 'isoformat'):
                timestamp_str = self.timestamp.isoformat()
            elif self.timestamp is not None:
                timestamp_str = str(self.timestamp)
        except (AttributeError, TypeError):
            timestamp_str = None
            
        return {
            "id": self.id,
            "timestamp": timestamp_str,
            "metric_type": self.metric_type,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "tags": self.tags if self.tags is not None else {}
        }

class CacheStatistic(Base):
    """Cache hit/miss and performance statistics."""
    __tablename__ = "cache_statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    cache_type = Column(String(50), nullable=False, index=True)  # l1, l2, crew_config, memory_query
    operation = Column(String(20), nullable=False, index=True)  # hit, miss, set, delete, invalidate
    key_pattern = Column(String(200), nullable=True, index=True)
    duration_ms = Column(Float, nullable=True)  # Operation duration in milliseconds
    data_size_bytes = Column(Integer, nullable=True)  # Size of cached data
    ttl_seconds = Column(Integer, nullable=True)  # TTL used for the cache entry
    
    def to_dict(self) -> Dict[str, Any]:
        timestamp_str = None
        try:
            if self.timestamp is not None and hasattr(self.timestamp, 'isoformat'):
                timestamp_str = self.timestamp.isoformat()
            elif self.timestamp is not None:
                timestamp_str = str(self.timestamp)
        except (AttributeError, TypeError):
            timestamp_str = None
            
        return {
            "id": self.id,
            "timestamp": timestamp_str,
            "cache_type": self.cache_type,
            "operation": self.operation,
            "key_pattern": self.key_pattern,
            "duration_ms": self.duration_ms,
            "data_size_bytes": self.data_size_bytes,
            "ttl_seconds": self.ttl_seconds
        }

class ResourceUsageMetric(Base):
    """System resource utilization tracking."""
    __tablename__ = "resource_usage_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    memory_used_mb = Column(Float, nullable=False)
    memory_available_mb = Column(Float, nullable=False)
    disk_usage_percent = Column(Float, nullable=False)
    active_connections = Column(Integer, default=0)
    queue_size = Column(Integer, default=0)
    active_executions = Column(Integer, default=0)
    
    def to_dict(self) -> Dict[str, Any]:
        timestamp_str = None
        try:
            if self.timestamp is not None and hasattr(self.timestamp, 'isoformat'):
                timestamp_str = self.timestamp.isoformat()
            elif self.timestamp is not None:
                timestamp_str = str(self.timestamp)
        except (AttributeError, TypeError):
            timestamp_str = None
            
        return {
            "id": self.id,
            "timestamp": timestamp_str,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_available_mb": self.memory_available_mb,
            "disk_usage_percent": self.disk_usage_percent,
            "active_connections": self.active_connections,
            "queue_size": self.queue_size,
            "active_executions": self.active_executions
        }

class QueryPerformance(Base):
    """Database query performance metrics."""
    __tablename__ = "query_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    query_type = Column(String(50), nullable=False, index=True)  # select, insert, update, delete
    table_name = Column(String(100), nullable=True, index=True)
    duration_ms = Column(Float, nullable=False)
    rows_affected = Column(Integer, nullable=True)
    query_hash = Column(String(32), nullable=True, index=True)  # MD5 hash of query
    was_cached = Column(Boolean, default=False)
    cache_hit = Column(Boolean, default=False)
    
    def to_dict(self) -> Dict[str, Any]:
        timestamp_str = None
        try:
            if self.timestamp is not None and hasattr(self.timestamp, 'isoformat'):
                timestamp_str = self.timestamp.isoformat()
            elif self.timestamp is not None:
                timestamp_str = str(self.timestamp)
        except (AttributeError, TypeError):
            timestamp_str = None
            
        return {
            "id": self.id,
            "timestamp": timestamp_str,
            "query_type": self.query_type,
            "table_name": self.table_name,
            "duration_ms": self.duration_ms,
            "rows_affected": self.rows_affected,
            "query_hash": self.query_hash,
            "was_cached": self.was_cached,
            "cache_hit": self.cache_hit
        }

class ExecutionProfile(Base):
    """Execution-specific performance data."""
    __tablename__ = "execution_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    stage = Column(String(50), nullable=False)  # start, task_assigned, task_completed, end
    agent_id = Column(String(50), nullable=True, index=True)
    task_type = Column(String(50), nullable=True)
    duration_ms = Column(Float, nullable=True)
    memory_used_mb = Column(Float, nullable=True)
    cpu_percent = Column(Float, nullable=True)
    cache_hits = Column(Integer, default=0)
    cache_misses = Column(Integer, default=0)
    llm_calls = Column(Integer, default=0)
    tool_calls = Column(Integer, default=0)
    execution_metadata = Column(JSON, default={})
    
    def to_dict(self) -> Dict[str, Any]:
        timestamp_str = None
        try:
            if self.timestamp is not None and hasattr(self.timestamp, 'isoformat'):
                timestamp_str = self.timestamp.isoformat()
            elif self.timestamp is not None:
                timestamp_str = str(self.timestamp)
        except (AttributeError, TypeError):
            timestamp_str = None
            
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "timestamp": timestamp_str,
            "stage": self.stage,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "duration_ms": self.duration_ms,
            "memory_used_mb": self.memory_used_mb,
            "cpu_percent": self.cpu_percent,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "metadata": self.execution_metadata if self.execution_metadata is not None else {}
        }

class AlertThreshold(Base):
    """Performance alerting thresholds."""
    __tablename__ = "alert_thresholds"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_type = Column(String(50), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    warning_threshold = Column(Float, nullable=True)
    critical_threshold = Column(Float, nullable=True)
    comparison_operator = Column(String(10), default="gt")  # gt, lt, eq, gte, lte
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        # Handle timestamps safely for model instances
        created_at_str = None
        try:
            if self.created_at is not None and hasattr(self.created_at, 'isoformat'):
                created_at_str = self.created_at.isoformat()
            elif self.created_at is not None:
                created_at_str = str(self.created_at)
        except (AttributeError, TypeError):
            created_at_str = None
            
        updated_at_str = None
        try:
            if self.updated_at is not None and hasattr(self.updated_at, 'isoformat'):
                updated_at_str = self.updated_at.isoformat()
            elif self.updated_at is not None:
                updated_at_str = str(self.updated_at)
        except (AttributeError, TypeError):
            updated_at_str = None
            
        return {
            "id": self.id,
            "metric_type": self.metric_type,
            "metric_name": self.metric_name,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "comparison_operator": self.comparison_operator,
            "enabled": self.enabled,
            "created_at": created_at_str,
            "updated_at": updated_at_str
        } 