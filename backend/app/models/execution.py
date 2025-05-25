from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ExecutionStatus(enum.Enum):
    """Execution status enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Execution(Base):
    """Execution model for tracking crew execution instances."""
    
    __tablename__ = "executions"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING)
    inputs = Column(JSON)  # Input parameters for the execution
    outputs = Column(JSON)  # Execution results
    error_message = Column(Text)
    execution_time = Column(Integer)  # Execution time in seconds
    
    # Foreign Keys
    crew_id = Column(Integer, ForeignKey("crews.id"))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    crew = relationship("Crew", back_populates="executions")
