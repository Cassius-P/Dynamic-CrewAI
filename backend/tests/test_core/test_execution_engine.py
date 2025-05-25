"""Tests for the ExecutionEngine class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.core.execution_engine import ExecutionEngine
from app.models.execution import ExecutionStatus


class TestExecutionEngine:
    """Test cases for the ExecutionEngine class."""

    def test_init(self):
        """Test ExecutionEngine initialization."""
        engine = ExecutionEngine()
        assert engine is not None
        assert hasattr(engine, 'crew_wrapper')

    @patch('app.core.execution_engine.CrewWrapper')
    def test_execute_crew_from_config_success(self, mock_crew_wrapper):
        """Test successful crew execution from config."""
        # Setup mocks
        mock_wrapper_instance = Mock()
        mock_crew_wrapper.return_value = mock_wrapper_instance
        
        mock_crew = Mock()
        mock_crew.kickoff.return_value = "Task completed successfully"
        mock_wrapper_instance.create_crew_from_dict.return_value = mock_crew
        
        crew_config = {
            "name": "Test Crew",
            "agents": [
                {
                    "name": "Test Agent",
                    "role": "Tester",
                    "goal": "Test things",
                    "backstory": "Expert tester"
                }
            ],
            "tasks": [
                {
                    "description": "Test the application",
                    "expected_output": "Test results",
                    "agent": "Test Agent"
                }
            ]
        }
        
        engine = ExecutionEngine()
        result = engine.execute_crew_from_config(crew_config)
        
        # Verify results
        assert result["status"] == ExecutionStatus.COMPLETED
        assert result["result"] == "Task completed successfully"
        assert result["error"] is None
        assert "execution_id" in result
        assert "start_time" in result
        assert "end_time" in result
        assert "execution_time" in result

    @patch('app.core.execution_engine.CrewWrapper')
    def test_execute_crew_from_config_failure(self, mock_crew_wrapper):
        """Test crew execution failure from config."""
        # Setup mocks
        mock_wrapper_instance = Mock()
        mock_crew_wrapper.return_value = mock_wrapper_instance
        
        mock_wrapper_instance.create_crew_from_dict.side_effect = Exception("Crew creation failed")
        
        crew_config = {
            "name": "Test Crew",
            "agents": [],
            "tasks": []
        }
        
        engine = ExecutionEngine()
        result = engine.execute_crew_from_config(crew_config)
        
        # Verify results
        assert result["status"] == ExecutionStatus.FAILED
        assert result["result"] is None
        assert "Crew creation failed" in result["error"]
        assert "execution_id" in result
        assert "traceback" in result

    def test_validate_crew_config_valid(self):
        """Test validation of valid crew configuration."""
        crew_config = {
            "name": "Test Crew",
            "agents": [
                {
                    "name": "Agent 1",
                    "role": "Developer",
                    "goal": "Write code",
                    "backstory": "Expert developer"
                }
            ],
            "tasks": [
                {
                    "description": "Write Python code",
                    "expected_output": "Python script",
                    "agent": "Agent 1"
                }
            ]
        }
        
        engine = ExecutionEngine()
        result = engine.validate_crew_config(crew_config)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_crew_config_missing_agents(self):
        """Test validation with missing agents."""
        crew_config = {
            "name": "Test Crew",
            "tasks": [
                {
                    "description": "Write code",
                    "expected_output": "Code",
                    "agent": "Agent 1"
                }
            ]
        }
        
        engine = ExecutionEngine()
        result = engine.validate_crew_config(crew_config)
        
        assert result["valid"] is False
        assert "must have at least one agent" in str(result["errors"])

    def test_validate_crew_config_missing_tasks(self):
        """Test validation with missing tasks."""
        crew_config = {
            "name": "Test Crew",
            "agents": [
                {
                    "name": "Agent 1",
                    "role": "Developer",
                    "goal": "Write code",
                    "backstory": "Expert"
                }
            ]
        }
        
        engine = ExecutionEngine()
        result = engine.validate_crew_config(crew_config)
        
        assert result["valid"] is False
        assert "must have at least one task" in str(result["errors"])

    def test_validate_crew_config_invalid_agent(self):
        """Test validation with invalid agent configuration."""
        crew_config = {
            "name": "Test Crew",
            "agents": [
                {
                    "name": "Agent 1",
                    # Missing role, goal, backstory
                }
            ],
            "tasks": [
                {
                    "description": "Write code",
                    "expected_output": "Code",
                    "agent": "Agent 1"
                }
            ]
        }
        
        engine = ExecutionEngine()
        result = engine.validate_crew_config(crew_config)
        
        assert result["valid"] is False
        assert any("missing required field" in error for error in result["errors"])

    def test_create_execution_record(self):
        """Test creating execution record for database storage."""
        crew_config = {
            "name": "Test Crew",
            "process": "sequential",
            "agents": [
                {
                    "name": "Agent 1",
                    "role": "Developer",
                    "goal": "Write code",
                    "backstory": "Expert",
                    "tools": ["file_read_tool"]
                }
            ],
            "tasks": [
                {
                    "description": "Write code",
                    "expected_output": "Code",
                    "agent": "Agent 1"
                }
            ]
        }
        
        execution_result = {
            "execution_id": "test-id-123",
            "status": ExecutionStatus.COMPLETED,
            "result": "Task completed",
            "start_time": "2023-01-01T00:00:00",
            "end_time": "2023-01-01T00:01:00",
            "execution_time": 60.0,
            "error": None
        }
        
        engine = ExecutionEngine()
        record = engine.create_execution_record(crew_config, execution_result)
        
        assert record["id"] == "test-id-123"
        assert record["status"] == ExecutionStatus.COMPLETED
        assert record["result"] == "Task completed"
        assert record["error_message"] is None
        assert record["execution_time"] == 60.0
        assert record["metadata"]["agent_count"] == 1
        assert record["metadata"]["task_count"] == 1
        assert record["metadata"]["has_tools"] is True
        assert record["metadata"]["process_type"] == "sequential"

    def test_get_execution_status_placeholder(self):
        """Test get_execution_status placeholder method."""
        engine = ExecutionEngine()
        status = engine.get_execution_status("test-id")
        
        # For Phase 2, this should return None (placeholder)
        assert status is None
