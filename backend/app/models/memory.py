from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from pgvector.sqlalchemy import Vector
from app.database import Base


class ShortTermMemory(Base):
    """Short-term memory for conversation context with vector embeddings."""
    __tablename__ = "short_term_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crew_id = Column(Integer, ForeignKey("crews.id"), nullable=False)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=True)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=False)  # task_input, task_output, agent_message, etc.
    embedding = Column(Vector(1536), nullable=True)  # OpenAI text-embedding-3-small dimensions
    meta_data = Column(Text, nullable=True)  # JSON metadata about the memory
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    relevance_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # For automatic cleanup

    # Relationships
    crew = relationship("Crew", back_populates="short_term_memories")
    execution = relationship("Execution", back_populates="short_term_memories")
    agent = relationship("Agent", back_populates="short_term_memories")


class LongTermMemory(Base):
    """Long-term memory for persistent knowledge with semantic search capabilities."""
    __tablename__ = "long_term_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crew_id = Column(Integer, ForeignKey("crews.id"), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)  # Condensed version for quick access
    content_type = Column(String(50), nullable=False)  # insight, learning, pattern, solution
    embedding = Column(Vector(1536), nullable=True)  # Vector embeddings for semantic search
    importance_score = Column(Float, nullable=False, default=0.5)  # 0.0 to 1.0
    access_count = Column(Integer, default=0)  # Track usage frequency
    last_accessed = Column(DateTime, nullable=True)
    source_execution_id = Column(Integer, ForeignKey("executions.id"), nullable=True)
    tags = Column(String(500), nullable=True)  # Comma-separated tags for categorization
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    crew = relationship("Crew", back_populates="long_term_memories")
    source_execution = relationship("Execution", back_populates="long_term_memories")


class EntityMemory(Base):
    """Entity memory for structured entity information with vector relationships."""
    __tablename__ = "entity_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crew_id = Column(Integer, ForeignKey("crews.id"), nullable=False)
    entity_name = Column(String(255), nullable=False)
    entity_type = Column(String(100), nullable=False)  # person, organization, concept, location, etc.
    description = Column(Text, nullable=True)
    attributes = Column(Text, nullable=True)  # JSON attributes about the entity
    embedding = Column(Vector(1536), nullable=True)  # Vector for entity similarity
    confidence_score = Column(Float, nullable=False, default=0.5)  # Entity recognition confidence
    first_mentioned = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    mention_count = Column(Integer, default=1)  # Track frequency of mentions

    # Relationships
    crew = relationship("Crew", back_populates="entity_memories")
    # Self-referential relationship for entity connections
    relationships_as_source = relationship(
        "EntityRelationship", 
        foreign_keys="EntityRelationship.source_entity_id",
        back_populates="source_entity"
    )
    relationships_as_target = relationship(
        "EntityRelationship", 
        foreign_keys="EntityRelationship.target_entity_id",
        back_populates="target_entity"
    )


class EntityRelationship(Base):
    """Relationships between entities with vector-based similarity."""
    __tablename__ = "entity_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_entity_id = Column(UUID(as_uuid=True), ForeignKey("entity_memories.id"), nullable=False)
    target_entity_id = Column(UUID(as_uuid=True), ForeignKey("entity_memories.id"), nullable=False)
    relationship_type = Column(String(100), nullable=False)  # works_for, located_in, related_to, etc.
    strength = Column(Float, nullable=False, default=0.5)  # Relationship strength 0.0 to 1.0
    context = Column(Text, nullable=True)  # Context where relationship was discovered
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    source_entity = relationship("EntityMemory", foreign_keys=[source_entity_id], back_populates="relationships_as_source")
    target_entity = relationship("EntityMemory", foreign_keys=[target_entity_id], back_populates="relationships_as_target")


class MemoryConfiguration(Base):
    """Memory configuration settings per crew."""
    __tablename__ = "memory_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crew_id = Column(Integer, ForeignKey("crews.id"), nullable=False, unique=True)
    
    # Short-term memory settings
    short_term_retention_hours = Column(Integer, default=24)  # How long to keep short-term memories
    short_term_max_entries = Column(Integer, default=100)  # Maximum short-term memories
    
    # Long-term memory settings
    long_term_consolidation_threshold = Column(Float, default=0.7)  # Importance score threshold for consolidation
    long_term_max_entries = Column(Integer, default=1000)  # Maximum long-term memories
    
    # Entity memory settings
    entity_confidence_threshold = Column(Float, default=0.6)  # Minimum confidence to store entity
    entity_similarity_threshold = Column(Float, default=0.8)  # Threshold for entity deduplication
    
    # General settings
    embedding_provider = Column(String(50), default="openai")  # openai, azure, etc.
    embedding_model = Column(String(100), default="text-embedding-3-small")
    cleanup_enabled = Column(Boolean, default=True)
    cleanup_interval_hours = Column(Integer, default=24)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    crew = relationship("Crew", back_populates="memory_configuration")


class MemoryCleanupLog(Base):
    """Track memory cleanup operations."""
    __tablename__ = "memory_cleanup_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crew_id = Column(Integer, ForeignKey("crews.id"), nullable=True)
    cleanup_type = Column(String(50), nullable=False)  # short_term, long_term, entity, full
    entries_removed = Column(Integer, default=0)
    cleanup_reason = Column(String(200), nullable=True)  # retention_expired, max_entries_exceeded, manual
    execution_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    crew = relationship("Crew", back_populates="memory_cleanup_logs") 