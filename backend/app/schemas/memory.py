from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from uuid import UUID


# Base memory schemas
class MemoryItemBase(BaseModel):
    """Base schema for memory items."""
    content: str = Field(..., min_length=1)
    content_type: str = Field(..., min_length=1, max_length=50)
    metadata: Optional[Dict[str, Any]] = None


class MemoryItemResponse(MemoryItemBase):
    """Response schema for memory items."""
    id: str
    created_at: datetime
    relevance_score: Optional[float] = None
    
    model_config = {"from_attributes": True}


class SearchResult(BaseModel):
    """Search result schema."""
    item: MemoryItemResponse
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    rank: int = Field(..., ge=1)


# Short-term memory schemas
class ShortTermMemoryCreate(MemoryItemBase):
    """Schema for creating short-term memory."""
    agent_id: Optional[int] = None
    execution_id: Optional[int] = None
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class ShortTermMemoryResponse(MemoryItemResponse):
    """Response schema for short-term memory."""
    agent_id: Optional[int] = None
    execution_id: Optional[int] = None
    expires_at: Optional[datetime] = None


class ShortTermMemorySearch(BaseModel):
    """Schema for short-term memory search."""
    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    content_type: Optional[str] = None
    agent_id: Optional[int] = None


# Long-term memory schemas
class LongTermMemoryCreate(MemoryItemBase):
    """Schema for creating long-term memory."""
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    source_execution_id: Optional[int] = None
    tags: Optional[List[str]] = None
    summary: Optional[str] = Field(None, max_length=500)


class LongTermMemoryResponse(MemoryItemResponse):
    """Response schema for long-term memory."""
    summary: Optional[str] = None
    importance_score: float
    access_count: int
    last_accessed: Optional[datetime] = None
    source_execution_id: Optional[int] = None
    tags: Optional[List[str]] = None
    updated_at: datetime


class LongTermMemoryUpdate(BaseModel):
    """Schema for updating long-term memory."""
    content: Optional[str] = Field(None, min_length=1)
    metadata: Optional[Dict[str, Any]] = None
    importance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags: Optional[List[str]] = None
    summary: Optional[str] = Field(None, max_length=500)


class LongTermMemorySearch(BaseModel):
    """Schema for long-term memory search."""
    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    content_type: Optional[str] = None
    min_importance: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags: Optional[List[str]] = None


# Entity memory schemas
class EntityMemoryCreate(MemoryItemBase):
    """Schema for creating entity memory."""
    entity_name: str = Field(..., min_length=1, max_length=255)
    entity_type: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)


class EntityMemoryResponse(MemoryItemResponse):
    """Response schema for entity memory."""
    entity_name: str
    entity_type: str
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    confidence_score: float
    mention_count: int
    first_mentioned: datetime
    last_updated: datetime


class EntityMemoryUpdate(BaseModel):
    """Schema for updating entity memory."""
    content: Optional[str] = Field(None, min_length=1)
    metadata: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class EntityMemorySearch(BaseModel):
    """Schema for entity memory search."""
    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    entity_type: Optional[str] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class EntityRelationshipCreate(BaseModel):
    """Schema for creating entity relationships."""
    source_entity_id: str
    target_entity_id: str
    relationship_type: str = Field(..., min_length=1, max_length=100)
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    context: Optional[str] = None


class EntityRelationshipResponse(BaseModel):
    """Response schema for entity relationships."""
    relationship_id: str
    relationship_type: str
    strength: float
    context: Optional[str] = None
    direction: str  # "outgoing" or "incoming"
    other_entity: Dict[str, Any]
    created_at: datetime


# Memory configuration schemas
class MemoryConfigurationUpdate(BaseModel):
    """Schema for updating memory configuration."""
    short_term_retention_hours: Optional[int] = Field(None, ge=1, le=8760)  # Max 1 year
    short_term_max_entries: Optional[int] = Field(None, ge=10, le=10000)
    long_term_consolidation_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    long_term_max_entries: Optional[int] = Field(None, ge=100, le=100000)
    entity_confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    entity_similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    embedding_provider: Optional[str] = Field(None, max_length=50)
    embedding_model: Optional[str] = Field(None, max_length=100)
    cleanup_enabled: Optional[bool] = None
    cleanup_interval_hours: Optional[int] = Field(None, ge=1, le=168)  # Max 1 week


class MemoryConfigurationResponse(BaseModel):
    """Response schema for memory configuration."""
    crew_id: int
    short_term_retention_hours: int
    short_term_max_entries: int
    long_term_consolidation_threshold: float
    long_term_max_entries: int
    entity_confidence_threshold: float
    entity_similarity_threshold: float
    embedding_provider: str
    embedding_model: str
    cleanup_enabled: bool
    cleanup_interval_hours: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# Memory statistics schemas
class MemoryStats(BaseModel):
    """Schema for memory statistics."""
    crew_id: int
    counts: Dict[str, int]
    limits: Dict[str, int]
    utilization: Dict[str, float]
    recent_cleanups: List[Dict[str, Any]]
    configuration: Dict[str, Any]


# Batch operation schemas
class MemorySearchRequest(BaseModel):
    """Schema for unified memory search."""
    query: str = Field(..., min_length=1)
    memory_types: Optional[List[str]] = None
    limit: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    
    @field_validator('memory_types')
    @classmethod
    def validate_memory_types(cls, v):
        if v is not None:
            valid_types = {"short_term", "long_term", "entity"}
            if not all(mt in valid_types for mt in v):
                raise ValueError(f"Memory types must be in {valid_types}")
        return v


class MemorySearchResponse(BaseModel):
    """Response schema for unified memory search."""
    short_term: Optional[List[SearchResult]] = None
    long_term: Optional[List[SearchResult]] = None
    entity: Optional[List[SearchResult]] = None


class ConversationContextRequest(BaseModel):
    """Schema for conversation context request."""
    limit: int = Field(default=20, ge=1, le=100)
    execution_id: Optional[int] = None


class ConsolidationResponse(BaseModel):
    """Response schema for memory consolidation."""
    evaluated: int
    consolidated: int
    threshold: float


class CleanupResponse(BaseModel):
    """Response schema for memory cleanup."""
    short_term_cleaned: int
    long_term_cleaned: int
    entity_cleaned: int
    total_cleaned: int
    execution_time: float


class ClearMemoryResponse(BaseModel):
    """Response schema for clearing memories."""
    short_term_cleared: int
    long_term_cleared: int
    entity_cleared: int
    total_cleared: int 