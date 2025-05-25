import pytest
from pydantic import ValidationError
from app.schemas.crew import CrewCreate, CrewUpdate, CrewResponse
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse
from app.schemas.llm_provider import LLMProviderCreate, LLMProviderResponse


def test_crew_create_schema():
    """Test CrewCreate schema validation."""
    crew_data = {
        "name": "Test Crew",
        "description": "A test crew",
        "process": "sequential",
        "verbose": True,
        "memory": False
    }
    
    crew = CrewCreate(**crew_data)
    
    assert crew.name == "Test Crew"
    assert crew.description == "A test crew"
    assert crew.process == "sequential"
    assert crew.verbose is True
    assert crew.memory is False


def test_crew_create_schema_validation():
    """Test CrewCreate schema validation with invalid data."""
    with pytest.raises(ValidationError):
        CrewCreate(name="")  # Empty name should fail  # type: ignore
    
    with pytest.raises(ValidationError):
        CrewCreate(name="Test", process="invalid_process")  # Invalid process  # type: ignore


def test_agent_create_schema():
    """Test AgentCreate schema validation."""
    agent_data = {
        "role": "Data Analyst",
        "goal": "Analyze data effectively",
        "backstory": "Expert in data analysis",
        "verbose": True,
        "allow_delegation": False
    }
    
    agent = AgentCreate(**agent_data)
    
    assert agent.role == "Data Analyst"
    assert agent.goal == "Analyze data effectively"
    assert agent.backstory == "Expert in data analysis"
    assert agent.verbose is True
    assert agent.allow_delegation is False


def test_agent_create_schema_validation():
    """Test AgentCreate schema validation with invalid data."""
    with pytest.raises(ValidationError):
        AgentCreate(role="", goal="test", backstory="test")  # Empty role  # type: ignore
    
    with pytest.raises(ValidationError):
        AgentCreate(role="test", goal="", backstory="test")  # Empty goal  # type: ignore


def test_llm_provider_create_schema():
    """Test LLMProviderCreate schema validation."""
    provider_data = {
        "name": "openai-gpt4",
        "provider_type": "openai",
        "model_name": "gpt-4",
        "api_key": "test-key",
        "temperature": "0.7",
        "is_active": True
    }
    
    provider = LLMProviderCreate(**provider_data)
    
    assert provider.name == "openai-gpt4"
    assert provider.provider_type == "openai"
    assert provider.model_name == "gpt-4"
    assert provider.temperature == "0.7"
    assert provider.is_active is True


def test_llm_provider_schema_validation():
    """Test LLMProviderCreate schema validation with invalid data."""
    with pytest.raises(ValidationError):
        LLMProviderCreate(name="", provider_type="openai", model_name="gpt-4")  # type: ignore
    
    with pytest.raises(ValidationError):
        LLMProviderCreate(name="test", provider_type="invalid", model_name="gpt-4")  # type: ignore
