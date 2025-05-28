"""Tests for TaskGenerator class."""

import pytest
from unittest.mock import Mock
from typing import List

from app.tools.task_generation import TaskGenerator
from app.models.agent import Agent
from crewai import Task, Agent as CrewAIAgent


class TestTaskGenerator:
    """Test cases for TaskGenerator class."""

    @pytest.fixture
    def task_generator(self):
        """Create a TaskGenerator instance for testing."""
        return TaskGenerator()

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

    def test_task_generator_initialization(self, task_generator):
        """Test TaskGenerator initialization."""
        assert task_generator is not None
        assert hasattr(task_generator, 'task_patterns')
        assert len(task_generator.task_patterns) > 0

    def test_generate_tasks_simple_text(self, task_generator, manager_agent_model):
        """Test generating tasks from simple text input."""
        text_input = "Create a web application with user authentication"
        
        tasks = task_generator.generate_tasks(text_input, manager_agent_model)
        
        assert isinstance(tasks, list)
        assert len(tasks) >= 1
        
        # Check first task
        task = tasks[0]
        assert isinstance(task, Task)
        assert hasattr(task, 'description')
        assert hasattr(task, 'expected_output')

    def test_generate_tasks_empty_input(self, task_generator, manager_agent_model):
        """Test that empty input raises ValueError."""
        with pytest.raises(ValueError, match="Text input cannot be empty"):
            task_generator.generate_tasks("", manager_agent_model)

    def test_generate_tasks_non_manager_agent(self, task_generator):
        """Test that non-manager agent raises ValueError."""
        regular_agent = Agent(
            role="Developer",
            goal="Write code",
            backstory="Software developer",
            can_generate_tasks=False
        )
        
        with pytest.raises(ValueError, match="Agent cannot generate tasks"):
            task_generator.generate_tasks("Some task", regular_agent)

    def test_parse_task_descriptions_numbered_list(self, task_generator):
        """Test parsing numbered list format."""
        text_input = """
        1. Create user registration system
        2. Implement authentication
        3. Design user dashboard
        """
        
        descriptions = task_generator._parse_task_descriptions(text_input)
        
        assert len(descriptions) >= 3
        assert any("user registration system" in desc.lower() for desc in descriptions)
        assert any("authentication" in desc.lower() for desc in descriptions)
        assert any("user dashboard" in desc.lower() for desc in descriptions)

    def test_parse_task_descriptions_action_words(self, task_generator):
        """Test parsing with action words."""
        text_input = "Create a database. Build an API. Test the application."
        
        descriptions = task_generator._parse_task_descriptions(text_input)
        
        assert len(descriptions) >= 3
        assert any("database" in desc.lower() for desc in descriptions)
        assert any("api" in desc.lower() for desc in descriptions)
        assert any("application" in desc.lower() for desc in descriptions)

    def test_generate_expected_output_create(self, task_generator):
        """Test expected output generation for create tasks."""
        description = "Create a user authentication system"
        
        output = task_generator._generate_expected_output(description)
        
        assert "implementation" in output.lower()
        assert "user authentication system" in output

    def test_generate_expected_output_test(self, task_generator):
        """Test expected output generation for test tasks."""
        description = "Test the user login functionality"
        
        output = task_generator._generate_expected_output(description)
        
        assert "test results" in output.lower()
        assert "user login functionality" in output

    def test_validate_task_generation_input_valid(self, task_generator, manager_agent_model):
        """Test validation with valid input."""
        text_input = "Create a web application with authentication system"
        
        result = task_generator.validate_task_generation_input(text_input, manager_agent_model)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_task_generation_input_too_short(self, task_generator, manager_agent_model):
        """Test validation with input that's too short."""
        text_input = "Short"
        
        result = task_generator.validate_task_generation_input(text_input, manager_agent_model)
        
        assert result["valid"] is False
        assert any("too short" in error for error in result["errors"])

    def test_get_task_generation_config(self, task_generator, manager_agent_model):
        """Test getting task generation configuration."""
        config = task_generator.get_task_generation_config(manager_agent_model)
        
        assert isinstance(config, dict)
        assert "max_tasks_per_request" in config
        assert "task_validation_enabled" in config
        assert "auto_assign_agents" in config
        assert config["task_generation_llm"] == "gpt-4"

    def test_get_task_generation_config_defaults(self, task_generator):
        """Test getting default task generation configuration."""
        agent_no_config = Agent(
            role="Manager",
            goal="Manage",
            backstory="Manager",
            can_generate_tasks=True,
            manager_config=None
        )
        
        config = task_generator.get_task_generation_config(agent_no_config)
        
        assert isinstance(config, dict)
        assert config["task_generation_llm"] == "gpt-4"  # default
        assert config["max_tasks_per_request"] == 10  # default

    def test_create_task_with_agent(self, task_generator):
        """Test creating task with agent assignment."""
        description = "Test task description"
        expected_output = "Test expected output"
        # Create a proper CrewAI agent instead of Mock to avoid Pydantic issues
        test_agent =  CrewAIAgent(
            role="Test Agent",
            goal="Test goal",
            backstory="Test backstory"
        )
        
        task = task_generator.create_task_with_agent(description, expected_output, test_agent)
        
        assert isinstance(task, Task)
        assert task.description == description
        assert task.expected_output == expected_output
        # Agent assignment verification would require more complex mocking

    def test_enhance_task_descriptions(self, task_generator):
        """Test enhancing task descriptions with context."""
        descriptions = ["create database", "build api"]
        context = "for e-commerce website"
        
        enhanced = task_generator.enhance_task_descriptions(descriptions, context)
        
        assert len(enhanced) == 2
        assert context in enhanced[0]
        assert context in enhanced[1]
        # Check capitalization and punctuation
        assert enhanced[0].startswith("Create")
        assert enhanced[0].endswith(".") 