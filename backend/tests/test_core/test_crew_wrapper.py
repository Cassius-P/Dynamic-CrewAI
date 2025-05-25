"""Tests for the CrewWrapper class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from crewai import Crew, Task
from app.core.crew_wrapper import CrewWrapper
from app.models.crew import Crew as CrewModel
from app.models.agent import Agent as AgentModel


class TestCrewWrapper:
    """Test cases for the CrewWrapper class."""

    def test_init(self):
        """Test CrewWrapper initialization."""
        wrapper = CrewWrapper()
        assert wrapper is not None
        assert hasattr(wrapper, 'agent_wrapper')

    @patch('app.core.crew_wrapper.AgentWrapper')
    def test_init_with_agent_wrapper(self, mock_agent_wrapper):
        """Test CrewWrapper initialization with agent wrapper."""
        mock_wrapper_instance = Mock()
        mock_agent_wrapper.return_value = mock_wrapper_instance
        
        wrapper = CrewWrapper()
        assert wrapper.agent_wrapper == mock_wrapper_instance

    @patch('app.core.crew_wrapper.Crew')
    @patch('app.core.crew_wrapper.Task')
    @patch('app.core.crew_wrapper.AgentWrapper')
    def test_create_crew_from_model(self, mock_agent_wrapper, mock_task_class, mock_crew_class):
        """Test creating crew from database model."""
        # Setup mocks
        mock_agent_wrapper_instance = Mock()
        mock_agent_wrapper.return_value = mock_agent_wrapper_instance
        
        mock_agent1 = Mock()
        mock_agent2 = Mock()
        mock_agent_wrapper_instance.create_agent_from_model.side_effect = [mock_agent1, mock_agent2]
        
        mock_task1 = Mock()
        mock_task2 = Mock()
        mock_task_class.side_effect = [mock_task1, mock_task2]
        
        mock_crew_instance = Mock()
        mock_crew_class.return_value = mock_crew_instance
        
        # Create mock model
        mock_agent_model1 = Mock(spec=AgentModel)
        mock_agent_model1.name = "Agent 1"
        mock_agent_model2 = Mock(spec=AgentModel)
        mock_agent_model2.name = "Agent 2"
        
        mock_model = Mock(spec=CrewModel)
        mock_model.name = "Test Crew"
        mock_model.process = "sequential"
        mock_model.verbose = True
        mock_model.memory = False
        mock_model.cache = True
        mock_model.max_rpm = 100
        mock_model.share_crew = False
        mock_model.step_callback = None
        mock_model.task_callback = None
        mock_model.agents = [mock_agent_model1, mock_agent_model2]
        mock_model.tasks = [
            {
                "description": "Task 1 description",
                "expected_output": "Task 1 output",
                "agent": "Agent 1"
            },
            {
                "description": "Task 2 description", 
                "expected_output": "Task 2 output",
                "agent": "Agent 2"
            }
        ]
        
        wrapper = CrewWrapper()
        crew = wrapper.create_crew_from_model(mock_model)
        
        # Verify crew creation
        assert crew == mock_crew_instance
        mock_crew_class.assert_called_once()
        
        # Verify agents were created
        assert mock_agent_wrapper_instance.create_agent_from_model.call_count == 2
        
        # Verify tasks were created
        assert mock_task_class.call_count == 2

    @patch('app.core.crew_wrapper.Crew')
    @patch('app.core.crew_wrapper.Task')  
    def test_create_crew_from_dict(self, mock_task_class, mock_crew_class):
        """Test creating crew from dictionary configuration."""
        mock_task1 = Mock()
        mock_task2 = Mock()
        mock_task_class.side_effect = [mock_task1, mock_task2]
        
        mock_crew_instance = Mock()
        mock_crew_class.return_value = mock_crew_instance
        
        config = {
            "name": "Test Crew",
            "process": "sequential",
            "agents": [
                {
                    "name": "Agent 1",
                    "role": "Developer",
                    "goal": "Write code",
                    "backstory": "Experienced developer"
                },
                {
                    "name": "Agent 2", 
                    "role": "Tester",
                    "goal": "Test code",
                    "backstory": "QA specialist"
                }
            ],
            "tasks": [
                {
                    "description": "Write Python code",
                    "expected_output": "Python script",
                    "agent": "Agent 1"
                },
                {
                    "description": "Test the code",
                    "expected_output": "Test results", 
                    "agent": "Agent 2"
                }
            ],
            "verbose": True
        }
        
        wrapper = CrewWrapper()
        crew = wrapper.create_crew_from_dict(config)
        
        assert crew == mock_crew_instance
        mock_crew_class.assert_called_once()
        assert mock_task_class.call_count == 2

    def test_create_crew_from_dict_missing_required(self):
        """Test creating crew from dict with missing required fields."""
        config = {
            "name": "Test Crew",
            # Missing agents and tasks
        }
        
        wrapper = CrewWrapper()
        
        with pytest.raises(ValueError, match="Missing required fields"):
            wrapper.create_crew_from_dict(config)

    def test_validate_crew_config_valid(self):
        """Test validation of valid crew configuration."""
        config = {
            "name": "Test Crew",
            "agents": [
                {
                    "name": "Agent 1",
                    "role": "Developer", 
                    "goal": "Write code",
                    "backstory": "Developer"
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
        
        wrapper = CrewWrapper()
        
        # Should not raise any exception
        wrapper._validate_crew_config(config)

    def test_validate_crew_config_missing_name(self):
        """Test validation with missing name."""
        config = {
            "agents": [],
            "tasks": []
        }
        
        wrapper = CrewWrapper()
        
        with pytest.raises(ValueError, match="Missing required fields"):
            wrapper._validate_crew_config(config)

    def test_validate_crew_config_missing_agents(self):
        """Test validation with missing agents."""
        config = {
            "name": "Test Crew",
            "tasks": []
        }
        
        wrapper = CrewWrapper()
        
        with pytest.raises(ValueError, match="Missing required fields"):
            wrapper._validate_crew_config(config)

    def test_validate_crew_config_missing_tasks(self):
        """Test validation with missing tasks."""
        config = {
            "name": "Test Crew",
            "agents": []
        }
        
        wrapper = CrewWrapper()
        
        with pytest.raises(ValueError, match="Missing required fields"):
            wrapper._validate_crew_config(config)

    def test_validate_crew_config_empty_values(self):
        """Test validation with empty values."""
        config = {
            "name": "",
            "agents": [],
            "tasks": []
        }
        
        wrapper = CrewWrapper()
        
        with pytest.raises(ValueError, match="cannot be empty"):
            wrapper._validate_crew_config(config)

    def test_validate_crew_config_empty_agents(self):
        """Test validation with empty agents list."""
        config = {
            "name": "Test Crew",
            "agents": [],
            "tasks": [{"description": "task", "expected_output": "output", "agent": "agent1"}]
        }
        
        wrapper = CrewWrapper()
        
        with pytest.raises(ValueError, match="Agents list cannot be empty"):
            wrapper._validate_crew_config(config)

    def test_validate_crew_config_empty_tasks(self):
        """Test validation with empty tasks list."""
        config = {
            "name": "Test Crew",
            "agents": [{"name": "Agent1", "role": "role", "goal": "goal", "backstory": "story"}],
            "tasks": []
        }
        
        wrapper = CrewWrapper()
        
        with pytest.raises(ValueError, match="Tasks list cannot be empty"):
            wrapper._validate_crew_config(config)

    @patch('app.core.crew_wrapper.AgentWrapper')
    def test_create_agents_from_configs(self, mock_agent_wrapper):
        """Test creating agents from configuration list."""
        mock_wrapper_instance = Mock()
        mock_agent_wrapper.return_value = mock_wrapper_instance
        
        mock_agent1 = Mock()
        mock_agent1.role = "Developer"
        mock_agent2 = Mock()  
        mock_agent2.role = "Tester"
        mock_wrapper_instance.create_agent_from_dict.side_effect = [mock_agent1, mock_agent2]
        
        agent_configs = [
            {
                "name": "Agent 1",
                "role": "Developer",
                "goal": "Write code",
                "backstory": "Developer"
            },
            {
                "name": "Agent 2",
                "role": "Tester", 
                "goal": "Test code",
                "backstory": "Tester"
            }
        ]
        
        wrapper = CrewWrapper()
        agents, agent_map = wrapper._create_agents_from_configs(agent_configs)
        
        assert len(agents) == 2
        assert mock_agent1 in agents
        assert mock_agent2 in agents
        assert agent_map["Agent 1"] == mock_agent1
        assert agent_map["Agent 2"] == mock_agent2
        assert mock_wrapper_instance.create_agent_from_dict.call_count == 2

    @patch('app.core.crew_wrapper.Task')
    def test_create_tasks_from_configs(self, mock_task_class):
        """Test creating tasks from configuration list."""
        mock_task1 = Mock()
        mock_task2 = Mock()
        mock_task_class.side_effect = [mock_task1, mock_task2]
        
        # Create mock agents
        mock_agent1 = Mock()
        mock_agent2 = Mock()
        agent_map = {
            "Agent 1": mock_agent1,
            "Agent 2": mock_agent2
        }
        
        task_configs = [
            {
                "description": "Write code",
                "expected_output": "Python script",
                "agent": "Agent 1"
            },
            {
                "description": "Test code",
                "expected_output": "Test results",
                "agent": "Agent 2"
            }
        ]
        
        wrapper = CrewWrapper()
        tasks = wrapper._create_tasks_from_configs(task_configs, agent_map)
        
        assert len(tasks) == 2
        assert mock_task1 in tasks
        assert mock_task2 in tasks
        assert mock_task_class.call_count == 2

    @patch('app.core.crew_wrapper.Task')
    def test_create_tasks_invalid_agent_reference(self, mock_task_class):
        """Test creating tasks with invalid agent reference."""
        agent_map = {
            "Agent 1": Mock()
        }
        
        task_configs = [
            {
                "description": "Write code",
                "expected_output": "Code",
                "agent": "NonexistentAgent"
            }
        ]
        
        wrapper = CrewWrapper()
        
        with pytest.raises(ValueError, match="Agent 'NonexistentAgent' not found"):
            wrapper._create_tasks_from_configs(task_configs, agent_map)

    def test_validate_task_config_valid(self):
        """Test validation of valid task configuration."""
        task_config = {
            "description": "Write Python code",
            "expected_output": "A Python script",
            "agent": "Developer"
        }
        
        wrapper = CrewWrapper()
        
        # Should not raise any exception
        wrapper._validate_task_config(task_config)

    def test_validate_task_config_missing_description(self):
        """Test validation with missing description."""
        task_config = {
            "expected_output": "Output",
            "agent": "Agent"
        }
        
        wrapper = CrewWrapper()
        
        with pytest.raises(ValueError, match="Missing required task fields"):
            wrapper._validate_task_config(task_config)

    def test_validate_task_config_missing_expected_output(self):
        """Test validation with missing expected_output."""
        task_config = {
            "description": "Description",
            "agent": "Agent"
        }
        
        wrapper = CrewWrapper()
        
        with pytest.raises(ValueError, match="Missing required task fields"):
            wrapper._validate_task_config(task_config)

    def test_validate_task_config_missing_agent(self):
        """Test validation with missing agent."""
        task_config = {
            "description": "Description", 
            "expected_output": "Output"
        }
        
        wrapper = CrewWrapper()
        
        with pytest.raises(ValueError, match="Missing required task fields"):
            wrapper._validate_task_config(task_config)

    def test_validate_task_config_empty_values(self):
        """Test validation with empty values."""
        task_config = {
            "description": "",
            "expected_output": "Output",
            "agent": "Agent"
        }
        
        wrapper = CrewWrapper()
        
        with pytest.raises(ValueError, match="cannot be empty"):
            wrapper._validate_task_config(task_config)

    @patch('app.core.crew_wrapper.Crew')
    def test_crew_creation_exception_handling(self, mock_crew_class):
        """Test exception handling during crew creation."""
        mock_crew_class.side_effect = Exception("Crew creation failed")
        
        config = {
            "name": "Test Crew",
            "agents": [
                {
                    "name": "Agent 1",
                    "role": "Developer",
                    "goal": "Write code", 
                    "backstory": "Developer"
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
        
        wrapper = CrewWrapper()
        
        with pytest.raises(Exception, match="Crew creation failed"):
            wrapper.create_crew_from_dict(config)

    @patch('app.core.crew_wrapper.Crew')
    @patch('app.core.crew_wrapper.Task')
    def test_create_crew_with_all_parameters(self, mock_task_class, mock_crew_class):
        """Test creating crew with all possible parameters."""
        mock_task_instance = Mock()
        mock_task_class.return_value = mock_task_instance
        
        mock_crew_instance = Mock()
        mock_crew_class.return_value = mock_crew_instance
        
        config = {
            "name": "Advanced Crew",
            "process": "hierarchical",
            "agents": [
                {
                    "name": "Manager",
                    "role": "Project Manager",
                    "goal": "Coordinate project",
                    "backstory": "Experienced PM"
                }
            ],
            "tasks": [
                {
                    "description": "Manage project",
                    "expected_output": "Project plan",
                    "agent": "Manager"
                }
            ],
            "verbose": True,
            "memory": True,
            "cache": False,
            "max_rpm": 50,
            "share_crew": True
        }
        
        wrapper = CrewWrapper()
        crew = wrapper.create_crew_from_dict(config)
        
        assert crew == mock_crew_instance
        mock_crew_class.assert_called_once()
        
        # Verify the call arguments include our parameters
        call_kwargs = mock_crew_class.call_args[1]
        assert call_kwargs['process'] == "hierarchical"
        assert call_kwargs['verbose'] is True
        assert call_kwargs['memory'] is True
        assert call_kwargs['cache'] is False
        assert call_kwargs['max_rpm'] == 50
        assert call_kwargs['share_crew'] is True

    @patch('app.core.crew_wrapper.AgentWrapper')
    def test_create_agents_from_models(self, mock_agent_wrapper):
        """Test creating agents from database models."""
        mock_wrapper_instance = Mock()
        mock_agent_wrapper.return_value = mock_wrapper_instance
        
        mock_agent1 = Mock()
        mock_agent1.role = "Developer"
        mock_agent2 = Mock()
        mock_agent2.role = "Tester"
        mock_wrapper_instance.create_agent_from_model.side_effect = [mock_agent1, mock_agent2]
        
        mock_model1 = Mock(spec=AgentModel)
        mock_model1.name = "Agent 1"
        mock_model2 = Mock(spec=AgentModel) 
        mock_model2.name = "Agent 2"
        
        agent_models = [mock_model1, mock_model2]
        
        wrapper = CrewWrapper()
        agents, agent_map = wrapper._create_agents_from_models(agent_models)
        
        assert len(agents) == 2
        assert mock_agent1 in agents
        assert mock_agent2 in agents
        assert agent_map["Agent 1"] == mock_agent1
        assert agent_map["Agent 2"] == mock_agent2
        assert mock_wrapper_instance.create_agent_from_model.call_count == 2
