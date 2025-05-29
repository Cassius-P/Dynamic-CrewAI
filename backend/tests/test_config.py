import pytest
import os
from app.config import Settings


def test_settings_initialization():
    """Test that settings can be initialized with default values."""
    settings = Settings()
    
    assert settings.project_name is not None
    assert settings.api_v1_str is not None
    assert settings.debug is not None


def test_settings_database_url():
    """Test that database URL is properly configured."""
    settings = Settings()
    
    assert hasattr(settings, 'database_url')
    assert settings.database_url is not None


def test_settings_from_env(monkeypatch):
    """Test that settings can be loaded from environment variables."""
    monkeypatch.setenv("PROJECT_NAME", "Test Project")
    monkeypatch.setenv("DEBUG", "False")
    
    settings = Settings()
    
    assert settings.project_name == "Test Project"
    assert settings.debug is False


def test_production_validation_with_docker_env(monkeypatch):
    """Test that production validation is enforced when DOCKER_ENV is set."""
    # Set Docker environment variable
    monkeypatch.setenv("DOCKER_ENV", "true")
    monkeypatch.setenv("ENVIRONMENT", "production")
    
    # Should fail without proper credentials
    with pytest.raises(Exception):
        Settings()


def test_production_validation_with_proper_env_vars(monkeypatch):
    """Test that production validation passes with proper environment variables."""
    monkeypatch.setenv("DOCKER_ENV", "true")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secure_postgres_password_123")
    monkeypatch.setenv("REDIS_PASSWORD", "secure_redis_password_456")
    monkeypatch.setenv("SECRET_KEY", "very_secure_secret_key_for_production_environment_123456789")
    
    settings = Settings()
    
    assert settings.environment == "production"
    assert settings.debug is False
    assert settings.postgres_password == "secure_postgres_password_123"
    assert settings.redis_password == "secure_redis_password_456"
    assert settings.secret_key == "very_secure_secret_key_for_production_environment_123456789"


def test_development_mode_defaults():
    """Test that development mode works with default values."""
    settings = Settings()
    
    # Should use default values in development
    assert settings.postgres_password == ""
    assert settings.redis_password == ""
    assert settings.secret_key == "dev-secret-key-change-in-production"
    assert settings.environment == "development"
