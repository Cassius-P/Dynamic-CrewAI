from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Crew(Base):
    """Crew model for storing crew configurations."""
    
    __tablename__ = "crews"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    process = Column(String(50), default="sequential")  # sequential, hierarchical
    verbose = Column(Boolean, default=False)
    memory = Column(Boolean, default=False)
    max_rpm = Column(Integer)
    max_execution_time = Column(Integer)
    config = Column(JSON)  # Additional configuration options
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    agents = relationship("Agent", back_populates="crew", cascade="all, delete-orphan")
    executions = relationship("Execution", back_populates="crew")
    
    # Memory relationships
    short_term_memories = relationship("ShortTermMemory", back_populates="crew", cascade="all, delete-orphan")
    long_term_memories = relationship("LongTermMemory", back_populates="crew", cascade="all, delete-orphan")
    entity_memories = relationship("EntityMemory", back_populates="crew", cascade="all, delete-orphan")
    memory_configuration = relationship("MemoryConfiguration", back_populates="crew", uselist=False, cascade="all, delete-orphan")
    memory_cleanup_logs = relationship("MemoryCleanupLog", back_populates="crew", cascade="all, delete-orphan")
