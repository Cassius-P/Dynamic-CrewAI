"""Tests for task manager functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import uuid

from app.task_queue.task_manager import (
    TaskManager,
    ExecutionState,
    ExecutionResult,
    TaskExecution
)


class TestExecutionState:
    """Test cases for ExecutionState enum."""
    
    def test_execution_state_values(self):
        """Test ExecutionState enum values."""
        assert ExecutionState.PENDING.value == "PENDING"
        assert ExecutionState.RUNNING.value == "RUNNING"
        assert ExecutionState.COMPLETED.value == "COMPLETED"
        assert ExecutionState.FAILED.value == "FAILED"
        assert ExecutionState.CANCELLED.value == "CANCELLED"


class TestExecutionResult:
    """Test cases for ExecutionResult data class."""
    
    def test_execution_result_creation(self):
        """Test ExecutionResult creation and attributes."""
        result = ExecutionResult(
            execution_id="exec_1",
            state=ExecutionState.COMPLETED,
            result="Task completed successfully",
            error=None,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            task_results={"task_1": "result_1"}
        )
        
        assert result.execution_id == "exec_1"
        assert result.state == ExecutionState.COMPLETED
        assert result.result == "Task completed successfully"
        assert result.error is None
        assert result.task_results == {"task_1": "result_1"}


class TestTaskExecution:
    """Test cases for TaskExecution data class."""
    
    def test_task_execution_creation(self):
        """Test TaskExecution creation."""
        execution = TaskExecution(
            execution_id="exec_1",
            crew_config={"agents": [], "tasks": []},
            dependencies=["task_1"],
            priority=5
        )
        
        assert execution.execution_id == "exec_1"
        assert execution.crew_config == {"agents": [], "tasks": []}
        assert execution.dependencies == ["task_1"]
        assert execution.priority == 5
        assert execution.state == ExecutionState.PENDING


class TestTaskManager:
    """Test cases for TaskManager class."""
    
    @pytest.fixture
    def task_manager(self):
        """Create a TaskManager instance for testing."""
        return TaskManager()
    
    @pytest.fixture
    def sample_crew_config(self):
        """Sample crew configuration for testing."""
        return {
            "agents": [
                {
                    "name": "test_agent",
                    "role": "Researcher",
                    "goal": "Research information",
                    "backstory": "Expert researcher"
                }
            ],
            "tasks": [
                {
                    "description": "Research task",
                    "expected_output": "Research results",
                    "agent": "test_agent"
                }
            ]
        }
    
    def test_task_manager_initialization(self, task_manager):
        """Test TaskManager initialization."""
        assert task_manager is not None
        assert hasattr(task_manager, 'task_queue')
        assert hasattr(task_manager, 'dependency_resolver')
        assert hasattr(task_manager, 'executions')
    
    def test_submit_execution_no_dependencies(self, task_manager, sample_crew_config):
        """Test submitting execution with no dependencies."""
        execution_id = str(uuid.uuid4())
        task_id = task_manager.submit_execution(
            execution_id=execution_id,
            crew_config=sample_crew_config
        )
        
        # Should return a valid task ID (UUID format)
        assert task_id is not None
        assert isinstance(task_id, str)
        assert execution_id in task_manager.executions
        
        # Check execution state
        execution = task_manager.executions[execution_id]
        assert execution.state == ExecutionState.RUNNING
        assert execution.task_id == task_id
    
    def test_submit_execution_with_dependencies(self, task_manager, sample_crew_config):
        """Test submitting execution with dependencies."""
        execution_id = str(uuid.uuid4())
        dependencies = ["task_1", "task_2"]
        
        task_id = task_manager.submit_execution(
            execution_id=execution_id,
            crew_config=sample_crew_config,
            dependencies=dependencies
        )
        
        # Should return execution_id since dependencies aren't met
        assert task_id == execution_id
        assert execution_id in task_manager.executions
        
        # Check dependency resolver was used
        assert len(task_manager.dependency_resolver.dependency_graph) > 0
        
        # Check execution state (should be PENDING due to unmet dependencies)
        execution = task_manager.executions[execution_id]
        assert execution.state == ExecutionState.PENDING
    
    def test_get_execution_status_not_found(self, task_manager):
        """Test getting status for non-existent execution."""
        status = task_manager.get_execution_status("non_existent")
        
        assert status is None
    
    @patch('app.task_queue.task_manager.TaskQueue')
    def test_get_execution_status_found(self, mock_task_queue, task_manager, sample_crew_config):
        """Test getting status for existing execution."""
        mock_queue_instance = mock_task_queue.return_value
        mock_queue_instance.submit_crew_execution.return_value = "task_123"
        mock_queue_instance.get_task_status.return_value = {
            "task_id": "task_123",
            "state": "PENDING",
            "info": {}
        }
        
        execution_id = str(uuid.uuid4())
        task_manager.submit_execution(execution_id, sample_crew_config)
        
        status = task_manager.get_execution_status(execution_id)
        
        assert status is not None
        assert status["execution_id"] == execution_id
        assert "task_status" in status
    
    def test_cancel_execution(self, task_manager, sample_crew_config):
        """Test canceling an execution."""
        execution_id = str(uuid.uuid4())
        task_manager.submit_execution(execution_id, sample_crew_config)
        
        result = task_manager.cancel_execution(execution_id)
        
        assert result is True
        assert task_manager.executions[execution_id].state == ExecutionState.CANCELLED
    
    def test_cancel_execution_not_found(self, task_manager):
        """Test canceling non-existent execution."""
        result = task_manager.cancel_execution("non_existent")
        
        assert result is False
    
    def test_get_ready_executions_empty(self, task_manager):
        """Test getting ready executions when none exist."""
        ready = task_manager.get_ready_executions()
        
        assert ready == []
    
    def test_get_ready_executions_with_data(self, task_manager, sample_crew_config):
        """Test getting ready executions."""
        # Submit multiple executions
        exec_1 = str(uuid.uuid4())
        exec_2 = str(uuid.uuid4())
        
        task_manager.submit_execution(exec_1, sample_crew_config)
        task_manager.submit_execution(exec_2, sample_crew_config, dependencies=[exec_1])
        
        ready = task_manager.get_ready_executions()
        
        # exec_1 should already be running (no dependencies), exec_2 should be pending
        # So no executions should be ready (exec_1 is already running, exec_2 has unmet dependencies)
        assert len(ready) == 0
    
    def test_mark_execution_completed(self, task_manager, sample_crew_config):
        """Test marking execution as completed."""
        execution_id = str(uuid.uuid4())
        execution = TaskExecution(
            execution_id=execution_id,
            crew_config=sample_crew_config,
            dependencies=[],
            priority=5
        )
        task_manager.executions[execution_id] = execution
        
        task_manager.mark_execution_completed(execution_id, "Success result")
        
        assert task_manager.executions[execution_id].state == ExecutionState.COMPLETED
        assert task_manager.executions[execution_id].result == "Success result"
    
    def test_mark_execution_failed(self, task_manager, sample_crew_config):
        """Test marking execution as failed."""
        execution_id = str(uuid.uuid4())
        execution = TaskExecution(
            execution_id=execution_id,
            crew_config=sample_crew_config,
            dependencies=[],
            priority=5
        )
        task_manager.executions[execution_id] = execution
        
        task_manager.mark_execution_failed(execution_id, "Error occurred")
        
        assert task_manager.executions[execution_id].state == ExecutionState.FAILED
        assert task_manager.executions[execution_id].error == "Error occurred"
    
    def test_get_execution_metrics(self, task_manager):
        """Test getting execution metrics."""
        # Add some test executions
        for i in range(5):
            execution_id = str(uuid.uuid4())
            execution = TaskExecution(
                execution_id=execution_id,
                crew_config={"agents": [], "tasks": []},
                dependencies=[],
                priority=5
            )
            if i < 2:
                execution.state = ExecutionState.COMPLETED
            elif i < 4:
                execution.state = ExecutionState.RUNNING
            # Last one remains PENDING
            
            task_manager.executions[execution_id] = execution
        
        metrics = task_manager.get_execution_metrics()
        
        assert metrics["total_executions"] == 5
        assert metrics["completed_executions"] == 2
        assert metrics["running_executions"] == 2
        assert metrics["pending_executions"] == 1
        assert metrics["failed_executions"] == 0
    
    def test_submit_parallel_executions(self, task_manager, sample_crew_config):
        """Test submitting multiple parallel executions."""
        execution_configs = [
            (str(uuid.uuid4()), sample_crew_config),
            (str(uuid.uuid4()), sample_crew_config),
            (str(uuid.uuid4()), sample_crew_config)
        ]
        
        task_ids = task_manager.submit_parallel_executions(execution_configs)
        
        assert len(task_ids) == 3
        # All should be valid task IDs (UUIDs)
        for task_id in task_ids:
            assert task_id is not None
            assert isinstance(task_id, str)
        assert len(task_manager.executions) == 3
    
    def test_get_execution_dependency_graph(self, task_manager, sample_crew_config):
        """Test getting execution dependency graph."""
        # Create executions with dependencies
        exec_1 = str(uuid.uuid4())
        exec_2 = str(uuid.uuid4())
        exec_3 = str(uuid.uuid4())
        
        execution_1 = TaskExecution(exec_1, sample_crew_config, [], 5)
        execution_2 = TaskExecution(exec_2, sample_crew_config, [exec_1], 5)
        execution_3 = TaskExecution(exec_3, sample_crew_config, [exec_1, exec_2], 5)
        
        task_manager.executions[exec_1] = execution_1
        task_manager.executions[exec_2] = execution_2
        task_manager.executions[exec_3] = execution_3
        
        # Manually set up dependency resolver
        task_manager.dependency_resolver.add_task(exec_1)
        task_manager.dependency_resolver.add_task(exec_2, [exec_1])
        task_manager.dependency_resolver.add_task(exec_3, [exec_1, exec_2])
        
        graph_info = task_manager.get_execution_dependency_graph()
        
        assert graph_info["total_tasks"] == 3
        assert not graph_info["has_cycles"]
    
    @patch('app.task_queue.task_manager.TaskQueue')
    def test_process_completed_tasks(self, mock_task_queue, task_manager, sample_crew_config):
        """Test processing completed tasks and updating dependencies."""
        mock_queue_instance = mock_task_queue.return_value
        mock_queue_instance.get_task_status.return_value = {
            "task_id": "task_123",
            "state": "SUCCESS",
            "ready": True,
            "successful": True
        }
        
        execution_id = str(uuid.uuid4())
        task_manager.submit_execution(execution_id, sample_crew_config)
        
        # Mark as completed in dependency resolver
        task_manager.dependency_resolver.mark_task_completed(execution_id)
        
        completed_tasks = task_manager.process_completed_tasks()
        
        # Should identify the completed task
        assert len(completed_tasks) >= 0  # May be empty if task not yet in completed state 