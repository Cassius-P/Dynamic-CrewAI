"""Tests for WebSocket events system."""

import pytest
from datetime import datetime
from app.websocket.events import (
    EventType, EventPriority, WebSocketEvent, EventFilter, EventRouter
)


class TestEventType:
    """Test cases for EventType enum."""
    
    def test_execution_event_types(self):
        """Test execution-related event types."""
        assert EventType.EXECUTION_STARTED == "execution.started"
        assert EventType.EXECUTION_PROGRESS == "execution.progress"
        assert EventType.EXECUTION_COMPLETED == "execution.completed"
        assert EventType.EXECUTION_FAILED == "execution.failed"
        assert EventType.EXECUTION_CANCELLED == "execution.cancelled"
    
    def test_task_event_types(self):
        """Test task-related event types."""
        assert EventType.TASK_ASSIGNED == "task.assigned"
        assert EventType.TASK_STARTED == "task.started"
        assert EventType.TASK_PROGRESS == "task.progress"
        assert EventType.TASK_COMPLETED == "task.completed"
        assert EventType.TASK_FAILED == "task.failed"
        assert EventType.TASK_CANCELLED == "task.cancelled"
    
    def test_manager_agent_event_types(self):
        """Test manager agent event types."""
        assert EventType.MANAGER_DELEGATION == "manager.delegation"
        assert EventType.MANAGER_COORDINATION == "manager.coordination"
        assert EventType.MANAGER_DECISION == "manager.decision"
        assert EventType.MANAGER_ASSIGNMENT == "manager.assignment"
    
    def test_system_event_types(self):
        """Test system event types."""
        assert EventType.SYSTEM_PERFORMANCE == "system.performance"
        assert EventType.SYSTEM_ALERT == "system.alert"
        assert EventType.SYSTEM_STATUS == "system.status"
        assert EventType.SYSTEM_ERROR == "system.error"


class TestEventPriority:
    """Test cases for EventPriority enum."""
    
    def test_priority_levels(self):
        """Test priority level values."""
        assert EventPriority.LOW == "low"
        assert EventPriority.NORMAL == "normal"
        assert EventPriority.HIGH == "high"
        assert EventPriority.CRITICAL == "critical"


class TestWebSocketEvent:
    """Test cases for WebSocketEvent model."""
    
    def test_event_creation_basic(self):
        """Test creating a basic WebSocket event."""
        event = WebSocketEvent(
            type=EventType.EXECUTION_STARTED,
            data={"execution_id": "exec_1"}
        )
        
        assert event.type == EventType.EXECUTION_STARTED
        assert event.data == {"execution_id": "exec_1"}
        assert event.priority == EventPriority.NORMAL
        assert event.timestamp is not None
        assert event.source is None
    
    def test_event_creation_with_all_fields(self):
        """Test creating an event with all fields."""
        timestamp = "2024-01-01T00:00:00Z"
        event = WebSocketEvent(
            type=EventType.TASK_COMPLETED,
            data={"task_id": "task_1", "result": "success"},
            timestamp=timestamp,
            priority=EventPriority.HIGH,
            source="task_manager",
            target="client_1",
            correlation_id="corr_123",
            metadata={"version": "1.0"}
        )
        
        assert event.type == EventType.TASK_COMPLETED
        assert event.data == {"task_id": "task_1", "result": "success"}
        assert event.timestamp == timestamp
        assert event.priority == EventPriority.HIGH
        assert event.source == "task_manager"
        assert event.target == "client_1"
        assert event.correlation_id == "corr_123"
        assert event.metadata == {"version": "1.0"}
    
    def test_event_auto_timestamp(self):
        """Test automatic timestamp generation."""
        event = WebSocketEvent(
            type=EventType.SYSTEM_STATUS,
            data={"status": "healthy"}
        )
        
        assert event.timestamp is not None
        assert event.timestamp.endswith("Z")
        
        # Should be recent timestamp
        timestamp_dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
        now = datetime.utcnow()
        diff = (now - timestamp_dt.replace(tzinfo=None)).total_seconds()
        assert diff < 5  # Should be within 5 seconds
    
    def test_to_dict(self):
        """Test converting event to dictionary."""
        event = WebSocketEvent(
            type=EventType.EXECUTION_PROGRESS,
            data={"execution_id": "exec_1", "progress": 0.5},
            priority=EventPriority.HIGH,
            source="execution_engine"
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["type"] == "execution.progress"
        assert event_dict["data"] == {"execution_id": "exec_1", "progress": 0.5}
        assert event_dict["priority"] == "high"
        assert event_dict["source"] == "execution_engine"
        assert event_dict["timestamp"] is not None
    
    def test_to_json_dict(self):
        """Test converting event to JSON-serializable dictionary."""
        event = WebSocketEvent(
            type=EventType.MEMORY_STORED,
            data={"memory_type": "short_term", "key": "test"},
            priority=EventPriority.LOW
        )
        
        json_dict = event.to_json_dict()
        
        assert json_dict["type"] == "memory.stored"
        assert json_dict["data"] == {"memory_type": "short_term", "key": "test"}
        assert json_dict["timestamp"] is not None
        # JSON dict should only contain basic fields
        assert "priority" not in json_dict
        assert "source" not in json_dict
    
    def test_create_execution_event(self):
        """Test creating execution event using factory method."""
        event = WebSocketEvent.create_execution_event(
            event_type=EventType.EXECUTION_STARTED,
            execution_id="exec_1",
            crew_id="crew_1",
            progress=0.0,
            message="Starting execution"
        )
        
        assert event.type == EventType.EXECUTION_STARTED
        assert event.source == "execution_engine"
        assert event.data["execution_id"] == "exec_1"
        assert event.data["crew_id"] == "crew_1"
        assert event.data["progress"] == 0.0
        assert event.data["message"] == "Starting execution"
    
    def test_create_execution_event_minimal(self):
        """Test creating minimal execution event."""
        event = WebSocketEvent.create_execution_event(
            event_type=EventType.EXECUTION_COMPLETED,
            execution_id="exec_1"
        )
        
        assert event.type == EventType.EXECUTION_COMPLETED
        assert event.source == "execution_engine"
        assert event.data["execution_id"] == "exec_1"
        assert "crew_id" not in event.data
        assert "progress" not in event.data
    
    def test_create_task_event(self):
        """Test creating task event using factory method."""
        event = WebSocketEvent.create_task_event(
            event_type=EventType.TASK_COMPLETED,
            task_id="task_1",
            execution_id="exec_1",
            agent_id="agent_1",
            status="completed",
            result="Task completed successfully"
        )
        
        assert event.type == EventType.TASK_COMPLETED
        assert event.source == "task_manager"
        assert event.data["task_id"] == "task_1"
        assert event.data["execution_id"] == "exec_1"
        assert event.data["agent_id"] == "agent_1"
        assert event.data["status"] == "completed"
        assert event.data["result"] == "Task completed successfully"
    
    def test_create_manager_event(self):
        """Test creating manager agent event."""
        event = WebSocketEvent.create_manager_event(
            event_type=EventType.MANAGER_DELEGATION,
            manager_id="manager_1",
            action="delegate_task",
            details={"task_id": "task_1", "agent_id": "agent_1"}
        )
        
        assert event.type == EventType.MANAGER_DELEGATION
        assert event.source == "manager_agent"
        assert event.data["manager_id"] == "manager_1"
        assert event.data["action"] == "delegate_task"
        assert event.data["details"] == {"task_id": "task_1", "agent_id": "agent_1"}
    
    def test_create_queue_event(self):
        """Test creating queue event."""
        event = WebSocketEvent.create_queue_event(
            event_type=EventType.QUEUE_TASK_ADDED,
            queue_name="default",
            task_count=5,
            task_id="task_1"
        )
        
        assert event.type == EventType.QUEUE_TASK_ADDED
        assert event.source == "task_queue"
        assert event.data["queue_name"] == "default"
        assert event.data["task_count"] == 5
        assert event.data["task_id"] == "task_1"
    
    def test_create_memory_event(self):
        """Test creating memory event."""
        event = WebSocketEvent.create_memory_event(
            event_type=EventType.MEMORY_STORED,
            memory_type="long_term",
            operation="store",
            details={"key": "test_key", "size": 1024}
        )
        
        assert event.type == EventType.MEMORY_STORED
        assert event.source == "memory_service"
        assert event.data["memory_type"] == "long_term"
        assert event.data["operation"] == "store"
        assert event.data["details"] == {"key": "test_key", "size": 1024}
    
    def test_create_system_event(self):
        """Test creating system event."""
        event = WebSocketEvent.create_system_event(
            event_type=EventType.SYSTEM_PERFORMANCE,
            component="database",
            status="healthy",
            metrics={"cpu": 25.5, "memory": 1024},
            message="System operating normally"
        )
        
        assert event.type == EventType.SYSTEM_PERFORMANCE
        assert event.source == "system"
        assert event.data["component"] == "database"
        assert event.data["status"] == "healthy"
        assert event.data["metrics"] == {"cpu": 25.5, "memory": 1024}
        assert event.data["message"] == "System operating normally"


class TestEventFilter:
    """Test cases for EventFilter."""
    
    def test_filter_creation(self):
        """Test creating an event filter."""
        event_filter = EventFilter(
            event_types=[EventType.EXECUTION_STARTED, EventType.EXECUTION_COMPLETED],
            sources=["execution_engine"],
            priority_levels=[EventPriority.HIGH, EventPriority.CRITICAL],
            targets=["client_1"]
        )
        
        assert event_filter.event_types == [EventType.EXECUTION_STARTED, EventType.EXECUTION_COMPLETED]
        assert event_filter.sources == ["execution_engine"]
        assert event_filter.priority_levels == [EventPriority.HIGH, EventPriority.CRITICAL]
        assert event_filter.targets == ["client_1"]
    
    def test_filter_matches_all_criteria(self):
        """Test filter matching when all criteria match."""
        event_filter = EventFilter(
            event_types=[EventType.EXECUTION_STARTED],
            sources=["execution_engine"],
            priority_levels=[EventPriority.HIGH],
            targets=None
        )
        
        event = WebSocketEvent(
            type=EventType.EXECUTION_STARTED,
            data={"execution_id": "exec_1"},
            priority=EventPriority.HIGH,
            source="execution_engine"
        )
        
        assert event_filter.matches(event) is True
    
    def test_filter_matches_no_criteria(self):
        """Test filter matching with no criteria (should match all)."""
        event_filter = EventFilter(
            event_types=None,
            sources=None,
            priority_levels=None,
            targets=None
        )
        
        event = WebSocketEvent(
            type=EventType.TASK_COMPLETED,
            data={"task_id": "task_1"}
        )
        
        assert event_filter.matches(event) is True
    
    def test_filter_fails_event_type(self):
        """Test filter failing on event type mismatch."""
        event_filter = EventFilter(
            event_types=[EventType.EXECUTION_STARTED],
            sources=None,
            priority_levels=None,
            targets=None
        )
        
        event = WebSocketEvent(
            type=EventType.EXECUTION_COMPLETED,
            data={"execution_id": "exec_1"}
        )
        
        assert event_filter.matches(event) is False
    
    def test_filter_fails_source(self):
        """Test filter failing on source mismatch."""
        event_filter = EventFilter(
            event_types=None,
            sources=["execution_engine"],
            priority_levels=None,
            targets=None
        )
        
        event = WebSocketEvent(
            type=EventType.TASK_COMPLETED,
            data={"task_id": "task_1"},
            source="task_manager"
        )
        
        assert event_filter.matches(event) is False
    
    def test_filter_fails_priority(self):
        """Test filter failing on priority mismatch."""
        event_filter = EventFilter(
            event_types=None,
            sources=None,
            priority_levels=[EventPriority.HIGH, EventPriority.CRITICAL],
            targets=None
        )
        
        event = WebSocketEvent(
            type=EventType.SYSTEM_STATUS,
            data={"status": "healthy"},
            priority=EventPriority.LOW
        )
        
        assert event_filter.matches(event) is False
    
    def test_filter_fails_target(self):
        """Test filter failing on target mismatch."""
        event_filter = EventFilter(
            event_types=None,
            sources=None,
            priority_levels=None,
            targets=["client_1", "client_2"]
        )
        
        event = WebSocketEvent(
            type=EventType.SYSTEM_STATUS,
            data={"status": "healthy"},
            target="client_3"
        )
        
        assert event_filter.matches(event) is False


class TestEventRouter:
    """Test cases for EventRouter."""
    
    def test_router_creation(self):
        """Test creating an event router."""
        router = EventRouter()
        assert router.filters == {}
    
    def test_add_filter(self):
        """Test adding event filter for a client."""
        router = EventRouter()
        event_filter = EventFilter(
            event_types=[EventType.EXECUTION_STARTED],
            sources=None,
            priority_levels=None,
            targets=None
        )
        
        router.add_filter("client_1", event_filter)
        
        assert "client_1" in router.filters
        assert router.filters["client_1"] == event_filter
    
    def test_remove_filter(self):
        """Test removing event filter for a client."""
        router = EventRouter()
        event_filter = EventFilter(
            event_types=[EventType.EXECUTION_STARTED],
            sources=None,
            priority_levels=None,
            targets=None
        )
        
        router.add_filter("client_1", event_filter)
        router.remove_filter("client_1")
        
        assert "client_1" not in router.filters
    
    def test_remove_nonexistent_filter(self):
        """Test removing filter for non-existent client."""
        router = EventRouter()
        
        # Should not raise an exception
        router.remove_filter("nonexistent_client")
        
        assert router.filters == {}
    
    def test_should_send_to_client_no_filter(self):
        """Test sending to client with no filter (should accept all)."""
        router = EventRouter()
        
        event = WebSocketEvent(
            type=EventType.EXECUTION_STARTED,
            data={"execution_id": "exec_1"}
        )
        
        assert router.should_send_to_client("client_1", event) is True
    
    def test_should_send_to_client_with_filter_match(self):
        """Test sending to client with matching filter."""
        router = EventRouter()
        event_filter = EventFilter(
            event_types=[EventType.EXECUTION_STARTED],
            sources=None,
            priority_levels=None,
            targets=None
        )
        router.add_filter("client_1", event_filter)
        
        event = WebSocketEvent(
            type=EventType.EXECUTION_STARTED,
            data={"execution_id": "exec_1"}
        )
        
        assert router.should_send_to_client("client_1", event) is True
    
    def test_should_send_to_client_with_filter_no_match(self):
        """Test sending to client with non-matching filter."""
        router = EventRouter()
        event_filter = EventFilter(
            event_types=[EventType.EXECUTION_STARTED],
            sources=None,
            priority_levels=None,
            targets=None
        )
        router.add_filter("client_1", event_filter)
        
        event = WebSocketEvent(
            type=EventType.EXECUTION_COMPLETED,
            data={"execution_id": "exec_1"}
        )
        
        assert router.should_send_to_client("client_1", event) is False
    
    def test_get_target_clients(self):
        """Test getting target clients for an event."""
        router = EventRouter()
        
        # Add filters for different clients
        execution_filter = EventFilter(
            event_types=[EventType.EXECUTION_STARTED],
            sources=None,
            priority_levels=None,
            targets=None
        )
        task_filter = EventFilter(
            event_types=[EventType.TASK_COMPLETED],
            sources=None,
            priority_levels=None,
            targets=None
        )
        
        router.add_filter("client_1", execution_filter)
        router.add_filter("client_2", task_filter)
        # client_3 has no filter (accepts all)
        
        all_clients = ["client_1", "client_2", "client_3"]
        
        # Test execution event
        execution_event = WebSocketEvent(
            type=EventType.EXECUTION_STARTED,
            data={"execution_id": "exec_1"}
        )
        
        target_clients = router.get_target_clients(execution_event, all_clients)
        assert set(target_clients) == {"client_1", "client_3"}
        
        # Test task event
        task_event = WebSocketEvent(
            type=EventType.TASK_COMPLETED,
            data={"task_id": "task_1"}
        )
        
        target_clients = router.get_target_clients(task_event, all_clients)
        assert set(target_clients) == {"client_2", "client_3"}
    
    def test_get_target_clients_empty_list(self):
        """Test getting target clients with empty client list."""
        router = EventRouter()
        
        event = WebSocketEvent(
            type=EventType.SYSTEM_STATUS,
            data={"status": "healthy"}
        )
        
        target_clients = router.get_target_clients(event, [])
        assert target_clients == [] 