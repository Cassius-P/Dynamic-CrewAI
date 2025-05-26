"""Tests for ManagerAgent wrapper class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from app.core.manager_agent_wrapper import ManagerAgentWrapper
from app.models.agent import Agent
from crewai import Agent as CrewAIAgent, Task


class TestManagerAgentWrapper:
    """Test cases for ManagerAgent wrapper class."""

    @pytest.fixture
    def manager_agent_model(self):
        """Create a manager agent model for testing."""
        return Agent(
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
    def manager_agent_wrapper(self):
        """Create a ManagerAgentWrapper instance for testing."""
        return ManagerAgentWrapper()

    def test_manager_agent_wrapper_initialization(self, manager_agent_wrapper):
        """Test ManagerAgentWrapper initialization."""
        assert manager_agent_wrapper is not None
        assert hasattr(manager_agent_wrapper, 'agent_wrapper')
        assert hasattr(manager_agent_wrapper, 'task_generator')

    def test_is_manager_agent_true(self, manager_agent_wrapper, manager_agent_model):
        """Test identification of manager agents."""
        result = manager_agent_wrapper.is_manager_agent(manager_agent_model)
        assert result is True

    def test_is_manager_agent_false(self, manager_agent_wrapper):
        """Test identification of non-manager agents."""
        regular_agent = Agent(
            role="Developer",
            goal="Write code",
            backstory="Software developer",
            allow_delegation=False,
            manager_type=None,
            can_generate_tasks=False
        )
        
        result = manager_agent_wrapper.is_manager_agent(regular_agent)
        assert result is False

    @patch('app.core.manager_agent_wrapper.AgentWrapper')
    def test_create_manager_agent_from_model(self, mock_agent_wrapper, manager_agent_wrapper, manager_agent_model):
        """Test creating CrewAI manager agent from model."""
        # Mock the base agent creation
        mock_crewai_agent = Mock(spec=CrewAIAgent)
        mock_agent_wrapper.return_value.create_agent_from_model.return_value = mock_crewai_agent
        
        result = manager_agent_wrapper.create_manager_agent_from_model(manager_agent_model)
        
        assert result == mock_crewai_agent
        mock_agent_wrapper.return_value.create_agent_from_model.assert_called_once_with(
            manager_agent_model, None
        )

    def test_create_manager_agent_from_model_invalid(self, manager_agent_wrapper):
        """Test creating manager agent from non-manager model raises error."""
        regular_agent = Agent(
            role="Developer",
            goal="Write code", 
            backstory="Software developer",
            manager_type=None
        )
        
        with pytest.raises(ValueError, match="Agent is not a manager agent"):
            manager_agent_wrapper.create_manager_agent_from_model(regular_agent)

    @patch('app.core.manager_agent_wrapper.TaskGenerator')
    def test_generate_tasks_from_text(self, mock_task_generator, manager_agent_wrapper, manager_agent_model):
        """Test generating tasks from text input."""
        # Mock task generator
        mock_generator = Mock()
        mock_task_generator.return_value = mock_generator
        
        # Mock generated tasks
        mock_tasks = [
            Mock(spec=Task, description="Task 1"),
            Mock(spec=Task, description="Task 2")
        ]
        mock_generator.generate_tasks.return_value = mock_tasks
        
        text_input = "Create a web application with user authentication"
        result = manager_agent_wrapper.generate_tasks_from_text(
            manager_agent_model, text_input
        )
        
        assert result == mock_tasks
        assert len(result) == 2
        mock_generator.generate_tasks.assert_called_once_with(text_input, manager_agent_model)

    def test_generate_tasks_from_text_non_manager(self, manager_agent_wrapper):
        """Test generating tasks from non-manager agent raises error."""
        regular_agent = Agent(
            role="Developer",
            goal="Write code",
            backstory="Software developer",
            can_generate_tasks=False
        )
        
        with pytest.raises(ValueError, match="Agent cannot generate tasks"):
            manager_agent_wrapper.generate_tasks_from_text(regular_agent, "Some task")

    def test_get_manager_config(self, manager_agent_wrapper, manager_agent_model):
        """Test getting manager configuration."""
        config = manager_agent_wrapper.get_manager_config(manager_agent_model)
        
        assert config == manager_agent_model.manager_config
        assert config["task_generation_llm"] == "gpt-4"
        assert config["max_tasks_per_request"] == 5

    def test_get_manager_config_default(self, manager_agent_wrapper):
        """Test getting default manager configuration."""
        agent_without_config = Agent(
            role="Manager",
            goal="Manage",
            backstory="Manager",
            manager_type="hierarchical",
            manager_config=None
        )
        
        config = manager_agent_wrapper.get_manager_config(agent_without_config)
        
        # Should return default config
        assert isinstance(config, dict)
        assert "task_generation_llm" in config
        assert "max_tasks_per_request" in config

    def test_validate_manager_agent_valid(self, manager_agent_wrapper, manager_agent_model):
        """Test validation of valid manager agent."""
        result = manager_agent_wrapper.validate_manager_agent(manager_agent_model)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_manager_agent_invalid(self, manager_agent_wrapper):
        """Test validation of invalid manager agent."""
        invalid_agent = Agent(
            role="Manager",
            goal="Manage",
            backstory="Manager",
            manager_type="invalid_type",  # Invalid type
            allow_delegation=False,  # Should be True for managers
            can_generate_tasks=True
        )
        
        result = manager_agent_wrapper.validate_manager_agent(invalid_agent)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    @patch('app.core.manager_agent_wrapper.TaskGenerator')
    def test_assign_tasks_to_agents(self, mock_task_generator, manager_agent_wrapper, manager_agent_model):
        """Test assigning generated tasks to available agents."""
        # Mock tasks
        tasks = [
            {"description": "Task 1", "agent": None},
            {"description": "Task 2", "agent": None}
        ]
        
        # Mock available agents
        available_agents = [
            Mock(spec=CrewAIAgent, role="Developer"),
            Mock(spec=CrewAIAgent, role="Designer")
        ]
        
        result = manager_agent_wrapper.assign_tasks_to_agents(
            manager_agent_model, tasks, available_agents
        )
        
        assert len(result) == 2
        # Tasks should be assigned to agents
        for task in result:
            assert task["agent"] is not None

    def test_get_delegation_strategy(self, manager_agent_wrapper, manager_agent_model):
        """Test getting delegation strategy from manager config."""
        strategy = manager_agent_wrapper.get_delegation_strategy(manager_agent_model)
        
        assert strategy == "round_robin"

    def test_get_delegation_strategy_default(self, manager_agent_wrapper):
        """Test getting default delegation strategy."""
        agent_without_strategy = Agent(
            role="Manager",
            goal="Manage",
            backstory="Manager",
            manager_type="hierarchical",
            manager_config={}
        )
        
        strategy = manager_agent_wrapper.get_delegation_strategy(agent_without_strategy)
        
        assert strategy == "sequential"  # Default strategy

    def test_create_manager_agent_with_tools(self, manager_agent_wrapper, manager_agent_model):
        """Test creating manager agent with specialized tools."""
        manager_agent_model.tools = [
            "task_generator",
            "agent_coordinator", 
            "progress_tracker"
        ]
        
        with patch('app.core.manager_agent_wrapper.AgentWrapper') as mock_agent_wrapper:
            mock_crewai_agent = Mock(spec=CrewAIAgent)
            mock_agent_wrapper.return_value.create_agent_from_model.return_value = mock_crewai_agent
            
            result = manager_agent_wrapper.create_manager_agent_from_model(manager_agent_model)
            
            assert result == mock_crewai_agent
            # Verify tools were included
            mock_agent_wrapper.return_value.create_agent_from_model.assert_called_once()

    def test_manager_agent_hierarchy_support(self, manager_agent_wrapper, manager_agent_model):
        """Test hierarchical manager agent support."""
        manager_agent_model.manager_type = "hierarchical"
        manager_agent_model.manager_config = {
            "subordinate_agent_ids": [2, 3, 4],
            "max_delegation_depth": 2
        }
        
        config = manager_agent_wrapper.get_manager_config(manager_agent_model)
        
        assert config["subordinate_agent_ids"] == [2, 3, 4]
        assert config["max_delegation_depth"] == 2

    def test_manager_agent_collaborative_support(self, manager_agent_wrapper):
        """Test collaborative manager agent support."""
        collaborative_agent = Agent(
            role="Team Coordinator",
            goal="Facilitate team collaboration",
            backstory="Collaborative team leader",
            manager_type="collaborative",
            allow_delegation=True,
            can_generate_tasks=True,
            manager_config={
                "collaboration_style": "consensus",
                "decision_threshold": 0.7
            }
        )
        
        assert manager_agent_wrapper.is_manager_agent(collaborative_agent) is True
        config = manager_agent_wrapper.get_manager_config(collaborative_agent)
        assert config["collaboration_style"] == "consensus" 