import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Crew, Agent, LLMProvider, Execution, ExecutionStatus
from app.database import Base


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_crew_model_creation(db_session):
    """Test Crew model creation and basic fields."""
    crew = Crew(
        name="Test Crew",
        description="A test crew",
        process="sequential",
        verbose=True,
        memory=True
    )
    
    db_session.add(crew)
    db_session.commit()
    db_session.refresh(crew)
    
    assert crew.id is not None
    assert crew.name == "Test Crew"  # type: ignore
    assert crew.description == "A test crew"  # type: ignore
    assert crew.process == "sequential"  # type: ignore
    assert crew.verbose is True  # type: ignore
    assert crew.memory is True  # type: ignore
    assert isinstance(crew.created_at, datetime)
    # updated_at is None on creation, only set on updates
    assert crew.updated_at is None


def test_agent_model_creation(db_session):
    """Test Agent model creation and basic fields."""
    agent = Agent(
        role="Test Role",
        goal="Test Goal",
        backstory="Test Backstory",
        verbose=True,
        allow_delegation=False
    )
    
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    
    assert agent.id is not None
    assert agent.role == "Test Role"  # type: ignore
    assert agent.goal == "Test Goal"  # type: ignore
    assert agent.backstory == "Test Backstory"  # type: ignore
    assert agent.verbose is True  # type: ignore
    assert agent.allow_delegation is False  # type: ignore
    assert isinstance(agent.created_at, datetime)


def test_llm_provider_model_creation(db_session):
    """Test LLMProvider model creation and basic fields."""
    provider = LLMProvider(
        name="openai",
        provider_type="openai",
        model_name="gpt-3.5-turbo",
        api_key="test-key",
        is_active=True
    )
    
    db_session.add(provider)
    db_session.commit()
    db_session.refresh(provider)
    
    assert provider.id is not None
    assert provider.name == "openai"  # type: ignore
    assert provider.provider_type == "openai"  # type: ignore
    assert provider.model_name == "gpt-3.5-turbo"  # type: ignore
    assert provider.api_key == "test-key"  # type: ignore
    assert provider.is_active is True  # type: ignore


def test_crew_agent_relationship(db_session):
    """Test the relationship between Crew and Agent models."""
    crew = Crew(
        name="Test Crew",
        description="A test crew"    )
    
    agent = Agent(
        role="Test Role",
        goal="Test Goal",
        backstory="Test Backstory"
    )
    
    crew.agents.append(agent)
    
    db_session.add(crew)
    db_session.commit()
    
    assert len(crew.agents) == 1
    assert crew.agents[0].role == "Test Role"  # type: ignore
    assert agent.crew_id == crew.id  # type: ignore
