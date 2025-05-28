"""Tests for enhanced CrewWrapper with manager agent integration."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from app.core.crew_wrapper import CrewWrapper
from app.models.crew import Crew as CrewModel
from app.models.agent import Agent as AgentModel
from crewai import Crew, Agent as CrewAIAgent, Task


class TestEnhancedCrewWrapper:
    """Test cases for enhanced CrewWrapper with manager agent support."""

    @pytest.fixture
    def crew_wrapper(self):
        """Create a CrewWrapper instance for testing."""
        return CrewWrapper()

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

    @pytest.fixture
    def crew_model_with_manager(self, manager_agent_model, regular_agent_model):
        """Create a crew model with manager agent for testing."""
        crew = Mock(spec=CrewModel)
        crew.agents = [manager_agent_model, regular_agent_model]
        crew.goal = "Create a web application with user authentication and dashboard"
        crew.tasks = None
        crew.verbose = True
        crew.process = None
        crew.max_rpm = None
        crew.config = None
        return crew

    def test_crew_wrapper_initialization_with_manager_wrapper(self, crew_wrapper):
        """Test CrewWrapper initialization includes manager agent wrapper."""
        assert crew_wrapper is not None
        assert hasattr(crew_wrapper, 'agent_wrapper')
        assert hasattr(crew_wrapper, 'manager_agent_wrapper')

    @patch('app.core.crew_wrapper.Crew')
    def test_create_crew_from_model_with_manager_agent(self, mock_crew, crew_wrapper, crew_model_with_manager):
        """Test creating crew from model with manager agent."""
        # Mock the crew creation
        mock_crew_instance = Mock(spec=Crew)
        mock_crew.return_value = mock_crew_instance
        
        # Mock manager agent creation - return True for first agent, False for second
        with patch('app.core.crew_wrapper.Task') as mock_task:
            with patch.object(crew_wrapper.manager_agent_wrapper, 'is_manager_agent', side_effect=[True, False]):
                with patch.object(crew_wrapper.manager_agent_wrapper, 'create_manager_agent_from_model') as mock_create_manager:
                    with patch.object(crew_wrapper.agent_wrapper, 'create_agent_from_model') as mock_create_agent:
                        mock_manager = Mock(spec=CrewAIAgent)
                        mock_manager.role = "Project Manager"
                        mock_manager.goal = "Coordinate team tasks"
                        mock_manager.backstory = "Experienced manager"
                        mock_manager.verbose = True
                        mock_manager.allow_delegation = True
                        mock_manager.max_rpm = None
                        mock_manager._rpm_controller = None
                        mock_create_manager.return_value = mock_manager
                        
                        mock_regular = Mock(spec=CrewAIAgent)
                        mock_regular.role = "Software Developer"
                        mock_regular.goal = "Write code"
                        mock_regular.backstory = "Skilled developer"
                        mock_regular.verbose = True
                        mock_regular.max_rpm = None
                        mock_regular._rpm_controller = None
                        mock_create_agent.return_value = mock_regular
                        
                        # Mock Task creation to prevent validation errors
                        mock_task_instance = Mock(spec=Task)
                        mock_task.return_value = mock_task_instance
                        
                        result = crew_wrapper.create_crew_from_model(crew_model_with_manager)
                        
                        # Verify manager agent was created
                        mock_create_manager.assert_called_once()
                        # Verify regular agent was created
                        mock_create_agent.assert_called_once()
                        # Verify crew was created
                        mock_crew.assert_called_once()
                        
                        # Check that hierarchical process was set
                        call_args = mock_crew.call_args[1]
                        assert call_args.get("process") == "hierarchical"
                        assert "manager_agent" in call_args

    def test_create_crew_from_dict_with_manager_agent(self, crew_wrapper):
        """Test creating crew from dictionary with manager agent."""
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
                    "backstory": "Skilled developer",
                    "allow_delegation": False
                }
            ],
            "goal": "Build a web application"
        }
        
        with patch('app.core.crew_wrapper.Crew') as mock_crew:
            with patch('app.core.crew_wrapper.Task') as mock_task:
                with patch.object(crew_wrapper.manager_agent_wrapper, 'create_manager_agent_from_dict') as mock_create_manager:
                    with patch.object(crew_wrapper.agent_wrapper, 'create_agent_from_dict') as mock_create_agent:
                        mock_manager = Mock(spec=CrewAIAgent)
                        mock_manager.role = "Project Manager"
                        mock_manager.goal = "Coordinate team tasks"
                        mock_manager.backstory = "Experienced manager"
                        mock_manager.verbose = True
                        mock_manager.allow_delegation = True
                        mock_create_manager.return_value = mock_manager
                        
                        mock_regular = Mock(spec=CrewAIAgent)
                        mock_regular.role = "Developer"
                        mock_regular.goal = "Write code"
                        mock_regular.backstory = "Skilled developer"
                        mock_regular.verbose = True
                        mock_create_agent.return_value = mock_regular
                        
                        # Mock Task creation to prevent validation errors
                        mock_task_instance = Mock(spec=Task)
                        mock_task.return_value = mock_task_instance
                        
                        result = crew_wrapper.create_crew_from_dict(crew_config)
                        
                        # Verify manager agent was created
                        mock_create_manager.assert_called_once()
                        # Verify regular agent was created
                        mock_create_agent.assert_called_once()
                        # Verify crew was created
                        mock_crew.assert_called_once()

    def test_create_crew_with_multiple_manager_agents_raises_error(self, crew_wrapper):
        """Test that multiple manager agents raise an error."""
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
        
        with pytest.raises(ValueError, match="Crew can only have one manager agent"):
            crew_wrapper.create_crew_from_dict(crew_config)

    @patch('app.core.crew_wrapper.Crew')
    def test_create_crew_with_manager_tasks_method(self, mock_crew, crew_wrapper, manager_agent_model, regular_agent_model):
        """Test the create_crew_with_manager_tasks method."""
        agents = [manager_agent_model, regular_agent_model]
        text_input = "Create a web application with user authentication and dashboard"
        
        # Mock the crew creation
        mock_crew_instance = Mock(spec=Crew)
        mock_crew.return_value = mock_crew_instance
        
        with patch('app.core.crew_wrapper.Task') as mock_task:
            with patch.object(crew_wrapper.manager_agent_wrapper, 'is_manager_agent', side_effect=[True, False]):
                with patch.object(crew_wrapper.manager_agent_wrapper, 'create_manager_agent_from_model') as mock_create_manager:
                    with patch.object(crew_wrapper.agent_wrapper, 'create_agent_from_model') as mock_create_agent:
                        with patch.object(crew_wrapper.manager_agent_wrapper, 'generate_tasks_from_text') as mock_generate:
                            with patch.object(crew_wrapper.manager_agent_wrapper, 'assign_tasks_to_agents') as mock_assign:
                                # Setup mocks
                                mock_manager = Mock(spec=CrewAIAgent)
                                mock_manager.role = "Project Manager"
                                mock_manager.goal = "Coordinate team tasks"
                                mock_manager.backstory = "Experienced manager"
                                mock_manager.verbose = True
                                mock_manager.allow_delegation = True
                                mock_create_manager.return_value = mock_manager
                                
                                mock_regular = Mock(spec=CrewAIAgent)
                                mock_regular.role = "Software Developer"
                                mock_regular.goal = "Write code"
                                mock_regular.backstory = "Skilled developer"
                                mock_regular.verbose = True
                                mock_create_agent.return_value = mock_regular
                                
                                mock_task_obj = Mock(spec=Task)
                                mock_task_obj.description = "Test task"
                                mock_task_obj.expected_output = "Test output"
                                mock_generate.return_value = [mock_task_obj]
                                
                                mock_assign.return_value = [
                                    {"description": "Test task", "expected_output": "Test output", "agent": mock_regular}
                                ]
                                
                                # Mock Task constructor to prevent validation errors
                                mock_task_instance = Mock(spec=Task)
                                mock_task.return_value = mock_task_instance
                                
                                result = crew_wrapper.create_crew_with_manager_tasks(agents, text_input)
                                
                                # Verify calls were made
                                mock_create_manager.assert_called_once()
                                mock_create_agent.assert_called_once()
                                mock_generate.assert_called_once_with(manager_agent_model, text_input)
                                mock_assign.assert_called_once()
                                mock_crew.assert_called_once()
                                
                                # Check crew configuration
                                call_args = mock_crew.call_args[1]
                                assert call_args.get("process") == "hierarchical"
                                assert "manager_agent" in call_args

    def test_create_crew_with_manager_tasks_no_manager_raises_error(self, crew_wrapper, regular_agent_model):
        """Test that create_crew_with_manager_tasks raises error when no manager agent."""
        agents = [regular_agent_model]
        text_input = "Create a web application"
        
        with patch.object(crew_wrapper.manager_agent_wrapper, 'is_manager_agent', return_value=False):
            with pytest.raises(ValueError, match="No manager agent found in agent list"):
                crew_wrapper.create_crew_with_manager_tasks(agents, text_input)

    def test_create_default_tasks_helper_method(self, crew_wrapper):
        """Test the _create_default_tasks helper method."""
        # Use patch to mock Task creation instead of testing actual Task creation
        with patch('app.core.crew_wrapper.Task') as mock_task:
            mock_agents = [
                Mock(spec=CrewAIAgent, role="Developer"),
                Mock(spec=CrewAIAgent, role="Designer")
            ]
            tasks = []
            
            crew_wrapper._create_default_tasks(mock_agents, tasks)
            
            # Verify Task was called for each agent
            assert mock_task.call_count == 2
            
            # Verify the tasks were added to the list
            assert len(tasks) == 2

    def test_manager_agent_task_generation_from_crew_goal(self, crew_wrapper, crew_model_with_manager):
        """Test task generation from crew goal when no explicit tasks provided."""
        with patch('app.core.crew_wrapper.Crew') as mock_crew:
            with patch('app.core.crew_wrapper.Task') as mock_task:
                with patch.object(crew_wrapper.manager_agent_wrapper, 'is_manager_agent', side_effect=[True, False]):
                    with patch.object(crew_wrapper.manager_agent_wrapper, 'create_manager_agent_from_model') as mock_create_manager:
                        with patch.object(crew_wrapper.agent_wrapper, 'create_agent_from_model') as mock_create_agent:
                            with patch.object(crew_wrapper.manager_agent_wrapper, 'generate_tasks_from_text') as mock_generate:
                                with patch.object(crew_wrapper.manager_agent_wrapper, 'assign_tasks_to_agents') as mock_assign:
                                    # Setup mocks
                                    mock_manager = Mock(spec=CrewAIAgent)
                                    mock_manager.role = "Project Manager"
                                    mock_manager.goal = "Coordinate team tasks"
                                    mock_manager.backstory = "Experienced manager"
                                    mock_manager.verbose = True
                                    mock_manager.allow_delegation = True
                                    mock_create_manager.return_value = mock_manager
                                    
                                    mock_regular = Mock(spec=CrewAIAgent)
                                    mock_regular.role = "Software Developer"
                                    mock_regular.goal = "Write code"
                                    mock_regular.backstory = "Skilled developer"
                                    mock_regular.verbose = True
                                    mock_create_agent.return_value = mock_regular
                                    
                                    mock_task_obj = Mock(spec=Task)
                                    mock_task_obj.description = "Generated task"
                                    mock_task_obj.expected_output = "Generated output"
                                    mock_generate.return_value = [mock_task_obj]
                                    
                                    mock_assign.return_value = [
                                        {"description": "Generated task", "expected_output": "Generated output", "agent": mock_regular}
                                    ]
                                    
                                    # Mock Task constructor to prevent validation errors
                                    mock_task_instance = Mock(spec=Task)
                                    mock_task.return_value = mock_task_instance
                                    
                                    # Set source model attribute to enable task generation
                                    setattr(mock_manager, '_source_model', crew_model_with_manager.agents[0])
                                    
                                    result = crew_wrapper.create_crew_from_model(crew_model_with_manager)
                                    
                                    # Verify task generation was attempted
                                    mock_generate.assert_called_once()
                                    mock_assign.assert_called_once()

    def test_fallback_to_default_tasks_on_generation_failure(self, crew_wrapper, crew_model_with_manager):
        """Test fallback to default tasks when task generation fails."""
        with patch('app.core.crew_wrapper.Crew') as mock_crew:
            with patch.object(crew_wrapper.manager_agent_wrapper, 'is_manager_agent', side_effect=[True, False]):
                with patch.object(crew_wrapper.manager_agent_wrapper, 'create_manager_agent_from_model') as mock_create_manager:
                    with patch.object(crew_wrapper.agent_wrapper, 'create_agent_from_model') as mock_create_agent:
                        with patch.object(crew_wrapper.manager_agent_wrapper, 'generate_tasks_from_text', side_effect=Exception("Generation failed")):
                            with patch.object(crew_wrapper, '_create_default_tasks') as mock_default:
                                # Setup mocks
                                mock_manager = Mock(spec=CrewAIAgent)
                                mock_create_manager.return_value = mock_manager
                                
                                mock_regular = Mock(spec=CrewAIAgent)
                                mock_create_agent.return_value = mock_regular
                                
                                # Set source model attribute to enable task generation attempt
                                setattr(mock_manager, '_source_model', crew_model_with_manager.agents[0])
                                
                                result = crew_wrapper.create_crew_from_model(crew_model_with_manager)
                                
                                # Verify fallback was called
                                mock_default.assert_called_once()

    def test_hierarchical_process_configuration(self, crew_wrapper):
        """Test that hierarchical process is properly configured with manager agents."""
        crew_config = {
            "agents": [
                {
                    "role": "Manager",
                    "goal": "Manage team",
                    "backstory": "Manager",
                    "manager_type": "hierarchical",
                    "allow_delegation": True
                },
                {
                    "role": "Developer",
                    "goal": "Code",
                    "backstory": "Developer"
                }
            ]
        }
        
        with patch('app.core.crew_wrapper.Crew') as mock_crew:
            with patch('app.core.crew_wrapper.Task') as mock_task:
                with patch.object(crew_wrapper.manager_agent_wrapper, 'create_manager_agent_from_dict') as mock_create_manager:
                    with patch.object(crew_wrapper.agent_wrapper, 'create_agent_from_dict') as mock_create_agent:
                        # Setup mock agents with all required attributes
                        mock_manager = Mock(spec=CrewAIAgent)
                        mock_manager.role = "Manager"
                        mock_manager.goal = "Manage team"
                        mock_manager.backstory = "Manager"
                        mock_manager.verbose = True
                        mock_manager.allow_delegation = True
                        mock_create_manager.return_value = mock_manager
                        
                        mock_regular = Mock(spec=CrewAIAgent)
                        mock_regular.role = "Developer"
                        mock_regular.goal = "Code"
                        mock_regular.backstory = "Developer"
                        mock_regular.verbose = True
                        mock_create_agent.return_value = mock_regular
                        
                        # Mock Task creation to prevent validation errors
                        mock_task_instance = Mock(spec=Task)
                        mock_task.return_value = mock_task_instance
                        
                        crew_wrapper.create_crew_from_dict(crew_config)
                        
                        # Check that hierarchical process and manager_agent were set
                        call_args = mock_crew.call_args[1]
                        assert call_args.get("process") == "hierarchical"
                        assert "manager_agent" in call_args 