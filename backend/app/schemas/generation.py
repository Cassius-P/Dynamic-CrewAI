"""Pydantic schemas for dynamic crew generation."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# Request schemas
class GenerationRequestCreate(BaseModel):
    """Schema for creating a dynamic crew generation request."""
    objective: str = Field(..., min_length=10, max_length=5000, description="High-level objective for the crew")
    requirements: Optional[Dict[str, Any]] = Field(default=None, description="Specific requirements and constraints")
    template_id: Optional[int] = Field(default=None, description="Template ID to use for generation")
    llm_provider: Optional[str] = Field(default="openai", description="LLM provider for generation")
    optimization_enabled: Optional[bool] = Field(default=True, description="Enable crew optimization")


class TaskAnalysisRequest(BaseModel):
    """Schema for analyzing task requirements."""
    objective: str = Field(..., min_length=10, max_length=5000)
    context: Optional[str] = Field(default=None, max_length=2000)
    domain: Optional[str] = Field(default=None, max_length=100)


class CrewOptimizationRequest(BaseModel):
    """Schema for crew optimization request."""
    crew_id: int = Field(..., description="ID of crew to optimize")
    optimization_type: str = Field(..., description="Type of optimization to apply")
    target_metrics: Optional[Dict[str, float]] = Field(default=None, description="Target optimization metrics")


class CrewValidationRequest(BaseModel):
    """Schema for crew validation request."""
    crew_config: Dict[str, Any] = Field(..., description="Crew configuration to validate")
    objective: str = Field(..., description="Objective the crew should accomplish")


# Response schemas
class TaskRequirementResponse(BaseModel):
    """Schema for task requirement response."""
    requirement_type: str
    requirement_name: str
    requirement_value: str
    priority: int
    satisfied: bool
    metadata: Optional[Dict[str, Any]] = None


class AgentCapabilityResponse(BaseModel):
    """Schema for agent capability response."""
    capability_name: str
    capability_type: str
    proficiency_level: int
    description: Optional[str] = None
    verified: bool


class TaskAnalysisResponse(BaseModel):
    """Schema for task analysis response."""
    objective: str
    complexity_score: float = Field(..., ge=0.0, le=10.0)
    estimated_duration_hours: float
    required_skills: List[str]
    required_tools: List[str]
    task_requirements: List[TaskRequirementResponse]
    domain_category: str
    risk_factors: List[str]


class CrewCompositionSuggestion(BaseModel):
    """Schema for crew composition suggestion."""
    agent_role: str
    agent_description: str
    required_skills: List[str]
    suggested_tools: List[str]
    priority: int = Field(..., ge=1, le=5)


class GenerationResult(BaseModel):
    """Schema for generation result."""
    crew_config: Dict[str, Any]
    agent_configs: List[Dict[str, Any]]
    task_configs: List[Dict[str, Any]]
    manager_config: Dict[str, Any]
    tool_assignments: Dict[str, List[str]]
    estimated_performance: Dict[str, float]


class GenerationRequestResponse(BaseModel):
    """Schema for generation request response."""
    id: int
    objective: str
    requirements: Optional[Dict[str, Any]]
    generated_crew_id: Optional[int]
    template_id: Optional[int]
    llm_provider: str
    generation_status: str
    generation_result: Optional[GenerationResult]
    validation_result: Optional[Dict[str, Any]]
    optimization_applied: bool
    generation_time_seconds: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class CrewOptimizationResponse(BaseModel):
    """Schema for crew optimization response."""
    id: int
    crew_id: int
    optimization_type: str
    optimization_score: float
    optimization_metrics: Dict[str, Any]
    applied: bool
    created_at: datetime
    applied_at: Optional[datetime]

    class Config:
        from_attributes = True


class CrewValidationResponse(BaseModel):
    """Schema for crew validation response."""
    valid: bool
    validation_score: float = Field(..., ge=0.0, le=10.0)
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    capability_coverage: Dict[str, float]
    estimated_success_rate: float = Field(..., ge=0.0, le=1.0)


class DynamicCrewTemplateResponse(BaseModel):
    """Schema for dynamic crew template response."""
    id: int
    name: str
    description: Optional[str]
    template_type: str
    template_config: Dict[str, Any]
    success_rate: float
    usage_count: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class GenerationMetricsResponse(BaseModel):
    """Schema for generation metrics response."""
    id: int
    generation_request_id: int
    metric_name: str
    metric_value: float
    metric_unit: str
    metric_category: str
    metric_metadata: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# Template creation schemas
class DynamicCrewTemplateCreate(BaseModel):
    """Schema for creating a dynamic crew template."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    template_type: str = Field(..., max_length=100)
    template_config: Dict[str, Any] = Field(..., description="Template configuration")


class DynamicCrewTemplateUpdate(BaseModel):
    """Schema for updating a dynamic crew template."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    template_type: Optional[str] = Field(default=None, max_length=100)
    template_config: Optional[Dict[str, Any]] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


# Bulk operation schemas
class BulkGenerationRequest(BaseModel):
    """Schema for bulk crew generation."""
    objectives: List[str] = Field(..., min_length=1, max_length=10, description="List of objectives (1-10 items)")
    shared_requirements: Optional[Dict[str, Any]] = Field(default=None)
    template_id: Optional[int] = Field(default=None)
    llm_provider: Optional[str] = Field(default="openai")


class BulkGenerationResponse(BaseModel):
    """Schema for bulk generation response."""
    total_requests: int
    successful_generations: int
    failed_generations: int
    generation_requests: List[GenerationRequestResponse]
    errors: List[str] 