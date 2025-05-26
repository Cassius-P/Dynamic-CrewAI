"""
CrewAI Memory Integration.

This module provides CrewAI-compatible memory interfaces that wrap the PostgreSQL-backed
memory system to provide seamless integration with CrewAI framework.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..database import get_db
from ..services.memory_service import MemoryService


logger = logging.getLogger(__name__)


class MemoryItem:
    """Simple memory item for CrewAI compatibility."""
    
    def __init__(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.content = content
        self.metadata = metadata or {}


class CrewAIMemoryAdapter:
    """
    CrewAI Memory adapter that integrates with our PostgreSQL-backed memory system.
    
    This adapter provides a simple interface for CrewAI to interact with our comprehensive
    memory system for persistence and advanced features.
    """
    
    def __init__(
        self,
        crew_id: int,  # Using int to match the database schema
        db_session: Optional[Session] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the CrewAI memory adapter.
        
        Args:
            crew_id: ID of the crew this memory belongs to
            db_session: Optional database session
            config: Optional memory configuration
        """
        self.crew_id = crew_id
        self.db_session = db_session or next(get_db())
        self.memory_service = MemoryService(self.db_session)
        self.config = config or {}
        self._initialized = False
        
    def _ensure_initialized(self):
        """Ensure the memory configuration exists."""
        if not self._initialized:
            # Get or create memory configuration
            self.memory_service.get_memory_config(self.crew_id)
            self._initialized = True
    
    def _store_memory(
        self,
        item: MemoryItem,
        memory_type: str = "short_term"
    ) -> bool:
        """Store memory item."""
        self._ensure_initialized()
        
        try:
            content_type = item.metadata.get('content_type', 'text')
            metadata = item.metadata.copy() if item.metadata else {}
            
            # Use the async store_memory method
            result = asyncio.run(self.memory_service.store_memory(
                crew_id=self.crew_id,
                content=item.content,
                memory_type=memory_type,
                content_type=content_type,
                metadata=metadata
            ))
            return bool(result)
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return False
    
    def _retrieve_memory(
        self,
        query: str,
        limit: int = 10,
        memory_type: Optional[str] = None
    ) -> List[MemoryItem]:
        """Retrieve memory items."""
        self._ensure_initialized()
        
        try:
            # Use the async retrieve_memories method
            memory_types = [memory_type] if memory_type else None
            retrieve_result = self.memory_service.retrieve_memories(
                crew_id=self.crew_id,
                query=query,
                memory_types=memory_types,
                limit=limit
            )
            
            # Handle both coroutines and direct results
            if asyncio.iscoroutine(retrieve_result):
                results = asyncio.run(retrieve_result)
            else:
                results = retrieve_result
            
            # Convert our results to CrewAI MemoryItem format
            memory_items = []
            for memory_type_key, search_results in results.items():
                for result in search_results:
                    memory_item = MemoryItem(
                        content=result.item.content,
                        metadata={
                            **(result.item.metadata or {}),
                            'memory_type': memory_type_key,
                            'similarity_score': result.similarity_score,
                            'created_at': result.item.created_at.isoformat() if result.item.created_at else None
                        }
                    )
                    memory_items.append(memory_item)
            
            return memory_items
        except Exception as e:
            logger.error(f"Error retrieving memory: {e}")
            return []
    
    def store(self, item: MemoryItem) -> bool:
        """Store a memory item (CrewAI interface)."""
        return self._store_memory(item)
    
    def retrieve(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """Retrieve memory items (CrewAI interface)."""
        return self._retrieve_memory(query, limit)
    
    def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """Search memory items (alias for retrieve)."""
        return self.retrieve(query, limit)
    
    def store_short_term(self, item: MemoryItem) -> bool:
        """Store in short-term memory."""
        return self._store_memory(item, "short_term")
    
    def store_long_term(self, item: MemoryItem) -> bool:
        """Store in long-term memory."""
        return self._store_memory(item, "long_term")
    
    def store_entity(self, item: MemoryItem) -> bool:
        """Store entity memory."""
        return self._store_memory(item, "entity")
    
    def get_short_term_memory(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """Get short-term memories."""
        return self._retrieve_memory(query, limit, "short_term")
    
    def get_long_term_memory(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """Get long-term memories."""
        return self._retrieve_memory(query, limit, "long_term")
    
    def get_entity_memory(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """Get entity memories."""
        return self._retrieve_memory(query, limit, "entity")
    
    def clear(self, memory_type: Optional[str] = None):
        """Clear memory (CrewAI interface)."""
        try:
            asyncio.run(self.memory_service.clear_all_memories(self.crew_id))
        except Exception as e:
            logger.error(f"Error clearing memory: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        try:
            stats_result = self.memory_service.get_memory_stats(self.crew_id)
            
            # Handle both coroutines and direct results
            if asyncio.iscoroutine(stats_result):
                return asyncio.run(stats_result)
            else:
                return stats_result
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {}


def create_crew_memory(
    crew_id: int,
    config: Optional[Dict[str, Any]] = None
) -> CrewAIMemoryAdapter:
    """
    Factory function to create a CrewAI memory adapter for a crew.
    
    Args:
        crew_id: ID of the crew
        config: Optional memory configuration
        
    Returns:
        CrewAI memory adapter instance
    """
    return CrewAIMemoryAdapter(crew_id=crew_id, config=config)


def create_agent_memory(
    crew_id: int,
    agent_id: int,
    config: Optional[Dict[str, Any]] = None
) -> CrewAIMemoryAdapter:
    """
    Factory function to create agent-specific memory.
    
    Args:
        crew_id: ID of the crew
        agent_id: ID of the agent
        config: Optional memory configuration
        
    Returns:
        Agent memory instance (simplified to use crew memory with agent metadata)
    """
    # For simplicity, we'll use the crew memory but add agent_id to metadata
    adapter = CrewAIMemoryAdapter(crew_id=crew_id, config=config)
    
    # Override store methods to add agent_id to metadata
    original_store = adapter._store_memory
    
    def store_with_agent_id(item: MemoryItem, memory_type: str = "short_term") -> bool:
        if not item.metadata:
            item.metadata = {}
        item.metadata['agent_id'] = agent_id
        return original_store(item, memory_type)
    
    adapter._store_memory = store_with_agent_id
    return adapter 