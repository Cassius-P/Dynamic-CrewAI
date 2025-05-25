from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AgentBase(BaseModel):
    """Base schema for Agent."""
    role: str = Field(..., min_length=1, max_length=255)
    goal: str = Field(..., min_length=1)
    backstory: str = Field(..., min_length=1)
    verbose: bool = False
    allow_delegation: bool = False
    max_iter: Optional[int] = Field(None, gt=0)
    max_execution_time: Optional[int] = Field(None, gt=0)
    tools: Optional[List[str]] = None
    llm_config: Optional[Dict[str, Any]] = None


class AgentCreate(AgentBase):
    """Schema for creating an agent."""
    crew_id: Optional[int] = None


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""
    role: Optional[str] = Field(None, min_length=1, max_length=255)
    goal: Optional[str] = Field(None, min_length=1)
    backstory: Optional[str] = Field(None, min_length=1)
    verbose: Optional[bool] = None
    allow_delegation: Optional[bool] = None
    max_iter: Optional[int] = Field(None, gt=0)
    max_execution_time: Optional[int] = Field(None, gt=0)
    tools: Optional[List[str]] = None
    llm_config: Optional[Dict[str, Any]] = None
    crew_id: Optional[int] = None


class AgentResponse(AgentBase):
    """Schema for agent response."""
    id: int
    crew_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}
