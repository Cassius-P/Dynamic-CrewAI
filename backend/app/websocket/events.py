"""WebSocket event system for real-time updates."""

from enum import Enum
from typing import Any, Dict, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """WebSocket event types for different system events."""
    
    # Execution Events
    EXECUTION_STARTED = "execution.started"
    EXECUTION_PROGRESS = "execution.progress"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"
    EXECUTION_CANCELLED = "execution.cancelled"
    
    # Task Events
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    
    # Manager Agent Events
    MANAGER_DELEGATION = "manager.delegation"
    MANAGER_COORDINATION = "manager.coordination"
    MANAGER_DECISION = "manager.decision"
    MANAGER_ASSIGNMENT = "manager.assignment"
    
    # Queue Events
    QUEUE_TASK_ADDED = "queue.task_added"
    QUEUE_TASK_PROCESSING = "queue.task_processing"
    QUEUE_TASK_COMPLETED = "queue.task_completed"
    QUEUE_BACKLOG_CHANGED = "queue.backlog_changed"
    
    # Memory Events
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_CLEARED = "memory.cleared"
    MEMORY_UPDATED = "memory.updated"
    
    # System Events
    SYSTEM_PERFORMANCE = "system.performance"
    SYSTEM_ALERT = "system.alert"
    SYSTEM_STATUS = "system.status"
    SYSTEM_ERROR = "system.error"
    
    # Connection Events
    CONNECTION_ESTABLISHED = "connection.established"
    CONNECTION_TERMINATED = "connection.terminated"
    CONNECTION_ERROR = "connection.error"
    
    # Crew Events
    CREW_CREATED = "crew.created"
    CREW_UPDATED = "crew.updated"
    CREW_DELETED = "crew.deleted"
    
    # Agent Events
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"


class EventPriority(str, Enum):
    """Event priority levels for message handling."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class WebSocketEvent(BaseModel):
    """WebSocket event model for structured event data."""
    
    type: EventType = Field(..., description="Type of the event")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload data")
    timestamp: Optional[str] = Field(None, description="Event timestamp in ISO format")
    priority: EventPriority = Field(default=EventPriority.NORMAL, description="Event priority")
    source: Optional[str] = Field(None, description="Source of the event (service/component)")
    target: Optional[str] = Field(None, description="Target client or group")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracking related events")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def __init__(self, **data):
        """Initialize event with current timestamp if not provided."""
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.utcnow().isoformat() + "Z"
        super().__init__(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for WebSocket transmission."""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "source": self.source,
            "target": self.target,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata
        }
    
    def to_json_dict(self) -> Dict[str, Any]:
        """Convert event to JSON-serializable dictionary."""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def create_execution_event(
        cls,
        event_type: EventType,
        execution_id: str,
        crew_id: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
        **kwargs
    ) -> "WebSocketEvent":
        """Create an execution-related event."""
        data: Dict[str, Any] = {"execution_id": execution_id}
        if crew_id:
            data["crew_id"] = crew_id
        if progress is not None:
            data["progress"] = progress
        if message:
            data["message"] = message
        if error:
            data["error"] = error
        
        return cls(
            type=event_type,
            data=data,
            source="execution_engine",
            **kwargs
        )
    
    @classmethod
    def create_task_event(
        cls,
        event_type: EventType,
        task_id: str,
        execution_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        result: Optional[str] = None,
        error: Optional[str] = None,
        **kwargs
    ) -> "WebSocketEvent":
        """Create a task-related event."""
        data: Dict[str, Any] = {"task_id": task_id}
        if execution_id:
            data["execution_id"] = execution_id
        if agent_id:
            data["agent_id"] = agent_id
        if status:
            data["status"] = status
        if result:
            data["result"] = result
        if error:
            data["error"] = error
        
        return cls(
            type=event_type,
            data=data,
            source="task_manager",
            **kwargs
        )
    
    @classmethod
    def create_manager_event(
        cls,
        event_type: EventType,
        manager_id: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> "WebSocketEvent":
        """Create a manager agent event."""
        data: Dict[str, Any] = {
            "manager_id": manager_id,
            "action": action
        }
        if details:
            data["details"] = details
        
        return cls(
            type=event_type,
            data=data,
            source="manager_agent",
            **kwargs
        )
    
    @classmethod
    def create_queue_event(
        cls,
        event_type: EventType,
        queue_name: str,
        task_count: Optional[int] = None,
        task_id: Optional[str] = None,
        **kwargs
    ) -> "WebSocketEvent":
        """Create a queue-related event."""
        data: Dict[str, Any] = {"queue_name": queue_name}
        if task_count is not None:
            data["task_count"] = task_count
        if task_id:
            data["task_id"] = task_id
        
        return cls(
            type=event_type,
            data=data,
            source="task_queue",
            **kwargs
        )
    
    @classmethod
    def create_memory_event(
        cls,
        event_type: EventType,
        memory_type: str,
        operation: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> "WebSocketEvent":
        """Create a memory-related event."""
        data: Dict[str, Any] = {
            "memory_type": memory_type,
            "operation": operation
        }
        if details:
            data["details"] = details
        
        return cls(
            type=event_type,
            data=data,
            source="memory_service",
            **kwargs
        )
    
    @classmethod
    def create_system_event(
        cls,
        event_type: EventType,
        component: str,
        status: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        **kwargs
    ) -> "WebSocketEvent":
        """Create a system-related event."""
        data: Dict[str, Any] = {"component": component}
        if status:
            data["status"] = status
        if metrics:
            data["metrics"] = metrics
        if message:
            data["message"] = message
        
        return cls(
            type=event_type,
            data=data,
            source="system",
            **kwargs
        )


class EventFilter(BaseModel):
    """Filter for WebSocket events based on various criteria."""
    
    event_types: Optional[list[EventType]] = Field(None, description="Allowed event types")
    sources: Optional[list[str]] = Field(None, description="Allowed event sources")
    priority_levels: Optional[list[EventPriority]] = Field(None, description="Allowed priority levels")
    targets: Optional[list[str]] = Field(None, description="Allowed targets")
    
    def matches(self, event: WebSocketEvent) -> bool:
        """Check if an event matches this filter."""
        if self.event_types and event.type not in self.event_types:
            return False
        
        if self.sources and event.source not in self.sources:
            return False
        
        if self.priority_levels and event.priority not in self.priority_levels:
            return False
        
        if self.targets and event.target not in self.targets:
            return False
        
        return True


class EventRouter:
    """Routes events to appropriate WebSocket connections."""
    
    def __init__(self):
        self.filters: Dict[str, EventFilter] = {}
    
    def add_filter(self, client_id: str, event_filter: EventFilter):
        """Add event filter for a client."""
        self.filters[client_id] = event_filter
    
    def remove_filter(self, client_id: str):
        """Remove event filter for a client."""
        self.filters.pop(client_id, None)
    
    def should_send_to_client(self, client_id: str, event: WebSocketEvent) -> bool:
        """Check if event should be sent to a specific client."""
        if client_id not in self.filters:
            return True  # No filter means accept all events
        
        return self.filters[client_id].matches(event)
    
    def get_target_clients(self, event: WebSocketEvent, all_clients: list[str]) -> list[str]:
        """Get list of clients that should receive this event."""
        target_clients = []
        
        for client_id in all_clients:
            if self.should_send_to_client(client_id, event):
                target_clients.append(client_id)
        
        return target_clients 