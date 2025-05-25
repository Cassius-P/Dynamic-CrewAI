import pytest


def test_create_llm_provider(client):
    """Test creating an LLM provider."""
    provider_data = {
        "name": "openai-test",
        "provider_type": "openai",
        "model_name": "gpt-3.5-turbo",
        "api_key": "test-key",
        "temperature": "0.7",
        "max_tokens": 1000,
        "is_active": True
    }
    
    response = client.post("/api/v1/llm-providers/", json=provider_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == "openai-test"
    assert data["provider_type"] == "openai"
    assert data["model_name"] == "gpt-3.5-turbo"
    assert data["id"] is not None


def test_get_llm_providers(client):
    """Test getting list of LLM providers."""
    # Create a provider first
    provider_data = {
        "name": "openai-test",
        "provider_type": "openai",
        "model_name": "gpt-3.5-turbo",
        "api_key": "test-key"
    }
    client.post("/api/v1/llm-providers/", json=provider_data)
    
    response = client.get("/api/v1/llm-providers/")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "openai-test"


def test_get_llm_provider_by_id(client):
    """Test getting a specific LLM provider by ID."""
    # Create a provider first
    provider_data = {
        "name": "openai-test",
        "provider_type": "openai",
        "model_name": "gpt-3.5-turbo",
        "api_key": "test-key"
    }
    create_response = client.post("/api/v1/llm-providers/", json=provider_data)
    provider_id = create_response.json()["id"]
    
    response = client.get(f"/api/v1/llm-providers/{provider_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == provider_id
    assert data["name"] == "openai-test"


def test_update_llm_provider(client):
    """Test updating an LLM provider."""
    # Create a provider first
    provider_data = {
        "name": "openai-test",
        "provider_type": "openai",
        "model_name": "gpt-3.5-turbo",
        "api_key": "test-key"
    }
    create_response = client.post("/api/v1/llm-providers/", json=provider_data)
    provider_id = create_response.json()["id"]
    
    # Update the provider
    update_data = {
        "name": "openai-updated",
        "model_name": "gpt-4"
    }
    response = client.put(f"/api/v1/llm-providers/{provider_id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "openai-updated"
    assert data["model_name"] == "gpt-4"


def test_delete_llm_provider(client):
    """Test deleting an LLM provider."""
    # Create a provider first
    provider_data = {
        "name": "openai-test",
        "provider_type": "openai",
        "model_name": "gpt-3.5-turbo",
        "api_key": "test-key"
    }
    create_response = client.post("/api/v1/llm-providers/", json=provider_data)
    provider_id = create_response.json()["id"]
    
    # Delete the provider
    response = client.delete(f"/api/v1/llm-providers/{provider_id}")
    assert response.status_code == 204
    
    # Verify it's deleted
    get_response = client.get(f"/api/v1/llm-providers/{provider_id}")
    assert get_response.status_code == 404


def test_llm_provider_not_found(client):
    """Test getting a non-existent LLM provider."""
    response = client.get("/api/v1/llm-providers/999")
    assert response.status_code == 404


def test_create_llm_provider_validation_error(client):
    """Test creating an LLM provider with invalid data."""
    provider_data = {
        "name": "",  # Empty name should fail
        "provider_type": "openai",
        "model_name": "gpt-3.5-turbo"
    }
    
    response = client.post("/api/v1/llm-providers/", json=provider_data)
    assert response.status_code == 422
