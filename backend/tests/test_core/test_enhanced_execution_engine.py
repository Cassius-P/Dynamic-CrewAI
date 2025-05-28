"""Tests for enhanced ExecutionEngine with manager agent coordination."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any

from app.core.execution_engine import ExecutionEngine
from app.models.agent import Agent as AgentModel
from app.models.execution import ExecutionStatus
from crewai import Crew


class TestEnhancedExecutionEngine:
    """Test cases for enhanced ExecutionEngine with manager agent support."""

    @pytest.fixture
    def execution_engine(self):
        """Create an ExecutionEngine instance for testing."""
        return ExecutionEngine()

    @pytest.fixture
    def manager_agent_model(self):
        """Create a manager agent model for testing."""
        return AgentModel(
            id=1,
            role="Project Manager",
            goal="Coordinate team tasks and ensure project success",
            backstory="Experienced project manager with team coordination skills",
            allow_delegation=True,
            manager_type="hierarchical",
            can_generate_tasks=True,
            manager_config={
                "task_generation_llm": "gpt-4",
                "max_tasks_per_request": 5,
                "delegation_strategy": "round_robin"
            }
        )

    @pytest.fixture
    def regular_agent_model(self):
        """Create a regular agent model for testing."""
        return AgentModel(
            id=2,
            role="Software Developer",
            goal="Write high-quality code",
            backstory="Experienced software developer",
            allow_delegation=False,
            manager_type=None,
            can_generate_tasks=False
        )

    def test_execution_engine_initialization_with_manager_wrapper(self, execution_engine):
        """Test ExecutionEngine initialization includes manager agent wrapper."""
        assert execution_engine is not None
        assert hasattr(execution_engine, 'crew_wrapper')
        assert hasattr(execution_engine, 'manager_agent_wrapper')

    def test_execute_crew_with_manager_tasks(self, execution_engine, manager_agent_model, regular_agent_model):
        """Test executing crew with manager agent task generation."""
        agents = [manager_agent_model, regular_agent_model]
        text_input = "Create a web application with user authentication and dashboard"
        
        # Mock the crew_wrapper attribute directly on the execution_engine instance
        mock_crew = Mock(spec=Crew)
        mock_crew.kickoff.return_value = "Execution completed successfully"
        mock_crew.tasks = [Mock(), Mock()]  # Mock tasks for count
        
        with patch.object(execution_engine, 'crew_wrapper') as mock_crew_wrapper:
            mock_crew_wrapper.create_crew_with_manager_tasks.return_value = mock_crew
            
            # Execute
            result = execution_engine.execute_crew_with_manager_tasks(agents, text_input)
            
            # Verify crew creation was called
            mock_crew_wrapper.create_crew_with_manager_tasks.assert_called_once_with(
                agents, text_input
            )
            
            # Verify crew execution
            mock_crew.kickoff.assert_called_once()
            
            # Verify result structure
            assert result["status"] == ExecutionStatus.COMPLETED
            assert result["manager_agent_used"] is True
            assert result["text_input"] == text_input
            assert result["generated_tasks_count"] == 2
            assert "execution_id" in result
            assert "start_time" in result
            assert "end_time" in result

    def test_execute_crew_with_manager_tasks_failure(self, execution_engine, manager_agent_model, regular_agent_model):
        """Test handling of execution failure with manager agent."""
        agents = [manager_agent_model, regular_agent_model]
        text_input = "Create a web application"
        
        # Mock the crew_wrapper attribute directly to raise exception
        with patch.object(execution_engine, 'crew_wrapper') as mock_crew_wrapper:
            mock_crew_wrapper.create_crew_with_manager_tasks.side_effect = Exception("Task generation failed")
            
            # Execute
            result = execution_engine.execute_crew_with_manager_tasks(agents, text_input)
            
            # Verify failure handling
            assert result["status"] == ExecutionStatus.FAILED
            assert result["manager_agent_used"] is True
            assert result["text_input"] == text_input
            assert "Task generation failed" in result["error"]
            assert "traceback" in result

    def test_validate_crew_config_with_manager_agent(self, execution_engine):
        """Test crew configuration validation with manager agent."""
        crew_config = {
            "agents": [
                {
                    "role": "Project Manager",
                    "goal": "Coordinate team tasks",
                    "backstory": "Experienced manager",
                    "manager_type": "hierarchical",
                    "can_generate_tasks": True,
                    "allow_delegation": True
                },
                {
                    "role": "Developer",
                    "goal": "Write code",
                    "backstory": "Skilled developer"
                }
            ],
            "goal": "Build a web application"
        }
        
        result = execution_engine.validate_crew_config(crew_config)
        
        assert result["valid"] is True
        assert result["manager_agent_detected"] is True
        assert result["can_generate_tasks"] is True
        assert len(result["errors"]) == 0

    def test_validate_crew_config_multiple_manager_agents_error(self, execution_engine):
        """Test validation error for multiple manager agents."""
        crew_config = {
            "agents": [
                {
                    "role": "Manager 1",
                    "goal": "Manage team",
                    "backstory": "Manager",
                    "manager_type": "hierarchical",
                    "allow_delegation": True
                },
                {
                    "role": "Manager 2",
                    "goal": "Manage team",
                    "backstory": "Manager",
                    "manager_type": "collaborative",
                    "allow_delegation": True
                }
            ]
        }
        
        result = execution_engine.validate_crew_config(crew_config)
        
        assert result["valid"] is False
        assert "Crew can only have one manager agent" in result["errors"]

    def test_validate_crew_config_no_tasks_with_manager_agent(self, execution_engine):
        """Test validation when no tasks provided but manager agent can generate them."""
        crew_config = {
            "agents": [
                {
                    "role": "Project Manager",
                    "goal": "Coordinate team",
                    "backstory": "Manager",
                    "can_generate_tasks": True
                }
            ],
            "goal": "Build something"
        }
        
        result = execution_engine.validate_crew_config(crew_config)
        
        assert result["valid"] is True
        assert result["can_generate_tasks"] is True
        assert len(result["errors"]) == 0

    def test_validate_crew_config_no_tasks_no_manager_error(self, execution_engine):
        """Test validation error when no tasks and no manager agent."""
        crew_config = {
            "agents": [
                {
                    "role": "Developer",
                    "goal": "Write code",
                    "backstory": "Developer"
                }
            ]
        }
        
        result = execution_engine.validate_crew_config(crew_config)
        
        assert result["valid"] is False
        assert "Crew must have at least one task or a manager agent that can generate tasks" in result["errors"]

    def test_validate_crew_config_invalid_manager_type(self, execution_engine):
        """Test validation error for invalid manager type."""
        crew_config = {
            "agents": [
                {
                    "role": "Manager",
                    "goal": "Manage",
                    "backstory": "Manager",
                    "manager_type": "invalid_type"
                }
            ],
            "tasks": [
                {
                    "description": "Test task",
                    "expected_output": "Test output",
                    "agent": "Manager"
                }
            ]
        }
        
        result = execution_engine.validate_crew_config(crew_config)
        
        assert result["valid"] is False
        assert any("has invalid manager_type: invalid_type" in error for error in result["errors"])

    def test_validate_crew_config_sequential_process_warning(self, execution_engine):
        """Test warning for sequential process with manager agent."""
        crew_config = {
            "agents": [
                {
                    "role": "Manager",
                    "goal": "Manage",
                    "backstory": "Manager",
                    "manager_type": "hierarchical"
                }
            ],
            "process": "sequential",
            "tasks": [
                {
                    "description": "Test task",
                    "expected_output": "Test output",
                    "agent": "Manager"
                }
            ]
        }
        
        result = execution_engine.validate_crew_config(crew_config)
        
        assert result["valid"] is True
        assert any("consider using hierarchical process" in warning for warning in result["warnings"])

    def test_create_execution_record_with_manager_agent(self, execution_engine):
        """Test creating execution record with manager agent metadata."""
        crew_config = {
            "agents": [
                {
                    "role": "Project Manager",
                    "goal": "Coordinate team",
                    "backstory": "Manager",
                    "manager_type": "hierarchical",
                    "can_generate_tasks": True,
                    "allow_delegation": True
                },
                {
                    "role": "Developer",
                    "goal": "Code",
                    "backstory": "Developer"
                }
            ],
            "tasks": []
        }
        
        execution_result = {
            "execution_id": "test-123",
            "status": ExecutionStatus.COMPLETED,
            "result": "Success",
            "start_time": "2025-01-09T10:00:00",
            "end_time": "2025-01-09T10:05:00",
            "execution_time": 300,
            "manager_agent_used": True,
            "text_input": "Build a web app",
            "generated_tasks_count": 3
        }
        
        record = execution_engine.create_execution_record(crew_config, execution_result)
        
        assert record["id"] == "test-123"
        assert record["status"] == ExecutionStatus.COMPLETED
        assert record["metadata"]["manager_agent_used"] is True
        assert record["metadata"]["manager_agent_info"]["role"] == "Project Manager"
        assert record["metadata"]["manager_agent_info"]["manager_type"] == "hierarchical"
        assert record["metadata"]["text_input"] == "Build a web app"
        assert record["metadata"]["generated_tasks_count"] == 3

    def test_create_execution_record_without_manager_agent(self, execution_engine):
        """Test creating execution record without manager agent."""
        crew_config = {
            "agents": [
                {
                    "role": "Developer",
                    "goal": "Code",
                    "backstory": "Developer"
                }
            ],
            "tasks": [
                {
                    "description": "Write code",
                    "expected_output": "Code",
                    "agent": "Developer"
                }
            ]
        }
        
        execution_result = {
            "execution_id": "test-456",
            "status": ExecutionStatus.COMPLETED,
            "result": "Success",
            "start_time": "2025-01-09T10:00:00",
            "end_time": "2025-01-09T10:05:00",
            "execution_time": 300
        }
        
        record = execution_engine.create_execution_record(crew_config, execution_result)
        
        assert record["metadata"]["manager_agent_used"] is False
        assert record["metadata"]["manager_agent_info"] is None
        assert record["metadata"]["text_input"] is None
        assert record["metadata"]["generated_tasks_count"] is None 