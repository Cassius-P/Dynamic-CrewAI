"""Tests for the AgentWrapper class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from crewai import Agent
from app.core.agent_wrapper import AgentWrapper
from app.models.agent import Agent as AgentModel
from app.models.llm_provider import LLMProvider


class TestAgentWrapper:
    """Test cases for the AgentWrapper class."""

    def test_init(self):
        """Test AgentWrapper initialization."""
        wrapper = AgentWrapper()
        assert wrapper is not None
        assert hasattr(wrapper, 'tool_registry')

    @patch('app.core.agent_wrapper.ToolRegistry')
    def test_init_with_tool_registry(self, mock_tool_registry):
        """Test AgentWrapper initialization with tool registry."""
        mock_registry_instance = Mock()
        mock_tool_registry.return_value = mock_registry_instance
        
        wrapper = AgentWrapper()
        assert wrapper.tool_registry == mock_registry_instance

    @patch('app.core.agent_wrapper.Agent')
    @patch('app.core.agent_wrapper.ToolRegistry')
    def test_create_agent_from_model(self, mock_tool_registry, mock_agent_class):
        """Test creating agent from database model."""
        # Setup mocks
        mock_registry = Mock()
        mock_tool_registry.return_value = mock_registry
        mock_registry.create_tools.return_value = [Mock(), Mock()]
        
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance
        
        # Create mock model
        mock_model = Mock(spec=AgentModel)
        mock_model.name = "Test Agent"
        mock_model.role = "Research Specialist"
        mock_model.goal = "Research and analyze data"
        mock_model.backstory = "Expert researcher with 10 years experience"
        mock_model.tools = ["file_read_tool", "web_search_tool"]
        mock_model.max_iter = 10
        mock_model.max_execution_time = 300
        mock_model.step_callback = None
        mock_model.system_template = None
        mock_model.prompt_template = None
        mock_model.response_template = None
        mock_model.allow_code_execution = False
        mock_model.max_retry_limit = 3
        mock_model.use_system_prompt = True
        mock_model.verbose = True
        mock_model.respect_context_window = True
        mock_model.memory = False
        mock_model.llm_provider = None
        
        wrapper = AgentWrapper()
        agent = wrapper.create_agent_from_model(mock_model)
        
        # Verify agent creation
        assert agent == mock_agent_instance
        mock_agent_class.assert_called_once()
        
        # Verify tool creation was called
        mock_registry.create_tools.assert_called_once_with(["file_read_tool", "web_search_tool"])

    @patch('app.core.agent_wrapper.Agent')
    @patch('app.core.agent_wrapper.LLMWrapper')
    def test_create_agent_from_model_with_llm(self, mock_llm_wrapper, mock_agent_class):
        """Test creating agent from model with LLM provider."""
        # Setup LLM mock
        mock_llm_instance = Mock()
        mock_llm_wrapper.return_value.create_llm_from_model.return_value = mock_llm_instance
        
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance
        
        # Create mock model with LLM provider
        mock_llm_provider = Mock(spec=LLMProvider)
        mock_llm_provider.name = "OpenAI GPT-4"
        
        mock_model = Mock(spec=AgentModel)
        mock_model.name = "Test Agent"
        mock_model.role = "Analyst"
        mock_model.goal = "Analyze data"
        mock_model.backstory = "Data analyst"
        mock_model.tools = []
        mock_model.llm_provider = mock_llm_provider
        mock_model.max_iter = 5
        mock_model.max_execution_time = 300
        mock_model.step_callback = None
        mock_model.system_template = None
        mock_model.prompt_template = None
        mock_model.response_template = None
        mock_model.allow_code_execution = False
        mock_model.max_retry_limit = 3
        mock_model.use_system_prompt = True
        mock_model.verbose = False
        mock_model.respect_context_window = True
        mock_model.memory = True
        
        wrapper = AgentWrapper()
        agent = wrapper.create_agent_from_model(mock_model)
        
        # Verify agent and LLM creation
        assert agent == mock_agent_instance
        mock_agent_class.assert_called_once()
        mock_llm_wrapper.assert_called_once()

    @patch('app.core.agent_wrapper.Agent')
    def test_create_agent_from_dict(self, mock_agent_class):
        """Test creating agent from dictionary configuration."""
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance
        
        config = {
            "name": "Test Agent",
            "role": "Developer",
            "goal": "Write clean code",
            "backstory": "Senior developer with expertise in Python",
            "tools": ["file_read_tool"],
            "verbose": True
        }
        
        wrapper = AgentWrapper()
        agent = wrapper.create_agent_from_dict(config)
        
        assert agent == mock_agent_instance
        mock_agent_class.assert_called_once()

    def test_create_agent_from_dict_missing_required(self):
        """Test creating agent from dict with missing required fields."""
        config = {
            "name": "Test Agent",
            # Missing role, goal, backstory
        }
        
        wrapper = AgentWrapper()
        
        with pytest.raises(ValueError, match="Missing required fields"):
            wrapper.create_agent_from_dict(config)

    @patch('app.core.agent_wrapper.Agent')
    def test_create_agent_from_dict_with_llm_config(self, mock_agent_class):
        """Test creating agent from dict with LLM configuration."""
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance
        
        config = {
            "name": "Test Agent",
            "role": "Analyst",
            "goal": "Analyze data",
            "backstory": "Data analyst",
            "llm_config": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7
            }
        }
        
        wrapper = AgentWrapper()
        agent = wrapper.create_agent_from_dict(config)
        
        assert agent == mock_agent_instance
        mock_agent_class.assert_called_once()

    def test_validate_agent_config_valid(self):
        """Test validation of valid agent configuration."""
        config = {
            "name": "Test Agent",
            "role": "Developer",
            "goal": "Write code",
            "backstory": "Experienced developer"        }
        
        wrapper = AgentWrapper()
        
        # Should not raise any exception
        wrapper._validate_agent_config(config)

    def test_validate_agent_config_missing_name(self):
        """Test validation with missing name - should pass since name is optional."""
        config = {
            "role": "Developer",
            "goal": "Write code", 
            "backstory": "Experienced developer"
        }
        
        wrapper = AgentWrapper()
        
        # Should not raise any exception since name is optional
        wrapper._validate_agent_config(config)

    def test_validate_agent_config_missing_role(self):
        """Test validation with missing role."""
        config = {
            "name": "Test Agent",
            "goal": "Write code",
            "backstory": "Experienced developer"
        }
        
        wrapper = AgentWrapper()
        
        with pytest.raises(ValueError, match="Missing required fields"):
            wrapper._validate_agent_config(config)

    def test_validate_agent_config_empty_values(self):
        """Test validation with empty string values."""
        config = {
            "name": "",
            "role": "Developer",
            "goal": "Write code",
            "backstory": "Experienced developer"
        }
        
        wrapper = AgentWrapper()
        
        with pytest.raises(ValueError, match="cannot be empty"):
            wrapper._validate_agent_config(config)

    def test_validate_agent_config_none_values(self):
        """Test validation with None values."""
        config = {
            "name": "Test Agent",
            "role": None,
            "goal": "Write code",
            "backstory": "Experienced developer"
        }
        
        wrapper = AgentWrapper()
        
        with pytest.raises(ValueError, match="cannot be empty"):
            wrapper._validate_agent_config(config)

    @patch('app.core.agent_wrapper.ToolRegistry')
    def test_prepare_tools_with_tools(self, mock_tool_registry):
        """Test tool preparation with tool names."""
        mock_registry = Mock()
        mock_tool_registry.return_value = mock_registry
        
        mock_tools = [Mock(), Mock()]
        mock_registry.create_tools.return_value = mock_tools
        
        wrapper = AgentWrapper()
        tools = wrapper._prepare_tools(["file_read_tool", "web_search_tool"])
        
        assert tools == mock_tools
        mock_registry.create_tools.assert_called_once_with(["file_read_tool", "web_search_tool"])

    @patch('app.core.agent_wrapper.ToolRegistry')
    def test_prepare_tools_empty_list(self, mock_tool_registry):
        """Test tool preparation with empty tool list."""
        mock_registry = Mock()
        mock_tool_registry.return_value = mock_registry
        mock_registry.create_tools.return_value = []
        
        wrapper = AgentWrapper()
        tools = wrapper._prepare_tools([])
        
        assert tools == []
        mock_registry.create_tools.assert_called_once_with([])

    @patch('app.core.agent_wrapper.ToolRegistry')
    def test_prepare_tools_none(self, mock_tool_registry):
        """Test tool preparation with None."""
        mock_registry = Mock()
        mock_tool_registry.return_value = mock_registry
        
        wrapper = AgentWrapper()
        tools = wrapper._prepare_tools(None)
        
        assert tools == []
        mock_registry.create_tools.assert_not_called()

    @patch('app.core.agent_wrapper.LLMWrapper')
    def test_prepare_llm_from_provider(self, mock_llm_wrapper):
        """Test LLM preparation from provider model."""
        mock_llm_instance = Mock()
        mock_wrapper_instance = Mock()
        mock_wrapper_instance.create_llm_from_model.return_value = mock_llm_instance
        mock_llm_wrapper.return_value = mock_wrapper_instance
        
        mock_provider = Mock(spec=LLMProvider)
        
        wrapper = AgentWrapper()
        llm = wrapper._prepare_llm(mock_provider)
        
        assert llm == mock_llm_instance
        mock_llm_wrapper.assert_called_once()
        mock_wrapper_instance.create_llm_from_model.assert_called_once_with(mock_provider)

    @patch('app.core.agent_wrapper.LLMWrapper')
    def test_prepare_llm_from_config(self, mock_llm_wrapper):
        """Test LLM preparation from configuration dict."""
        mock_llm_instance = Mock()
        mock_wrapper_instance = Mock()
        mock_wrapper_instance.create_llm_from_config.return_value = mock_llm_instance
        mock_llm_wrapper.return_value = mock_wrapper_instance
        
        llm_config = {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.7
        }
        
        wrapper = AgentWrapper()
        llm = wrapper._prepare_llm(llm_config)
        
        assert llm == mock_llm_instance
        mock_llm_wrapper.assert_called_once()
        mock_wrapper_instance.create_llm_from_config.assert_called_once_with(llm_config)

    def test_prepare_llm_none(self):
        """Test LLM preparation with None."""
        wrapper = AgentWrapper()
        llm = wrapper._prepare_llm(None)
        
        assert llm is None

    @patch('app.core.agent_wrapper.Agent')
    def test_agent_creation_exception_handling(self, mock_agent_class):
        """Test exception handling during agent creation."""
        mock_agent_class.side_effect = Exception("Agent creation failed")
        
        mock_model = Mock(spec=AgentModel)
        mock_model.name = "Test Agent"
        mock_model.role = "Developer"
        mock_model.goal = "Write code"
        mock_model.backstory = "Developer"
        mock_model.tools = []
        mock_model.llm_provider = None
        mock_model.max_iter = 5
        mock_model.max_execution_time = 300
        mock_model.step_callback = None
        mock_model.system_template = None
        mock_model.prompt_template = None
        mock_model.response_template = None
        mock_model.allow_code_execution = False
        mock_model.max_retry_limit = 3
        mock_model.use_system_prompt = True
        mock_model.verbose = True
        mock_model.respect_context_window = True
        mock_model.memory = False
        
        wrapper = AgentWrapper()
        
        with pytest.raises(Exception, match="Agent creation failed"):
            wrapper.create_agent_from_model(mock_model)

    @patch('app.core.agent_wrapper.Agent')
    def test_create_agent_with_all_parameters(self, mock_agent_class):
        """Test creating agent with all possible parameters."""
        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance
        
        config = {
            "name": "Test Agent",
            "role": "Senior Developer", 
            "goal": "Develop high-quality software",
            "backstory": "10+ years of software development experience",
            "tools": ["file_read_tool", "file_write_tool"],
            "max_iter": 15,
            "max_execution_time": 600,
            "verbose": True,
            "allow_code_execution": True,
            "max_retry_limit": 5,
            "use_system_prompt": False,
            "respect_context_window": False,
            "memory": True
        }
        
        wrapper = AgentWrapper()
        agent = wrapper.create_agent_from_dict(config)
        
        assert agent == mock_agent_instance
        mock_agent_class.assert_called_once()
        
        # Verify the call arguments include our parameters
        call_kwargs = mock_agent_class.call_args[1]
        assert call_kwargs['role'] == "Senior Developer"
        assert call_kwargs['goal'] == "Develop high-quality software"
        assert call_kwargs['backstory'] == "10+ years of software development experience"
        assert call_kwargs['max_iter'] == 15
        assert call_kwargs['max_execution_time'] == 600
        assert call_kwargs['verbose'] is True
        assert call_kwargs['allow_code_execution'] is True
