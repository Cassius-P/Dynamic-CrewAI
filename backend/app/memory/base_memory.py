"""Base memory interface for CrewAI memory implementations."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.orm import Session


class MemoryItem(BaseModel):
    """Base memory item structure."""
    id: str
    content: str
    content_type: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    relevance_score: Optional[float] = None


class SearchResult(BaseModel):
    """Memory search result."""
    item: MemoryItem
    similarity_score: float
    rank: int


class BaseMemory(ABC):
    """Abstract base class for memory implementations."""
    
    def __init__(self, db_session: Session, crew_id: int):
        """Initialize memory with database session and crew ID."""
        self.db_session = db_session
        self.crew_id = crew_id
    
    @abstractmethod
    async def store(
        self, 
        content: str, 
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Store content in memory and return the memory ID."""
        pass
    
    @abstractmethod
    async def retrieve(
        self, 
        query: str, 
        limit: int = 10,
        similarity_threshold: float = 0.5,
        **kwargs
    ) -> List[SearchResult]:
        """Retrieve relevant memories based on query."""
        pass
    
    @abstractmethod
    async def get_by_id(self, memory_id: str) -> Optional[MemoryItem]:
        """Get a specific memory by ID."""
        pass
    
    @abstractmethod
    async def update(
        self, 
        memory_id: str, 
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> bool:
        """Update an existing memory."""
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        pass
    
    @abstractmethod
    async def clear_all(self) -> int:
        """Clear all memories for this crew. Returns count of deleted items."""
        pass
    
    @abstractmethod
    async def get_recent(
        self, 
        limit: int = 10,
        content_type: Optional[str] = None
    ) -> List[MemoryItem]:
        """Get recent memories."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> int:
        """Perform cleanup operations. Returns count of cleaned items."""
        pass


class EmbeddingService:
    """Service for generating embeddings."""
    
    def __init__(self, provider: str = "openai", model: str = "text-embedding-3-small"):
        """Initialize embedding service."""
        self.provider = provider
        self.model = model
        self._client = None
    
    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if self.provider == "openai":
            return await self._get_openai_embedding(text)
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")
    
    async def _get_openai_embedding(self, text: str) -> List[float]:
        """Get OpenAI embedding."""
        try:
            from openai import AsyncOpenAI
            
            if not self._client:
                self._client = AsyncOpenAI()
            
            response = await self._client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {e}")
    
    async def get_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        import numpy as np
        
        # Convert to numpy arrays
        a = np.array(embedding1)
        b = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b) 