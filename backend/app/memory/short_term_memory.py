"""Short-term memory implementation for conversation context."""

import json
import uuid
from typing import List, Dict, Any, Optional, cast
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, text

from app.models.memory import ShortTermMemory
from .base_memory import BaseMemory, MemoryItem, SearchResult, EmbeddingService


class ShortTermMemoryImpl(BaseMemory):
    """Short-term memory for conversation context with vector embeddings."""
    
    def __init__(self, db_session: Session, crew_id: int, config: Optional[Dict[str, Any]] = None):
        """Initialize short-term memory."""
        super().__init__(db_session, crew_id)
        self.config = config or {}
        self.retention_hours = self.config.get("short_term_retention_hours", 24)
        self.max_entries = self.config.get("short_term_max_entries", 100)
        self.embedding_service = EmbeddingService(
            provider=self.config.get("embedding_provider", "openai"),
            model=self.config.get("embedding_model", "text-embedding-3-small")
        )
    
    async def store(
        self, 
        content: str, 
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: Optional[int] = None,
        execution_id: Optional[int] = None,
        relevance_score: Optional[float] = None
    ) -> str:
        """Store content in short-term memory."""
        try:
            # Generate embedding for the content
            embedding = await self.embedding_service.get_embedding(content)
            
            # Create memory record
            memory = ShortTermMemory(
                id=uuid.uuid4(),
                crew_id=self.crew_id,
                execution_id=execution_id,
                content=content,
                content_type=content_type,
                embedding=embedding,
                meta_data=json.dumps(metadata) if metadata else None,
                agent_id=agent_id,
                relevance_score=relevance_score,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=self.retention_hours)
            )
            
            self.db_session.add(memory)
            self.db_session.commit()
            
            # Cleanup if we exceed max entries
            await self._enforce_max_entries()
            
            return str(memory.id)
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to store short-term memory: {e}")
    
    async def retrieve(
        self, 
        query: str, 
        limit: int = 10,
        similarity_threshold: float = 0.5,
        content_type: Optional[str] = None,
        agent_id: Optional[int] = None
    ) -> List[SearchResult]:
        """Retrieve relevant memories using vector similarity search."""
        try:
            # Generate embedding for the query
            query_embedding = await self.embedding_service.get_embedding(query)
            
            # Build base query
            base_query = self.db_session.query(ShortTermMemory).filter(
                ShortTermMemory.crew_id == self.crew_id,
                ShortTermMemory.embedding.isnot(None)
            )
            
            # Add optional filters
            if content_type:
                base_query = base_query.filter(ShortTermMemory.content_type == content_type)
            if agent_id:
                base_query = base_query.filter(ShortTermMemory.agent_id == agent_id)
            
            # Use pgvector cosine similarity search
            similarity_query = base_query.order_by(
                text(f"embedding <=> '{query_embedding}'")
            ).limit(limit * 2)  # Get more results to filter by threshold
            
            memories = similarity_query.all()
            
            # Calculate similarities and filter by threshold
            results = []
            for i, memory in enumerate(memories):
                # Cast the embedding attribute to get the actual runtime value
                memory_embedding = cast(List[float], memory.embedding)
                if memory_embedding:
                    similarity = await self.embedding_service.get_similarity(
                        query_embedding, memory_embedding
                    )
                    
                    if similarity >= similarity_threshold:
                        # Cast all model attributes to their runtime types
                        memory_content = cast(str, memory.content)
                        memory_content_type = cast(str, memory.content_type)
                        memory_meta_data = cast(Optional[str], memory.meta_data)
                        memory_created_at = cast(datetime, memory.created_at)
                        memory_relevance_score = cast(Optional[float], memory.relevance_score)
                        
                        memory_item = MemoryItem(
                            id=str(memory.id),
                            content=memory_content,
                            content_type=memory_content_type,
                            metadata=json.loads(memory_meta_data) if memory_meta_data else None,
                            created_at=memory_created_at,
                            relevance_score=memory_relevance_score
                        )
                        
                        results.append(SearchResult(
                            item=memory_item,
                            similarity_score=similarity,
                            rank=i + 1
                        ))
            
            # Sort by similarity score and limit results
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            return results[:limit]
            
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve short-term memories: {e}")
    
    async def get_by_id(self, memory_id: str) -> Optional[MemoryItem]:
        """Get a specific memory by ID."""
        try:
            memory = self.db_session.query(ShortTermMemory).filter(
                ShortTermMemory.id == uuid.UUID(memory_id),
                ShortTermMemory.crew_id == self.crew_id
            ).first()
            
            if not memory:
                return None
            
            # Cast all model attributes to their runtime types
            memory_content = cast(str, memory.content)
            memory_content_type = cast(str, memory.content_type)
            memory_meta_data = cast(Optional[str], memory.meta_data)
            memory_created_at = cast(datetime, memory.created_at)
            memory_relevance_score = cast(Optional[float], memory.relevance_score)
            
            return MemoryItem(
                id=str(memory.id),
                content=memory_content,
                content_type=memory_content_type,
                metadata=json.loads(memory_meta_data) if memory_meta_data else None,
                created_at=memory_created_at,
                relevance_score=memory_relevance_score
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to get short-term memory: {e}")
    
    async def update(
        self, 
        memory_id: str, 
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        relevance_score: Optional[float] = None
    ) -> bool:
        """Update an existing memory."""
        try:
            memory = self.db_session.query(ShortTermMemory).filter(
                ShortTermMemory.id == uuid.UUID(memory_id),
                ShortTermMemory.crew_id == self.crew_id
            ).first()
            
            if not memory:
                return False
            
            # Update fields using setattr to avoid type checker issues
            if content is not None:
                setattr(memory, 'content', content)
                # Regenerate embedding if content changed
                embedding = await self.embedding_service.get_embedding(content)
                setattr(memory, 'embedding', embedding)
            
            if metadata is not None:
                setattr(memory, 'meta_data', json.dumps(metadata))
            
            if relevance_score is not None:
                setattr(memory, 'relevance_score', relevance_score)
            
            self.db_session.commit()
            return True
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to update short-term memory: {e}")
    
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        try:
            deleted_count = self.db_session.query(ShortTermMemory).filter(
                ShortTermMemory.id == uuid.UUID(memory_id),
                ShortTermMemory.crew_id == self.crew_id
            ).delete()
            
            self.db_session.commit()
            return deleted_count > 0
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to delete short-term memory: {e}")
    
    async def clear_all(self) -> int:
        """Clear all memories for this crew."""
        try:
            deleted_count = self.db_session.query(ShortTermMemory).filter(
                ShortTermMemory.crew_id == self.crew_id
            ).delete()
            
            self.db_session.commit()
            return deleted_count
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to clear short-term memories: {e}")
    
    async def get_recent(
        self, 
        limit: int = 10,
        content_type: Optional[str] = None
    ) -> List[MemoryItem]:
        """Get recent memories."""
        try:
            query = self.db_session.query(ShortTermMemory).filter(
                ShortTermMemory.crew_id == self.crew_id
            )
            
            if content_type:
                query = query.filter(ShortTermMemory.content_type == content_type)
            
            memories = query.order_by(desc(ShortTermMemory.created_at)).limit(limit).all()
            
            return [
                MemoryItem(
                    id=str(memory.id),
                    content=cast(str, memory.content),
                    content_type=cast(str, memory.content_type),
                    metadata=json.loads(cast(str, memory.meta_data)) if cast(Optional[str], memory.meta_data) else None,
                    created_at=cast(datetime, memory.created_at),
                    relevance_score=cast(Optional[float], memory.relevance_score)
                )
                for memory in memories
            ]
            
        except Exception as e:
            raise RuntimeError(f"Failed to get recent short-term memories: {e}")
    
    async def cleanup(self) -> int:
        """Remove expired memories and enforce max entries."""
        try:
            # Remove expired memories
            expired_count = self.db_session.query(ShortTermMemory).filter(
                ShortTermMemory.crew_id == self.crew_id,
                ShortTermMemory.expires_at < datetime.utcnow()
            ).delete()
            
            # Enforce max entries
            max_entries_count = await self._enforce_max_entries()
            
            self.db_session.commit()
            return expired_count + max_entries_count
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to cleanup short-term memories: {e}")
    
    async def _enforce_max_entries(self) -> int:
        """Enforce maximum number of entries by removing oldest."""
        try:
            # Count current entries
            current_count = self.db_session.query(ShortTermMemory).filter(
                ShortTermMemory.crew_id == self.crew_id
            ).count()
            
            if current_count <= self.max_entries:
                return 0
            
            # Get oldest entries to remove
            entries_to_remove = current_count - self.max_entries
            oldest_memories = self.db_session.query(ShortTermMemory).filter(
                ShortTermMemory.crew_id == self.crew_id
            ).order_by(ShortTermMemory.created_at).limit(entries_to_remove).all()
            
            # Delete oldest entries
            for memory in oldest_memories:
                self.db_session.delete(memory)
            
            return entries_to_remove
            
        except Exception as e:
            raise RuntimeError(f"Failed to enforce max entries: {e}")
    
    async def get_conversation_context(
        self, 
        limit: int = 20,
        execution_id: Optional[int] = None
    ) -> List[MemoryItem]:
        """Get conversation context for current or specific execution."""
        try:
            query = self.db_session.query(ShortTermMemory).filter(
                ShortTermMemory.crew_id == self.crew_id,
                ShortTermMemory.content_type.in_(["task_input", "task_output", "agent_message"])
            )
            
            if execution_id:
                query = query.filter(ShortTermMemory.execution_id == execution_id)
            
            memories = query.order_by(desc(ShortTermMemory.created_at)).limit(limit).all()
            
            return [
                MemoryItem(
                    id=str(memory.id),
                    content=cast(str, memory.content),
                    content_type=cast(str, memory.content_type),
                    metadata=json.loads(cast(str, memory.meta_data)) if cast(Optional[str], memory.meta_data) else None,
                    created_at=cast(datetime, memory.created_at),
                    relevance_score=cast(Optional[float], memory.relevance_score)
                )
                for memory in reversed(memories)  # Return in chronological order
            ]
            
        except Exception as e:
            raise RuntimeError(f"Failed to get conversation context: {e}") 