"""Mock memory implementation for testing and basic functionality."""

import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .base_memory import BaseMemory, MemoryItem, SearchResult


class MockEmbeddingService:
    """Mock embedding service for testing."""
    
    async def get_embedding(self, text: str) -> List[float]:
        """Return a mock embedding."""
        # Simple hash-based mock embedding
        hash_val = hash(text) % 1000
        return [float(hash_val % 100) / 100.0] * 1536
    
    async def get_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Return mock similarity score."""
        # Simple similarity based on first element
        if not embedding1 or not embedding2:
            return 0.0
        diff = abs(embedding1[0] - embedding2[0])
        return max(0.0, 1.0 - diff)


class MockMemoryImpl(BaseMemory):
    """Mock memory implementation for testing."""
    
    def __init__(self, db_session, crew_id: int, config: Optional[Dict[str, Any]] = None):
        """Initialize mock memory."""
        super().__init__(db_session, crew_id)
        self.config = config or {}
        self.embedding_service = MockEmbeddingService()
        self._memories: Dict[str, Dict[str, Any]] = {}
    
    async def store(
        self, 
        content: str, 
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: Optional[int] = None,
        execution_id: Optional[int] = None,
        relevance_score: Optional[float] = None
    ) -> str:
        """Store content in mock memory."""
        memory_id = str(uuid.uuid4())
        embedding = await self.embedding_service.get_embedding(content)
        
        self._memories[memory_id] = {
            'id': memory_id,
            'crew_id': self.crew_id,
            'content': content,
            'content_type': content_type,
            'metadata': metadata or {},
            'agent_id': agent_id,
            'execution_id': execution_id,
            'relevance_score': relevance_score,
            'embedding': embedding,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(hours=24)
        }
        
        return memory_id
    
    async def retrieve(
        self, 
        query: str, 
        limit: int = 10,
        similarity_threshold: float = 0.5,
        content_type: Optional[str] = None,
        agent_id: Optional[int] = None
    ) -> List[SearchResult]:
        """Retrieve relevant memories using mock similarity search."""
        query_embedding = await self.embedding_service.get_embedding(query)
        results = []
        
        for memory_data in self._memories.values():
            if memory_data['crew_id'] != self.crew_id:
                continue
                
            if content_type and memory_data['content_type'] != content_type:
                continue
                
            if agent_id and memory_data['agent_id'] != agent_id:
                continue
            
            similarity = await self.embedding_service.get_similarity(
                query_embedding, memory_data['embedding']
            )
            
            if similarity >= similarity_threshold:
                memory_item = MemoryItem(
                    id=memory_data['id'],
                    content=memory_data['content'],
                    content_type=memory_data['content_type'],
                    metadata=memory_data['metadata'],
                    created_at=memory_data['created_at'],
                    relevance_score=memory_data['relevance_score']
                )
                
                results.append(SearchResult(
                    item=memory_item,
                    similarity_score=similarity,
                    rank=len(results) + 1
                ))
        
        # Sort by similarity score and limit results
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:limit]
    
    async def get_by_id(self, memory_id: str) -> Optional[MemoryItem]:
        """Get a specific memory by ID."""
        memory_data = self._memories.get(memory_id)
        if not memory_data or memory_data['crew_id'] != self.crew_id:
            return None
        
        return MemoryItem(
            id=memory_data['id'],
            content=memory_data['content'],
            content_type=memory_data['content_type'],
            metadata=memory_data['metadata'],
            created_at=memory_data['created_at'],
            relevance_score=memory_data['relevance_score']
        )
    
    async def update(
        self, 
        memory_id: str, 
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        relevance_score: Optional[float] = None
    ) -> bool:
        """Update an existing memory."""
        if memory_id not in self._memories:
            return False
            
        memory_data = self._memories[memory_id]
        if memory_data['crew_id'] != self.crew_id:
            return False
        
        if content is not None:
            memory_data['content'] = content
            memory_data['embedding'] = await self.embedding_service.get_embedding(content)
        
        if metadata is not None:
            memory_data['metadata'] = metadata
        
        if relevance_score is not None:
            memory_data['relevance_score'] = relevance_score
        
        return True
    
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        if memory_id in self._memories and self._memories[memory_id]['crew_id'] == self.crew_id:
            del self._memories[memory_id]
            return True
        return False
    
    async def clear_all(self) -> int:
        """Clear all memories for this crew."""
        to_delete = [
            mid for mid, data in self._memories.items() 
            if data['crew_id'] == self.crew_id
        ]
        for mid in to_delete:
            del self._memories[mid]
        return len(to_delete)
    
    async def get_recent(
        self, 
        limit: int = 10,
        content_type: Optional[str] = None
    ) -> List[MemoryItem]:
        """Get recent memories."""
        memories = [
            data for data in self._memories.values()
            if data['crew_id'] == self.crew_id and 
            (content_type is None or data['content_type'] == content_type)
        ]
        
        # Sort by created_at descending
        memories.sort(key=lambda x: x['created_at'], reverse=True)
        
        return [
            MemoryItem(
                id=data['id'],
                content=data['content'],
                content_type=data['content_type'],
                metadata=data['metadata'],
                created_at=data['created_at'],
                relevance_score=data['relevance_score']
            )
            for data in memories[:limit]
        ]
    
    async def cleanup(self) -> int:
        """Remove expired memories."""
        now = datetime.utcnow()
        to_delete = [
            mid for mid, data in self._memories.items()
            if data['crew_id'] == self.crew_id and 
            data.get('expires_at', now) < now
        ]
        for mid in to_delete:
            del self._memories[mid]
        return len(to_delete)
    
    async def get_conversation_context(
        self, 
        limit: int = 20,
        execution_id: Optional[int] = None
    ) -> List[MemoryItem]:
        """Get conversation context for current or specific execution."""
        memories = [
            data for data in self._memories.values()
            if (data['crew_id'] == self.crew_id and 
                data['content_type'] in ["task_input", "task_output", "agent_message"] and
                (execution_id is None or data.get('execution_id') == execution_id))
        ]
        
        # Sort by created_at descending
        memories.sort(key=lambda x: x['created_at'], reverse=True)
        
        result = [
            MemoryItem(
                id=data['id'],
                content=data['content'],
                content_type=data['content_type'],
                metadata=data['metadata'],
                created_at=data['created_at'],
                relevance_score=data['relevance_score']
            )
            for data in memories[:limit]
        ]
        
        # Return in chronological order
        return list(reversed(result))
    
    async def get_insights(self, limit: int = 10) -> List[MemoryItem]:
        """Get high-importance insights."""
        memories = [
            data for data in self._memories.values()
            if (data['crew_id'] == self.crew_id and 
                data.get('relevance_score', 0) > 0.7)
        ]
        
        # Sort by relevance score descending
        memories.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return [
            MemoryItem(
                id=data['id'],
                content=data['content'],
                content_type=data['content_type'],
                metadata=data['metadata'],
                created_at=data['created_at'],
                relevance_score=data['relevance_score']
            )
            for data in memories[:limit]
        ]
    
    async def get_by_type(self, entity_type: str, limit: int = 10) -> List[MemoryItem]:
        """Get entities by type."""
        memories = [
            data for data in self._memories.values()
            if (data['crew_id'] == self.crew_id and 
                data.get('metadata', {}).get('entity_type') == entity_type)
        ]
        
        return [
            MemoryItem(
                id=data['id'],
                content=data['content'],
                content_type=data['content_type'],
                metadata=data['metadata'],
                created_at=data['created_at'],
                relevance_score=data['relevance_score']
            )
            for data in memories[:limit]
        ]
    
    async def add_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        strength: float = 0.5,
        context: Optional[str] = None
    ) -> str:
        """Add entity relationship."""
        relationship_id = str(uuid.uuid4())
        # For mock, just store minimal relationship data
        return relationship_id
    
    async def get_relationships(
        self,
        entity_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get entity relationships."""
        # For mock, return empty list
        return []
    
    async def consolidate_from_short_term(self, importance_threshold: float = 0.7) -> int:
        """Consolidate memories from short-term to long-term."""
        # For mock, return 0
        return 0 