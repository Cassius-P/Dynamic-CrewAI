import pytest
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
