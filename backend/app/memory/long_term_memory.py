"""Long-term memory implementation for persistent knowledge."""

import json
import uuid
from typing import List, Dict, Any, Optional, cast
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, text, func

from app.models.memory import LongTermMemory
from .base_memory import BaseMemory, MemoryItem, SearchResult, EmbeddingService


class LongTermMemoryImpl(BaseMemory):
    """Long-term memory for persistent knowledge with semantic search capabilities."""
    
    def __init__(self, db_session: Session, crew_id: int, config: Optional[Dict[str, Any]] = None):
        """Initialize long-term memory."""
        super().__init__(db_session, crew_id)
        self.config = config or {}
        self.consolidation_threshold = self.config.get("long_term_consolidation_threshold", 0.7)
        self.max_entries = self.config.get("long_term_max_entries", 1000)
        self.embedding_service = EmbeddingService(
            provider=self.config.get("embedding_provider", "openai"),
            model=self.config.get("embedding_model", "text-embedding-3-small")
        )
    
    async def store(
        self, 
        content: str, 
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance_score: float = 0.5,
        source_execution_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        summary: Optional[str] = None
    ) -> str:
        """Store content in long-term memory."""
        try:
            # Generate embedding for the content
            embedding = await self.embedding_service.get_embedding(content)
            
            # Create memory record
            memory = LongTermMemory(
                id=uuid.uuid4(),
                crew_id=self.crew_id,
                content=content,
                summary=summary,
                content_type=content_type,
                embedding=embedding,
                importance_score=importance_score,
                access_count=0,
                last_accessed=None,
                source_execution_id=source_execution_id,
                tags=",".join(tags) if tags else None,
                metadata=json.dumps(metadata) if metadata else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db_session.add(memory)
            self.db_session.commit()
            
            # Cleanup if we exceed max entries
            await self._enforce_max_entries()
            
            return str(memory.id)
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to store long-term memory: {e}")
    
    async def retrieve(
        self, 
        query: str, 
        limit: int = 10,
        similarity_threshold: float = 0.5,
        content_type: Optional[str] = None,
        min_importance: Optional[float] = None,
        tags: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """Retrieve relevant memories using vector similarity search."""
        try:
            # Generate embedding for the query
            query_embedding = await self.embedding_service.get_embedding(query)
            
            # Build base query
            base_query = self.db_session.query(LongTermMemory).filter(
                LongTermMemory.crew_id == self.crew_id,
                LongTermMemory.embedding.isnot(None)
            )
            
            # Add optional filters
            if content_type:
                base_query = base_query.filter(LongTermMemory.content_type == content_type)
            if min_importance:
                base_query = base_query.filter(LongTermMemory.importance_score >= min_importance)
            if tags:
                for tag in tags:
                    base_query = base_query.filter(LongTermMemory.tags.contains(tag))
            
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
                        # Update access tracking using setattr to avoid type checker issues
                        setattr(memory, 'access_count', getattr(memory, 'access_count', 0) + 1)
                        setattr(memory, 'last_accessed', datetime.utcnow())
                        
                        # Cast all model attributes to their runtime types
                        memory_content = cast(str, memory.content)
                        memory_content_type = cast(str, memory.content_type)
                        memory_metadata = cast(Optional[str], memory.metadata)
                        memory_created_at = cast(datetime, memory.created_at)
                        memory_importance_score = cast(Optional[float], memory.importance_score)
                        
                        memory_item = MemoryItem(
                            id=str(memory.id),
                            content=memory_content,
                            content_type=memory_content_type,
                            metadata=json.loads(memory_metadata) if memory_metadata else None,
                            created_at=memory_created_at,
                            relevance_score=memory_importance_score
                        )
                        
                        results.append(SearchResult(
                            item=memory_item,
                            similarity_score=similarity,
                            rank=i + 1
                        ))
            
            # Commit access tracking updates
            self.db_session.commit()
            
            # Sort by combined score (similarity + importance)
            results.sort(
                key=lambda x: (x.similarity_score * 0.7 + (x.item.relevance_score or 0) * 0.3), 
                reverse=True
            )
            return results[:limit]
            
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve long-term memories: {e}")
    
    async def get_by_id(self, memory_id: str) -> Optional[MemoryItem]:
        """Get a specific memory by ID."""
        try:
            memory = self.db_session.query(LongTermMemory).filter(
                LongTermMemory.id == uuid.UUID(memory_id),
                LongTermMemory.crew_id == self.crew_id
            ).first()
            
            if not memory:
                return None
            
            # Update access tracking using setattr to avoid type checker issues
            setattr(memory, 'access_count', getattr(memory, 'access_count', 0) + 1)
            setattr(memory, 'last_accessed', datetime.utcnow())
            self.db_session.commit()
            
            # Cast all model attributes to their runtime types
            memory_content = cast(str, memory.content)
            memory_content_type = cast(str, memory.content_type)
            memory_metadata = cast(Optional[str], memory.metadata)
            memory_created_at = cast(datetime, memory.created_at)
            memory_importance_score = cast(Optional[float], memory.importance_score)
            
            return MemoryItem(
                id=str(memory.id),
                content=memory_content,
                content_type=memory_content_type,
                metadata=json.loads(memory_metadata) if memory_metadata else None,
                created_at=memory_created_at,
                relevance_score=memory_importance_score
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to get long-term memory: {e}")
    
    async def update(
        self, 
        memory_id: str, 
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance_score: Optional[float] = None,
        tags: Optional[List[str]] = None,
        summary: Optional[str] = None
    ) -> bool:
        """Update an existing memory."""
        try:
            memory = self.db_session.query(LongTermMemory).filter(
                LongTermMemory.id == uuid.UUID(memory_id),
                LongTermMemory.crew_id == self.crew_id
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
                setattr(memory, 'metadata', json.dumps(metadata))
            
            if importance_score is not None:
                setattr(memory, 'importance_score', importance_score)
            
            if tags is not None:
                setattr(memory, 'tags', ",".join(tags))
            
            if summary is not None:
                setattr(memory, 'summary', summary)
            
            setattr(memory, 'updated_at', datetime.utcnow())
            
            self.db_session.commit()
            return True
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to update long-term memory: {e}")
    
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        try:
            deleted_count = self.db_session.query(LongTermMemory).filter(
                LongTermMemory.id == uuid.UUID(memory_id),
                LongTermMemory.crew_id == self.crew_id
            ).delete()
            
            self.db_session.commit()
            return deleted_count > 0
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to delete long-term memory: {e}")
    
    async def clear_all(self) -> int:
        """Clear all memories for this crew."""
        try:
            deleted_count = self.db_session.query(LongTermMemory).filter(
                LongTermMemory.crew_id == self.crew_id
            ).delete()
            
            self.db_session.commit()
            return deleted_count
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to clear long-term memories: {e}")
    
    async def get_recent(
        self, 
        limit: int = 10,
        content_type: Optional[str] = None
    ) -> List[MemoryItem]:
        """Get recent memories."""
        try:
            query = self.db_session.query(LongTermMemory).filter(
                LongTermMemory.crew_id == self.crew_id
            )
            
            if content_type:
                query = query.filter(LongTermMemory.content_type == content_type)
            
            memories = query.order_by(desc(LongTermMemory.created_at)).limit(limit).all()
            
            return [
                MemoryItem(
                    id=str(memory.id),
                    content=cast(str, memory.content),
                    content_type=cast(str, memory.content_type),
                    metadata=json.loads(cast(str, memory.metadata)) if cast(Optional[str], memory.metadata) else None,
                    created_at=cast(datetime, memory.created_at),
                    relevance_score=cast(Optional[float], memory.importance_score)
                )
                for memory in memories
            ]
            
        except Exception as e:
            raise RuntimeError(f"Failed to get recent long-term memories: {e}")
    
    async def cleanup(self) -> int:
        """Remove low-importance memories and enforce max entries."""
        try:
            # Remove memories with very low importance and no recent access
            cutoff_date = datetime.utcnow().replace(day=datetime.utcnow().day - 30)  # 30 days ago
            
            low_importance_count = self.db_session.query(LongTermMemory).filter(
                LongTermMemory.crew_id == self.crew_id,
                LongTermMemory.importance_score < 0.3,
                LongTermMemory.access_count == 0,
                LongTermMemory.created_at < cutoff_date
            ).delete()
            
            # Enforce max entries
            max_entries_count = await self._enforce_max_entries()
            
            self.db_session.commit()
            return low_importance_count + max_entries_count
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to cleanup long-term memories: {e}")
    
    async def _enforce_max_entries(self) -> int:
        """Enforce maximum number of entries by removing least important."""
        try:
            # Count current entries
            current_count = self.db_session.query(LongTermMemory).filter(
                LongTermMemory.crew_id == self.crew_id
            ).count()
            
            if current_count <= self.max_entries:
                return 0
            
            # Get least important entries to remove
            entries_to_remove = current_count - self.max_entries
            least_important = self.db_session.query(LongTermMemory).filter(
                LongTermMemory.crew_id == self.crew_id
            ).order_by(
                LongTermMemory.importance_score,
                LongTermMemory.access_count,
                LongTermMemory.created_at
            ).limit(entries_to_remove).all()
            
            # Delete least important entries
            for memory in least_important:
                self.db_session.delete(memory)
            
            return entries_to_remove
            
        except Exception as e:
            raise RuntimeError(f"Failed to enforce max entries: {e}")
    
    async def consolidate_from_short_term(self, short_term_memories: List[MemoryItem]) -> int:
        """Consolidate important short-term memories into long-term storage."""
        try:
            consolidated_count = 0
            
            for memory in short_term_memories:
                # Only consolidate if importance score meets threshold
                if (memory.relevance_score or 0) >= self.consolidation_threshold:
                    # Check if similar memory already exists
                    existing = await self.retrieve(
                        memory.content, 
                        limit=1, 
                        similarity_threshold=0.9
                    )
                    
                    if not existing:
                        # Store as new long-term memory
                        await self.store(
                            content=memory.content,
                            content_type=memory.content_type,
                            metadata=memory.metadata,
                            importance_score=memory.relevance_score or 0.5,
                            summary=memory.content[:200] + "..." if len(memory.content) > 200 else memory.content
                        )
                        consolidated_count += 1
                    else:
                        # Update existing memory's importance
                        existing_memory = existing[0]
                        new_importance = min(1.0, (existing_memory.item.relevance_score or 0) + 0.1)
                        await self.update(
                            existing_memory.item.id,
                            importance_score=new_importance
                        )
            
            return consolidated_count
            
        except Exception as e:
            raise RuntimeError(f"Failed to consolidate memories: {e}")
    
    async def get_insights(self, limit: int = 10) -> List[MemoryItem]:
        """Get high-importance insights and learnings."""
        try:
            memories = self.db_session.query(LongTermMemory).filter(
                LongTermMemory.crew_id == self.crew_id,
                LongTermMemory.content_type.in_(["insight", "learning", "pattern"]),
                LongTermMemory.importance_score >= 0.7
            ).order_by(
                desc(LongTermMemory.importance_score),
                desc(LongTermMemory.access_count)
            ).limit(limit).all()
            
            return [
                MemoryItem(
                    id=str(memory.id),
                    content=cast(str, memory.content),
                    content_type=cast(str, memory.content_type),
                    metadata=json.loads(cast(str, memory.metadata)) if cast(Optional[str], memory.metadata) else None,
                    created_at=cast(datetime, memory.created_at),
                    relevance_score=cast(Optional[float], memory.importance_score)
                )
                for memory in memories
            ]
            
        except Exception as e:
            raise RuntimeError(f"Failed to get insights: {e}")
    
    async def get_by_tags(self, tags: List[str], limit: int = 10) -> List[MemoryItem]:
        """Get memories by tags."""
        try:
            query = self.db_session.query(LongTermMemory).filter(
                LongTermMemory.crew_id == self.crew_id
            )
            
            for tag in tags:
                query = query.filter(LongTermMemory.tags.contains(tag))
            
            memories = query.order_by(
                desc(LongTermMemory.importance_score)
            ).limit(limit).all()
            
            return [
                MemoryItem(
                    id=str(memory.id),
                    content=cast(str, memory.content),
                    content_type=cast(str, memory.content_type),
                    metadata=json.loads(cast(str, memory.metadata)) if cast(Optional[str], memory.metadata) else None,
                    created_at=cast(datetime, memory.created_at),
                    relevance_score=cast(Optional[float], memory.importance_score)
                )
                for memory in memories
            ]
            
        except Exception as e:
            raise RuntimeError(f"Failed to get memories by tags: {e}") 