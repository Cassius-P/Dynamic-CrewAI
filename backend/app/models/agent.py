from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Agent(Base):
    """Agent model for storing agent configurations."""
    
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(255), nullable=False)
    goal = Column(Text, nullable=False)
    backstory = Column(Text, nullable=False)
    verbose = Column(Boolean, default=False)
    allow_delegation = Column(Boolean, default=False)
    max_iter = Column(Integer)
    max_execution_time = Column(Integer)
    tools = Column(JSON)  # List of tool names/configurations
    llm_config = Column(JSON)  # LLM configuration
    
    # Manager agent specific fields
    manager_type = Column(String(50))  # hierarchical, collaborative, sequential
    can_generate_tasks = Column(Boolean, default=False)
    manager_config = Column(JSON)  # Manager-specific configuration
    
    # Foreign Keys
    crew_id = Column(Integer, ForeignKey("crews.id"))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    crew = relationship("Crew", back_populates="agents")
    short_term_memories = relationship("ShortTermMemory", back_populates="agent")
