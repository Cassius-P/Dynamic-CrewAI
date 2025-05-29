from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator, ValidationError
import sys
import os


class Settings(BaseSettings):
    """Application settings with validation for required environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # API
    project_name: str = "CrewAI Backend"
    api_v1_str: str = "/api/v1"
    debug: bool = True
    environment: str = "development"
    allowed_hosts: str = "*"
    
    # Database - Use environment variables for construction
    postgres_db: str = "crewai"
    postgres_user: str = "crewai"
    postgres_password: str = Field(default="", min_length=1, description="PostgreSQL password")
    postgres_host: str = "localhost"
    postgres_port: int = Field(default=5432, ge=1, le=65535, description="PostgreSQL port")
    
    @property
    def database_url(self) -> str:
        """Construct database URL from components."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    # Redis - Use environment variables for construction
    redis_host: str = "localhost"
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    redis_password: str = Field(default="", min_length=1, description="Redis password")
    
    @property
    def redis_url(self) -> str:
        """Construct Redis URL from components."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production", min_length=1, description="Secret key for FastAPI")
    
    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    
    # Application
    app_port: int = Field(default=8000, ge=1, le=65535, description="Application port")
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(valid_levels)}")
        return v.upper()
    
    @model_validator(mode='after')
    def validate_production_requirements(self):
        """Validate production requirements."""
        is_production = self.environment.lower() == 'production'
        is_docker = os.getenv('DOCKER_ENV') == 'true'
        
        # Only enforce strict validation in production or Docker
        if is_production or is_docker:
            # Check for required passwords
            if not self.postgres_password or len(self.postgres_password) < 8:
                raise ValueError("POSTGRES_PASSWORD must be at least 8 characters in production")
            
            if not self.redis_password or len(self.redis_password) < 8:
                raise ValueError("REDIS_PASSWORD must be at least 8 characters in production")
            
            if self.secret_key == "dev-secret-key-change-in-production" or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be changed and at least 32 characters in production")
            
            # Check for weak passwords
            if self.postgres_password in ["password", "postgres", "123456", "admin"]:
                raise ValueError("POSTGRES_PASSWORD must not be a common/weak password")
            
            if self.redis_password in ["password", "redis", "123456", "admin"]:
                raise ValueError("REDIS_PASSWORD must not be a common/weak password")
            
            # Production-specific checks
            if is_production and self.debug:
                raise ValueError("DEBUG must be False in production environment")
        
        return self


def create_settings():
    """Create settings with proper error handling."""
    try:
        settings = Settings()
        
        # Check if we're in production/Docker and validate accordingly
        is_production = settings.environment.lower() == 'production'
        is_docker = os.getenv('DOCKER_ENV') == 'true'
        
        if is_production or is_docker:
            print("✅ Production environment validation passed!")
        else:
            print("✅ Development environment loaded")
            
        return settings
        
    except ValidationError as e:
        print("\n❌ Environment validation failed!")
        print("Missing or invalid environment variables:")
        for error in e.errors():
            loc = error.get('loc', ())
            field = str(loc[0]) if loc else 'unknown'
            msg = error.get('msg', 'Invalid value')
            print(f"   - {field.upper()}: {msg}")
        
        print("\n🔧 Required environment variables for production:")
        print("   - POSTGRES_PASSWORD (min 8 chars, not common passwords)")
        print("   - REDIS_PASSWORD (min 8 chars, not common passwords)")
        print("   - SECRET_KEY (min 32 chars, not default value)")
        print("   - DOCKER_ENV=true (to enable production validation)")
        print("\n📋 Generate secure values:")
        print("   python -c \"import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(50))\"")
        print("   python -c \"import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(16))\"")
        print("   python -c \"import secrets; print('REDIS_PASSWORD=' + secrets.token_urlsafe(16))\"")
        print()
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Configuration error: {str(e)}")
        sys.exit(1)


# Create settings instance
settings = create_settings()
