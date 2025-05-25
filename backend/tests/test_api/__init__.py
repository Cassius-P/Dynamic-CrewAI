import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models.crew import Crew
from app.models.agent import Agent
from app.models.llm_provider import LLMProvider


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create and clean up test database for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_create_crew():
    """Test creating a crew."""
    crew_data = {
        "name": "Test Crew",
        "description": "A test crew",
        "process": "sequential",
        "verbose": True,
        "memory": False
    }
    
    response = client.post("/api/v1/crews/", json=crew_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == "Test Crew"
    assert data["description"] == "A test crew"
    assert data["id"] is not None


def test_get_crews():
    """Test getting list of crews."""
    # Create a crew first
    crew_data = {
        "name": "Test Crew",
        "description": "A test crew"
    }
    client.post("/api/v1/crews/", json=crew_data)
    
    response = client.get("/api/v1/crews/")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Test Crew"


def test_get_crew_by_id():
    """Test getting a specific crew by ID."""
    # Create a crew first
    crew_data = {
        "name": "Test Crew",
        "description": "A test crew"
    }
    create_response = client.post("/api/v1/crews/", json=crew_data)
    crew_id = create_response.json()["id"]
    
    response = client.get(f"/api/v1/crews/{crew_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == crew_id
    assert data["name"] == "Test Crew"


def test_update_crew():
    """Test updating a crew."""
    # Create a crew first
    crew_data = {
        "name": "Test Crew",
        "description": "A test crew"
    }
    create_response = client.post("/api/v1/crews/", json=crew_data)
    crew_id = create_response.json()["id"]
    
    # Update the crew
    update_data = {
        "name": "Updated Crew",
        "description": "An updated test crew"
    }
    response = client.put(f"/api/v1/crews/{crew_id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "Updated Crew"
    assert data["description"] == "An updated test crew"


def test_delete_crew():
    """Test deleting a crew."""
    # Create a crew first
    crew_data = {
        "name": "Test Crew",
        "description": "A test crew"
    }
    create_response = client.post("/api/v1/crews/", json=crew_data)
    crew_id = create_response.json()["id"]
    
    # Delete the crew
    response = client.delete(f"/api/v1/crews/{crew_id}")
    assert response.status_code == 204
    
    # Verify it's deleted
    get_response = client.get(f"/api/v1/crews/{crew_id}")
    assert get_response.status_code == 404


def test_create_agent():
    """Test creating an agent."""
    agent_data = {
        "role": "Data Analyst",
        "goal": "Analyze data effectively",
        "backstory": "Expert in data analysis",
        "verbose": True,
        "allow_delegation": False
    }
    
    response = client.post("/api/v1/agents/", json=agent_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["role"] == "Data Analyst"
    assert data["goal"] == "Analyze data effectively"
    assert data["id"] is not None


def test_create_llm_provider():
    """Test creating an LLM provider."""
    provider_data = {
        "name": "openai-gpt4",
        "provider_type": "openai",
        "model_name": "gpt-4",
        "api_key": "test-key",
        "temperature": "0.7",
        "is_active": True
    }
    
    response = client.post("/api/v1/llm-providers/", json=provider_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == "openai-gpt4"
    assert data["provider_type"] == "openai"
    assert data["api_key"] == "***hidden***"  # Should be hidden
    assert data["id"] is not None
