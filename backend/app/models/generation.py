"""Models for dynamic crew generation functionality."""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class DynamicCrewTemplate(Base):
    """Template for dynamic crew generation patterns."""
    
    __tablename__ = "dynamic_crew_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    template_type = Column(String(100))  # task_based, domain_specific, etc.
    template_config = Column(JSON)  # Template configuration and patterns
    success_rate = Column(Float, default=0.0)  # Success rate of crews generated from this template
    usage_count = Column(Integer, default=0)  # Number of times template was used
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    generation_requests = relationship("GenerationRequest", back_populates="template")


class GenerationRequest(Base):
    """Request for dynamic crew generation."""
    
    __tablename__ = "generation_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    objective = Column(Text, nullable=False)  # High-level objective for the crew
    requirements = Column(JSON)  # Specific requirements and constraints
    generated_crew_id = Column(Integer, ForeignKey("crews.id"))
    template_id = Column(Integer, ForeignKey("dynamic_crew_templates.id"))
    llm_provider = Column(String(100))  # LLM provider used for generation
    generation_status = Column(String(50), default="pending")  # pending, generating, completed, failed
    generation_result = Column(JSON)  # Generated crew configuration
    validation_result = Column(JSON)  # Validation results
    optimization_applied = Column(Boolean, default=False)
    generation_time_seconds = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    template = relationship("DynamicCrewTemplate", back_populates="generation_requests")
    optimizations = relationship("CrewOptimization", back_populates="generation_request")


class CrewOptimization(Base):
    """Optimization history and results for crews."""
    
    __tablename__ = "crew_optimizations"
    
    id = Column(Integer, primary_key=True, index=True)
    crew_id = Column(Integer, ForeignKey("crews.id"))
    generation_request_id = Column(Integer, ForeignKey("generation_requests.id"))
    optimization_type = Column(String(100))  # performance, cost, speed, quality
    original_config = Column(JSON)  # Original crew configuration
    optimized_config = Column(JSON)  # Optimized crew configuration
    optimization_score = Column(Float)  # Optimization improvement score
    optimization_metrics = Column(JSON)  # Detailed optimization metrics
    applied = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    applied_at = Column(DateTime(timezone=True))
    
    # Relationships
    generation_request = relationship("GenerationRequest", back_populates="optimizations")


class AgentCapability(Base):
    """Agent skill and capability definitions."""
    
    __tablename__ = "agent_capabilities"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    capability_name = Column(String(255), nullable=False)
    capability_type = Column(String(100))  # skill, tool, domain_knowledge, etc.
    proficiency_level = Column(Integer, default=1)  # 1-10 scale
    capability_description = Column(Text)
    capability_metadata = Column(JSON)  # Additional capability information
    verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TaskRequirement(Base):
    """Task requirement specifications."""
    
    __tablename__ = "task_requirements"
    
    id = Column(Integer, primary_key=True, index=True)
    generation_request_id = Column(Integer, ForeignKey("generation_requests.id"))
    requirement_type = Column(String(100))  # skill, tool, resource, constraint
    requirement_name = Column(String(255), nullable=False)
    requirement_value = Column(String(500))
    priority = Column(Integer, default=1)  # 1=low, 5=critical
    requirement_metadata = Column(JSON)
    satisfied = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GenerationMetrics(Base):
    """Metrics for dynamic generation performance."""
    
    __tablename__ = "generation_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    generation_request_id = Column(Integer, ForeignKey("generation_requests.id"))
    metric_name = Column(String(255), nullable=False)
    metric_value = Column(Float)
    metric_unit = Column(String(50))
    metric_category = Column(String(100))  # performance, quality, cost, time
    metric_metadata = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 