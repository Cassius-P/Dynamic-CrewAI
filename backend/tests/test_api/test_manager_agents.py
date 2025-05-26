"""Tests for Manager Agent API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
import json

from app.main import app
from app.models.agent import Agent
from app.models.execution import Execution, ExecutionStatus


class TestManagerAgentAPI:
    """Test cases for Manager Agent API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def mock_manager_service(self):
        """Mock manager agent service."""
        return Mock()

    @pytest.fixture
    def sample_manager_agent(self):
        """Sample manager agent for testing."""
        from datetime import datetime
        return Agent(
            id=1,
            role="Project Manager",
            goal="Coordinate team tasks and ensure project success",
            backstory="Experienced project manager with team coordination skills",
            verbose=False,
            allow_delegation=True,
            manager_type="hierarchical",
            can_generate_tasks=True,
            manager_config={
                "task_generation_llm": "gpt-4",
                "max_tasks_per_request": 5,
                "delegation_strategy": "round_robin"
            },
            created_at=datetime.utcnow(),
            crew_id=None
        )

    @pytest.fixture
    def sample_regular_agent(self):
        """Sample regular agent for testing."""
        from datetime import datetime
        return Agent(
            id=2,
            role="Software Developer",
            goal="Write high-quality code",
            backstory="Experienced software developer",
            verbose=False,
            allow_delegation=False,
            manager_type=None,
            can_generate_tasks=False,
            created_at=datetime.utcnow(),
            crew_id=None
        )

    def test_create_manager_agent_success(self, client, sample_manager_agent):
        """Test successful manager agent creation."""
        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.create_manager_agent.return_value = sample_manager_agent

            response = client.post("/api/v1/manager-agents/", json={
                "role": "Project Manager",
                "goal": "Coordinate team tasks",
                "backstory": "Experienced manager",
                "manager_type": "hierarchical",
                "can_generate_tasks": True,
                "allow_delegation": True
            })

            assert response.status_code == 201
            data = response.json()
            assert data["role"] == "Project Manager"
            assert data["manager_type"] == "hierarchical"
            assert data["can_generate_tasks"] is True

    def test_create_manager_agent_validation_error(self, client):
        """Test manager agent creation with validation error."""
        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.create_manager_agent.side_effect = ValueError("Invalid configuration")

            response = client.post("/api/v1/manager-agents/", json={
                "role": "",  # Invalid empty role
                "goal": "Coordinate team tasks",
                "backstory": "Experienced manager"
            })

            assert response.status_code == 400
            assert "Invalid configuration" in response.json()["detail"]

    def test_list_manager_agents(self, client, sample_manager_agent):
        """Test listing manager agents."""
        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_manager_agents.return_value = [sample_manager_agent]

            response = client.get("/api/v1/manager-agents/")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["role"] == "Project Manager"

    def test_list_manager_agents_with_pagination(self, client, sample_manager_agent):
        """Test listing manager agents with pagination."""
        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_manager_agents.return_value = [sample_manager_agent]

            response = client.get("/api/v1/manager-agents/?skip=10&limit=5")

            assert response.status_code == 200
            mock_service_instance.get_manager_agents.assert_called_once_with(10, 5)

    def test_get_manager_agent_by_id(self, client, sample_manager_agent):
        """Test getting a specific manager agent by ID."""
        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_manager_agent_by_id.return_value = sample_manager_agent

            response = client.get("/api/v1/manager-agents/1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["role"] == "Project Manager"

    def test_get_manager_agent_not_found(self, client):
        """Test getting a non-existent manager agent."""
        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_manager_agent_by_id.return_value = None

            response = client.get("/api/v1/manager-agents/999")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"]

    def test_update_manager_agent(self, client, sample_manager_agent):
        """Test updating a manager agent."""
        updated_agent = sample_manager_agent
        updated_agent.role = "Senior Project Manager"

        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.update_manager_agent.return_value = updated_agent

            response = client.put("/api/v1/manager-agents/1", json={
                "role": "Senior Project Manager"
            })

            assert response.status_code == 200
            data = response.json()
            assert data["role"] == "Senior Project Manager"

    def test_update_manager_agent_validation_error(self, client):
        """Test updating manager agent with validation error."""
        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.update_manager_agent.side_effect = ValueError("Invalid update")

            response = client.put("/api/v1/manager-agents/1", json={
                "manager_type": "invalid_type"
            })

            assert response.status_code == 400
            assert "Invalid update" in response.json()["detail"]

    def test_delete_manager_agent(self, client):
        """Test deleting a manager agent."""
        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.delete_manager_agent.return_value = True

            response = client.delete("/api/v1/manager-agents/1")

            assert response.status_code == 204

    def test_delete_manager_agent_not_found(self, client):
        """Test deleting a non-existent manager agent."""
        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.delete_manager_agent.side_effect = ValueError("Manager agent 999 not found")

            response = client.delete("/api/v1/manager-agents/999")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"]

    def test_generate_tasks(self, client):
        """Test task generation endpoint."""
        generated_tasks = [
            {
                "description": "Design user interface",
                "expected_output": "UI mockups and wireframes",
                "generated_at": "2025-01-09T10:00:00",
                "source_text": "Create a web application"
            },
            {
                "description": "Implement backend API",
                "expected_output": "REST API endpoints",
                "generated_at": "2025-01-09T10:00:00",
                "source_text": "Create a web application"
            }
        ]

        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.generate_tasks_from_text.return_value = generated_tasks

            response = client.post("/api/v1/manager-agents/1/generate-tasks", json={
                "text_input": "Create a web application",
                "max_tasks": 2
            })

            assert response.status_code == 200
            data = response.json()
            assert data["agent_id"] == 1
            assert data["text_input"] == "Create a web application"
            assert len(data["tasks"]) == 2
            assert data["tasks"][0]["description"] == "Design user interface"

    def test_generate_tasks_agent_cannot_generate(self, client):
        """Test task generation with agent that cannot generate tasks."""
        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.generate_tasks_from_text.side_effect = ValueError("Manager agent 1 cannot generate tasks")

            response = client.post("/api/v1/manager-agents/1/generate-tasks", json={
                "text_input": "Create a web application"
            })

            assert response.status_code == 400
            assert "cannot generate tasks" in response.json()["detail"]

    def test_execute_crew_with_manager(self, client):
        """Test crew execution with manager agent."""
        execution_result = {
            "execution_id": "test-123",
            "status": ExecutionStatus.COMPLETED,
            "result": "Execution completed successfully",
            "start_time": "2025-01-09T10:00:00",
            "end_time": "2025-01-09T10:05:00",
            "execution_time": 300,
            "manager_agent_used": True,
            "text_input": "Build a web app",
            "generated_tasks_count": 3
        }

        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.execute_crew_with_manager_tasks.return_value = execution_result

            response = client.post("/api/v1/manager-agents/execute-crew", json={
                "agent_ids": [1, 2, 3],
                "text_input": "Build a web app",
                "crew_config": {"verbose": True}
            })

            assert response.status_code == 200
            data = response.json()
            assert data["execution_id"] == "test-123"
            assert data["status"] == ExecutionStatus.COMPLETED.value
            assert data["manager_agent_used"] is True

    def test_execute_crew_no_manager_agent(self, client):
        """Test crew execution without manager agent."""
        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.execute_crew_with_manager_tasks.side_effect = ValueError("No manager agent found in the provided agents")

            response = client.post("/api/v1/manager-agents/execute-crew", json={
                "agent_ids": [2, 3],  # No manager agent
                "text_input": "Build a web app"
            })

            assert response.status_code == 400
            assert "No manager agent found" in response.json()["detail"]

    def test_get_manager_agent_capabilities(self, client):
        """Test getting manager agent capabilities."""
        capabilities = {
            "agent_id": 1,
            "role": "Project Manager",
            "manager_type": "hierarchical",
            "can_generate_tasks": True,
            "allow_delegation": True,
            "manager_config": {"delegation_strategy": "round_robin"},
            "delegation_strategies": ["round_robin", "random", "sequential"],
            "supported_manager_types": ["hierarchical", "collaborative", "sequential"],
            "capabilities": {
                "task_generation": True,
                "delegation": True,
                "hierarchical_management": True,
                "collaborative_management": False,
                "sequential_management": False
            }
        }

        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_manager_agent_capabilities.return_value = capabilities

            response = client.get("/api/v1/manager-agents/1/capabilities")

            assert response.status_code == 200
            data = response.json()
            assert data["agent_id"] == 1
            assert data["can_generate_tasks"] is True
            assert data["capabilities"]["task_generation"] is True

    def test_get_manager_agent_executions(self, client):
        """Test getting manager agent execution history."""
        # Create mock execution objects with proper attributes
        from datetime import datetime
        mock_execution = Mock()
        mock_execution.id = "exec-1"
        mock_execution.status = ExecutionStatus.COMPLETED
        mock_execution.outputs = "Success"
        mock_execution.started_at = datetime.fromisoformat("2025-01-09T10:00:00")
        mock_execution.completed_at = datetime.fromisoformat("2025-01-09T10:05:00")
        mock_execution.execution_time = 300
        mock_execution.error_message = None
        # Mock the metadata attribute access
        mock_execution.metadata = {"manager_agent_id": 1}
        
        mock_executions = [mock_execution]

        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_manager_agent_executions.return_value = mock_executions

            response = client.get("/api/v1/manager-agents/1/executions")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["execution_id"] == "exec-1"
            assert data[0]["status"] == ExecutionStatus.COMPLETED.value

    def test_get_manager_agent_statistics(self, client):
        """Test getting manager agent statistics."""
        statistics = {
            "agent_id": 1,
            "total_executions": 10,
            "successful_executions": 8,
            "failed_executions": 2,
            "success_rate": 80.0,
            "manager_type": "hierarchical",
            "can_generate_tasks": True,
            "created_at": "2025-01-09T09:00:00"
        }

        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_manager_agent_statistics.return_value = statistics

            response = client.get("/api/v1/manager-agents/1/statistics")

            assert response.status_code == 200
            data = response.json()
            assert data["agent_id"] == 1
            assert data["total_executions"] == 10
            assert data["success_rate"] == 80.0

    def test_validate_manager_agent_config(self, client, sample_manager_agent):
        """Test validating manager agent configuration."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": ["Manager agents that can generate tasks should typically allow delegation"]
        }

        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_manager_agent_by_id.return_value = sample_manager_agent
            mock_service_instance.validate_manager_agent_config.return_value = validation_result

            response = client.post("/api/v1/manager-agents/1/validate", json={
                "manager_type": "collaborative",
                "can_generate_tasks": True
            })

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert len(data["warnings"]) == 1

    def test_validate_manager_agent_config_invalid(self, client, sample_manager_agent):
        """Test validating invalid manager agent configuration."""
        validation_result = {
            "valid": False,
            "errors": ["Invalid manager_type: invalid_type"],
            "warnings": []
        }

        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_manager_agent_by_id.return_value = sample_manager_agent
            mock_service_instance.validate_manager_agent_config.return_value = validation_result

            response = client.post("/api/v1/manager-agents/1/validate", json={
                "manager_type": "invalid_type"
            })

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert "Invalid manager_type" in data["errors"][0]

    def test_endpoints_error_handling(self, client):
        """Test error handling for all endpoints."""
        with patch('app.api.v1.manager_agents.get_manager_agent_service') as mock_service:
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_manager_agents.side_effect = Exception("Database error")

            response = client.get("/api/v1/manager-agents/")

            assert response.status_code == 500
            assert "Failed to retrieve manager agents" in response.json()["detail"] 