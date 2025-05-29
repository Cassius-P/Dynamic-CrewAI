"""Tests for task queue functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import uuid
import json

from app.task_queue.task_queue import (
    CrewExecutionTask,
    TaskQueue,
    TaskState,
    TaskResult,
    execute_crew_task,
    retry_failed_task,
    cancel_task
)


class TestTaskQueue:
    """Test cases for TaskQueue class."""
    
    @pytest.fixture
    def task_queue(self):
        """Create a TaskQueue instance for testing."""
        return TaskQueue()
    
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
    
    def test_task_queue_initialization(self, task_queue):
        """Test TaskQueue initialization."""
        assert task_queue is not None
        assert hasattr(task_queue, 'celery_app')
        assert hasattr(task_queue, 'redis_client')
    
    def test_submit_crew_execution(self, task_queue, sample_crew_config):
        """Test submitting crew execution to queue."""
        # Test basic submission
        execution_id = str(uuid.uuid4())
        task_id = task_queue.submit_crew_execution(
            execution_id=execution_id,
            crew_config=sample_crew_config
        )
        
        assert task_id is not None
        assert isinstance(task_id, str)
    
    def test_submit_crew_execution_with_dependencies(self, task_queue, sample_crew_config):
        """Test submitting crew execution with task dependencies."""
        execution_id = str(uuid.uuid4())
        dependencies = ["task_1", "task_2"]
        
        task_id = task_queue.submit_crew_execution(
            execution_id=execution_id,
            crew_config=sample_crew_config,
            dependencies=dependencies
        )
        
        assert task_id is not None
    
    def test_get_task_status(self, task_queue):
        """Test getting task status."""
        task_id = str(uuid.uuid4())
        
        # Mock Celery AsyncResult
        with patch('app.task_queue.task_queue.AsyncResult') as mock_result:
            mock_result.return_value.state = 'PENDING'
            mock_result.return_value.info = {}
            
            status = task_queue.get_task_status(task_id)
            
            assert status is not None
            assert 'state' in status
            assert 'info' in status
    
    def test_cancel_task(self, task_queue):
        """Test canceling a task."""
        task_id = str(uuid.uuid4())
        
        with patch('app.task_queue.task_queue.celery_app.control.revoke') as mock_revoke:
            result = task_queue.cancel_task(task_id)
            
            mock_revoke.assert_called_once_with(task_id, terminate=True)
            assert result is True
    
    def test_get_queue_metrics(self, task_queue):
        """Test getting queue metrics."""
        with patch.object(task_queue, '_get_redis_metrics') as mock_redis_metrics:
            mock_redis_metrics.return_value = {
                'active_tasks': 5,
                'pending_tasks': 3,
                'failed_tasks': 1,
                'completed_tasks': 10
            }
            
            metrics = task_queue.get_queue_metrics()
            
            assert 'active_tasks' in metrics
            assert 'pending_tasks' in metrics
            assert 'failed_tasks' in metrics
            assert 'completed_tasks' in metrics


class TestCrewExecutionTask:
    """Test cases for CrewExecutionTask Celery task."""
    
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
    
    @patch('app.task_queue.task_queue.ExecutionEngine')
    def test_execute_crew_task_success(self, mock_execution_engine, sample_crew_config):
        """Test successful crew task execution."""
        # Mock successful execution
        mock_engine = mock_execution_engine.return_value
        mock_engine.execute_crew_from_config.return_value = {
            "execution_id": "test_id",
            "status": "COMPLETED",
            "result": "Success",
            "error": None
        }
        
        # Create a mock self object for the Celery task
        mock_self = Mock()
        mock_self.request.id = "mock_task_id"
        mock_self.request.retries = 0
        mock_self.max_retries = 3
        mock_self.update_state = Mock()
        
        # Call the function directly using the original implementation
        result = execute_crew_task.__wrapped__(
            mock_self,
            "test_id",
            sample_crew_config
        )
        
        assert result["status"] == "COMPLETED"
        assert result["result"] == "Success"
        assert result["error"] is None
    
    @patch('app.task_queue.task_queue.ExecutionEngine')
    def test_execute_crew_task_failure(self, mock_execution_engine, sample_crew_config):
        """Test crew task execution failure."""
        # Mock failed execution
        mock_engine = mock_execution_engine.return_value
        mock_engine.execute_crew_from_config.side_effect = Exception("Execution failed")
        
        # Create a mock self object for the Celery task
        mock_self = Mock()
        mock_self.request.id = "mock_task_id"
        mock_self.request.retries = 0
        mock_self.max_retries = 3
        mock_self.update_state = Mock()
        
        # Call the function directly using the original implementation
        result = execute_crew_task.__wrapped__(
            mock_self,
            "test_id",
            sample_crew_config
        )
        
        assert result["status"] == "FAILED"
        assert result["error"] is not None
        assert "Execution failed" in result["error"]
    
    def test_retry_failed_task(self):
        """Test retrying a failed task."""
        task_id = str(uuid.uuid4())
        
        with patch('app.task_queue.task_queue.AsyncResult') as mock_async_result:
            with patch('app.task_queue.task_queue.execute_crew_task.retry') as mock_retry:
                # Mock the AsyncResult to return FAILURE state
                mock_result = mock_async_result.return_value
                mock_result.state = 'FAILURE'
                
                retry_failed_task(task_id, max_retries=3, countdown=60)
                mock_retry.assert_called_once()
    
    def test_cancel_task_function(self):
        """Test the cancel task function."""
        task_id = str(uuid.uuid4())
        
        with patch('app.task_queue.task_queue.celery_app.control.revoke') as mock_revoke:
            result = cancel_task(task_id)
            
            mock_revoke.assert_called_once_with(task_id, terminate=True)
            assert result is True


class TestTaskState:
    """Test cases for TaskState enum."""
    
    def test_task_state_values(self):
        """Test TaskState enum values."""
        assert TaskState.PENDING.value == "PENDING"
        assert TaskState.STARTED.value == "STARTED"
        assert TaskState.SUCCESS.value == "SUCCESS"
        assert TaskState.FAILURE.value == "FAILURE"
        assert TaskState.RETRY.value == "RETRY"
        assert TaskState.REVOKED.value == "REVOKED"


class TestTaskResult:
    """Test cases for TaskResult data class."""
    
    def test_task_result_creation(self):
        """Test TaskResult creation and attributes."""
        result = TaskResult(
            task_id="test_task",
            execution_id="test_execution",
            state=TaskState.SUCCESS,
            result="Task completed",
            error=None,
            traceback=None,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            retries=0
        )
        
        assert result.task_id == "test_task"
        assert result.execution_id == "test_execution"
        assert result.state == TaskState.SUCCESS
        assert result.result == "Task completed"
        assert result.error is None
        assert result.retries == 0
    
    def test_task_result_serialization(self):
        """Test TaskResult to/from dict conversion."""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(seconds=30)
        
        result = TaskResult(
            task_id="test_task",
            execution_id="test_execution",
            state=TaskState.SUCCESS,
            result="Task completed",
            error=None,
            traceback=None,
            start_time=start_time,
            end_time=end_time,
            retries=0
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["task_id"] == "test_task"
        assert result_dict["state"] == "SUCCESS"
        assert "start_time" in result_dict
        assert "end_time" in result_dict
        
        # Test from_dict
        restored_result = TaskResult.from_dict(result_dict)
        assert restored_result.task_id == result.task_id
        assert restored_result.state == result.state


@pytest.mark.integration
class TestTaskQueueIntegration:
    """Integration tests for task queue with Redis."""
    
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
    
    @pytest.fixture
    def redis_task_queue(self):
        """Create TaskQueue with real Redis connection for integration tests."""
        # Note: Requires Redis to be running
        queue = TaskQueue(redis_url="redis://localhost:6379/1")  # Use test DB
        yield queue
        # Cleanup after test
        if queue.redis_client:
            queue.redis_client.flushdb()
    
    def test_task_queue_redis_integration(self, redis_task_queue, sample_crew_config):
        """Test TaskQueue with real Redis integration."""
        execution_id = str(uuid.uuid4())
        
        task_id = redis_task_queue.submit_crew_execution(
            execution_id=execution_id,
            crew_config=sample_crew_config
        )
        
        # Verify task was submitted
        assert task_id is not None
        
        # Check task status
        status = redis_task_queue.get_task_status(task_id)
        assert status is not None
    
    @pytest.mark.skip(reason="Requires Redis and Celery worker running")
    def test_end_to_end_task_execution(self, redis_task_queue, sample_crew_config):
        """Test end-to-end task execution."""
        execution_id = str(uuid.uuid4())
        
        task_id = redis_task_queue.submit_crew_execution(
            execution_id=execution_id,
            crew_config=sample_crew_config
        )
        
        # Wait for task completion (in real scenario)
        # This would require proper async handling
        assert task_id is not None 