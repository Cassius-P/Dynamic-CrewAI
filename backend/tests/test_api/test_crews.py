import pytest


def test_create_crew(client):
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


def test_get_crews(client):
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


def test_get_crew_by_id(client):
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


def test_update_crew(client):
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


def test_delete_crew(client):
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


def test_crew_not_found(client):
    """Test getting a non-existent crew."""
    response = client.get("/api/v1/crews/999")
    assert response.status_code == 404


def test_create_crew_validation_error(client):
    """Test creating a crew with invalid data."""
    crew_data = {
        "name": "",  # Empty name should fail
        "description": "A test crew"
    }
    
    response = client.post("/api/v1/crews/", json=crew_data)
    assert response.status_code == 422
