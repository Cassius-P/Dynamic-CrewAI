from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # API
    project_name: str = "CrewAI Backend"
    api_v1_str: str = "/api/v1"
    debug: bool = True
    
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/crewai_backend"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str = "your-secret-key-here"
    
    # Logging
    log_level: str = "INFO"


settings = Settings()
