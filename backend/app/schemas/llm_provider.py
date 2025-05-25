from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class LLMProviderBase(BaseModel):
    """Base schema for LLM Provider."""
    name: str = Field(..., min_length=1, max_length=255)
    provider_type: str = Field(...)
    
    @field_validator('provider_type')
    @classmethod
    def validate_provider_type(cls, v):
        if v not in ["openai", "anthropic", "ollama"]:
            raise ValueError("Provider type must be 'openai', 'anthropic', or 'ollama'")
        return v
    model_name: str = Field(..., min_length=1, max_length=255)
    api_key: Optional[str] = Field(None, max_length=512)
    api_base: Optional[str] = Field(None, max_length=512)
    api_version: Optional[str] = Field(None, max_length=50)
    temperature: Optional[str] = None
    max_tokens: Optional[int] = Field(None, gt=0)
    config: Optional[Dict[str, Any]] = None
    is_active: bool = True


class LLMProviderCreate(LLMProviderBase):
    """Schema for creating an LLM provider."""
    pass


class LLMProviderUpdate(BaseModel):
    """Schema for updating an LLM provider."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    provider_type: Optional[str] = None
    model_name: Optional[str] = Field(None, min_length=1, max_length=255)
    api_key: Optional[str] = Field(None, max_length=512)
    api_base: Optional[str] = Field(None, max_length=512)
    api_version: Optional[str] = Field(None, max_length=50)
    temperature: Optional[str] = None
    max_tokens: Optional[int] = Field(None, gt=0)
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    
    @field_validator('provider_type')
    @classmethod
    def validate_provider_type(cls, v):
        if v is not None and v not in ["openai", "anthropic", "ollama"]:
            raise ValueError("Provider type must be 'openai', 'anthropic', or 'ollama'")
        return v


class LLMProviderResponse(LLMProviderBase):
    """Schema for LLM provider response."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Hide sensitive information in response
    api_key: Optional[str] = Field(None, description="Hidden for security")
    
    model_config = {"from_attributes": True}
    
    @field_validator('api_key', mode='before')
    @classmethod
    def hide_api_key(cls, v):
        """Hide API key in response for security."""
        if v:
            return "***hidden***"
        return v
