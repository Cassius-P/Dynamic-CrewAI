from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class CrewBase(BaseModel):
    """Base schema for Crew."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    process: str = Field(default="sequential")
    
    @field_validator('process')
    @classmethod
    def validate_process(cls, v):
        if v not in ["sequential", "hierarchical"]:
            raise ValueError("Process must be 'sequential' or 'hierarchical'")
        return v
    verbose: bool = False
    memory: bool = False
    max_rpm: Optional[int] = Field(None, gt=0)
    max_execution_time: Optional[int] = Field(None, gt=0)
    config: Optional[Dict[str, Any]] = None


class CrewCreate(CrewBase):
    """Schema for creating a crew."""
    pass


class CrewUpdate(BaseModel):
    """Schema for updating a crew."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    process: Optional[str] = None
    
    @field_validator('process')
    @classmethod
    def validate_process(cls, v):
        if v is not None and v not in ["sequential", "hierarchical"]:
            raise ValueError("Process must be 'sequential' or 'hierarchical'")
        return v
    verbose: Optional[bool] = None
    memory: Optional[bool] = None
    max_rpm: Optional[int] = Field(None, gt=0)
    max_execution_time: Optional[int] = Field(None, gt=0)
    config: Optional[Dict[str, Any]] = None


class CrewResponse(CrewBase):
    """Schema for crew response."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}
