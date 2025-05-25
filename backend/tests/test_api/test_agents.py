def test_create_agent(client):
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
    assert data["backstory"] == "Expert in data analysis"
    assert data["id"] is not None


def test_get_agents(client):
    """Test getting list of agents."""
    # Create an agent first
    agent_data = {
        "role": "Data Analyst",
        "goal": "Analyze data effectively",
        "backstory": "Expert in data analysis"
    }
    client.post("/api/v1/agents/", json=agent_data)
    
    response = client.get("/api/v1/agents/")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) >= 1
    assert data[0]["role"] == "Data Analyst"


def test_get_agent_by_id(client):
    """Test getting a specific agent by ID."""
    # Create an agent first
    agent_data = {
        "role": "Data Analyst",
        "goal": "Analyze data effectively",
        "backstory": "Expert in data analysis"
    }
    create_response = client.post("/api/v1/agents/", json=agent_data)
    agent_id = create_response.json()["id"]
    
    response = client.get(f"/api/v1/agents/{agent_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == agent_id
    assert data["role"] == "Data Analyst"


def test_update_agent(client):
    """Test updating an agent."""
    # Create an agent first
    agent_data = {
        "role": "Data Analyst",
        "goal": "Analyze data effectively",
        "backstory": "Expert in data analysis"
    }
    create_response = client.post("/api/v1/agents/", json=agent_data)
    agent_id = create_response.json()["id"]
    
    # Update the agent
    update_data = {
        "role": "Senior Data Analyst",
        "goal": "Lead data analysis projects"
    }
    response = client.put(f"/api/v1/agents/{agent_id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["role"] == "Senior Data Analyst"
    assert data["goal"] == "Lead data analysis projects"
    assert data["backstory"] == "Expert in data analysis"  # Should remain unchanged


def test_delete_agent(client):
    """Test deleting an agent."""
    # Create an agent first
    agent_data = {
        "role": "Data Analyst",
        "goal": "Analyze data effectively",
        "backstory": "Expert in data analysis"
    }
    create_response = client.post("/api/v1/agents/", json=agent_data)
    agent_id = create_response.json()["id"]
    
    # Delete the agent
    response = client.delete(f"/api/v1/agents/{agent_id}")
    assert response.status_code == 204
    
    # Verify it's deleted
    get_response = client.get(f"/api/v1/agents/{agent_id}")
    assert get_response.status_code == 404


def test_agent_not_found(client):
    """Test getting a non-existent agent."""
    response = client.get("/api/v1/agents/999")
    assert response.status_code == 404


def test_create_agent_validation_error(client):
    """Test creating an agent with invalid data."""
    agent_data = {
        "role": "",  # Empty role should fail
        "goal": "Analyze data effectively",
        "backstory": "Expert in data analysis"
    }
    
    response = client.post("/api/v1/agents/", json=agent_data)
    assert response.status_code == 422
