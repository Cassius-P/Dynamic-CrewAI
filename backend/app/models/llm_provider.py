from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class LLMProvider(Base):
    """LLM Provider model for storing LLM configurations."""
    
    __tablename__ = "llm_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    provider_type = Column(String(50), nullable=False)  # openai, anthropic, ollama
    model_name = Column(String(255), nullable=False)
    api_key = Column(String(512))  # Encrypted storage recommended
    api_base = Column(String(512))  # For custom endpoints
    api_version = Column(String(50))
    temperature = Column(String(10))  # Store as string to handle various formats
    max_tokens = Column(Integer)
    config = Column(JSON)  # Additional provider-specific configuration
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
