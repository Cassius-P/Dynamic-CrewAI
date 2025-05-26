"""Entity memory implementation for structured entity information."""

import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, text, func

from app.models.memory import EntityMemory, EntityRelationship
from .base_memory import BaseMemory, MemoryItem, SearchResult, EmbeddingService


class EntityItem(MemoryItem):
    """Extended memory item for entities."""
    entity_name: str
    entity_type: str
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    confidence_score: float
    mention_count: int
    first_mentioned: datetime
    last_updated: datetime


class EntityMemoryImpl(BaseMemory):
    """Entity memory for structured entity information with vector relationships."""
    
    def __init__(self, db_session: Session, crew_id: int, config: Optional[Dict[str, Any]] = None):
        """Initialize entity memory."""
        super().__init__(db_session, crew_id)
        self.config = config or {}
        self.confidence_threshold = self.config.get("entity_confidence_threshold", 0.6)
        self.similarity_threshold = self.config.get("entity_similarity_threshold", 0.8)
        self.embedding_service = EmbeddingService(
            provider=self.config.get("embedding_provider", "openai"),
            model=self.config.get("embedding_model", "text-embedding-3-small")
        )
    
    async def store(
        self, 
        content: str, 
        content_type: str = "entity",
        metadata: Optional[Dict[str, Any]] = None,
        entity_name: Optional[str] = None,
        entity_type: Optional[str] = None,
        description: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        confidence_score: float = 0.5
    ) -> str:
        """Store entity in memory."""
        try:
            # Use entity_name or extract from content
            if not entity_name:
                entity_name = content.split()[0] if content else "unknown"
            
            # Check if entity already exists
            existing_entity = await self._find_similar_entity(entity_name, entity_type)
            
            if existing_entity and confidence_score >= self.confidence_threshold:
                # Update existing entity
                return await self._update_existing_entity(
                    existing_entity, content, description, attributes, confidence_score
                )
            elif confidence_score >= self.confidence_threshold:
                # Create new entity
                return await self._create_new_entity(
                    content, entity_name, entity_type, description, 
                    attributes, confidence_score, metadata
                )
            else:
                # Confidence too low, don't store
                raise ValueError(f"Entity confidence {confidence_score} below threshold {self.confidence_threshold}")
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to store entity: {e}")
    
    async def retrieve(
        self, 
        query: str, 
        limit: int = 10,
        similarity_threshold: float = 0.5,
        entity_type: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> List[SearchResult]:
        """Retrieve relevant entities using vector similarity search."""
        try:
            # Generate embedding for the query
            query_embedding = await self.embedding_service.get_embedding(query)
            
            # Build base query
            base_query = self.db_session.query(EntityMemory).filter(
                EntityMemory.crew_id == self.crew_id,
                EntityMemory.embedding.isnot(None)
            )
            
            # Add optional filters
            if entity_type:
                base_query = base_query.filter(EntityMemory.entity_type == entity_type)
            if min_confidence:
                base_query = base_query.filter(EntityMemory.confidence_score >= min_confidence)
            
            # Use pgvector cosine similarity search
            similarity_query = base_query.order_by(
                text(f"embedding <=> '{query_embedding}'")
            ).limit(limit * 2)  # Get more results to filter by threshold
            
            entities = similarity_query.all()
            
            # Calculate similarities and filter by threshold
            results = []
            for i, entity in enumerate(entities):
                if entity.embedding:
                    similarity = await self.embedding_service.get_similarity(
                        query_embedding, entity.embedding
                    )
                    
                    if similarity >= similarity_threshold:
                        # Update mention tracking
                        entity.mention_count += 1
                        entity.last_updated = datetime.utcnow()
                        
                        entity_item = EntityItem(
                            id=str(entity.id),
                            content=entity.description or entity.entity_name,
                            content_type="entity",
                            metadata=json.loads(entity.attributes) if entity.attributes else None,
                            created_at=entity.first_mentioned,
                            relevance_score=entity.confidence_score,
                            entity_name=entity.entity_name,
                            entity_type=entity.entity_type,
                            description=entity.description,
                            attributes=json.loads(entity.attributes) if entity.attributes else None,
                            confidence_score=entity.confidence_score,
                            mention_count=entity.mention_count,
                            first_mentioned=entity.first_mentioned,
                            last_updated=entity.last_updated
                        )
                        
                        results.append(SearchResult(
                            item=entity_item,
                            similarity_score=similarity,
                            rank=i + 1
                        ))
            
            # Commit mention tracking updates
            self.db_session.commit()
            
            # Sort by combined score (similarity + confidence + mentions)
            results.sort(
                key=lambda x: (
                    x.similarity_score * 0.5 + 
                    (x.item.relevance_score or 0) * 0.3 + 
                    min(x.item.mention_count / 10.0, 0.2)
                ), 
                reverse=True
            )
            return results[:limit]
            
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve entities: {e}")
    
    async def get_by_id(self, memory_id: str) -> Optional[EntityItem]:
        """Get a specific entity by ID."""
        try:
            entity = self.db_session.query(EntityMemory).filter(
                EntityMemory.id == uuid.UUID(memory_id),
                EntityMemory.crew_id == self.crew_id
            ).first()
            
            if not entity:
                return None
            
            return EntityItem(
                id=str(entity.id),
                content=entity.description or entity.entity_name,
                content_type="entity",
                metadata=json.loads(entity.attributes) if entity.attributes else None,
                created_at=entity.first_mentioned,
                relevance_score=entity.confidence_score,
                entity_name=entity.entity_name,
                entity_type=entity.entity_type,
                description=entity.description,
                attributes=json.loads(entity.attributes) if entity.attributes else None,
                confidence_score=entity.confidence_score,
                mention_count=entity.mention_count,
                first_mentioned=entity.first_mentioned,
                last_updated=entity.last_updated
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to get entity: {e}")
    
    async def update(
        self, 
        memory_id: str, 
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None
    ) -> bool:
        """Update an existing entity."""
        try:
            entity = self.db_session.query(EntityMemory).filter(
                EntityMemory.id == uuid.UUID(memory_id),
                EntityMemory.crew_id == self.crew_id
            ).first()
            
            if not entity:
                return False
            
            # Update fields
            if description is not None:
                entity.description = description
                # Regenerate embedding if description changed
                embedding_text = f"{entity.entity_name} {entity.entity_type} {description}"
                entity.embedding = await self.embedding_service.get_embedding(embedding_text)
            
            if attributes is not None:
                entity.attributes = json.dumps(attributes)
            
            if confidence_score is not None:
                entity.confidence_score = confidence_score
            
            entity.last_updated = datetime.utcnow()
            
            self.db_session.commit()
            return True
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to update entity: {e}")
    
    async def delete(self, memory_id: str) -> bool:
        """Delete an entity by ID."""
        try:
            # Delete relationships first
            self.db_session.query(EntityRelationship).filter(
                (EntityRelationship.source_entity_id == uuid.UUID(memory_id)) |
                (EntityRelationship.target_entity_id == uuid.UUID(memory_id))
            ).delete()
            
            # Delete entity
            deleted_count = self.db_session.query(EntityMemory).filter(
                EntityMemory.id == uuid.UUID(memory_id),
                EntityMemory.crew_id == self.crew_id
            ).delete()
            
            self.db_session.commit()
            return deleted_count > 0
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to delete entity: {e}")
    
    async def clear_all(self) -> int:
        """Clear all entities for this crew."""
        try:
            # Delete relationships first
            relationship_count = self.db_session.query(EntityRelationship).join(
                EntityMemory, EntityRelationship.source_entity_id == EntityMemory.id
            ).filter(EntityMemory.crew_id == self.crew_id).delete()
            
            # Delete entities
            entity_count = self.db_session.query(EntityMemory).filter(
                EntityMemory.crew_id == self.crew_id
            ).delete()
            
            self.db_session.commit()
            return entity_count
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to clear entities: {e}")
    
    async def get_recent(
        self, 
        limit: int = 10,
        content_type: Optional[str] = None
    ) -> List[EntityItem]:
        """Get recent entities."""
        try:
            query = self.db_session.query(EntityMemory).filter(
                EntityMemory.crew_id == self.crew_id
            )
            
            entities = query.order_by(desc(EntityMemory.last_updated)).limit(limit).all()
            
            return [
                EntityItem(
                    id=str(entity.id),
                    content=entity.description or entity.entity_name,
                    content_type="entity",
                    metadata=json.loads(entity.attributes) if entity.attributes else None,
                    created_at=entity.first_mentioned,
                    relevance_score=entity.confidence_score,
                    entity_name=entity.entity_name,
                    entity_type=entity.entity_type,
                    description=entity.description,
                    attributes=json.loads(entity.attributes) if entity.attributes else None,
                    confidence_score=entity.confidence_score,
                    mention_count=entity.mention_count,
                    first_mentioned=entity.first_mentioned,
                    last_updated=entity.last_updated
                )
                for entity in entities
            ]
            
        except Exception as e:
            raise RuntimeError(f"Failed to get recent entities: {e}")
    
    async def cleanup(self) -> int:
        """Remove low-confidence entities and orphaned relationships."""
        try:
            # Remove entities with very low confidence and no recent mentions
            cutoff_date = datetime.utcnow().replace(day=datetime.utcnow().day - 60)  # 60 days ago
            
            low_confidence_count = self.db_session.query(EntityMemory).filter(
                EntityMemory.crew_id == self.crew_id,
                EntityMemory.confidence_score < 0.3,
                EntityMemory.mention_count <= 1,
                EntityMemory.first_mentioned < cutoff_date
            ).delete()
            
            # Remove orphaned relationships
            orphaned_relationships = self.db_session.query(EntityRelationship).filter(
                ~EntityRelationship.source_entity_id.in_(
                    self.db_session.query(EntityMemory.id).filter(
                        EntityMemory.crew_id == self.crew_id
                    )
                )
            ).delete()
            
            self.db_session.commit()
            return low_confidence_count + orphaned_relationships
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to cleanup entities: {e}")
    
    async def add_relationship(
        self, 
        source_entity_id: str, 
        target_entity_id: str,
        relationship_type: str,
        strength: float = 0.5,
        context: Optional[str] = None
    ) -> str:
        """Add a relationship between two entities."""
        try:
            # Check if relationship already exists
            existing = self.db_session.query(EntityRelationship).filter(
                EntityRelationship.source_entity_id == uuid.UUID(source_entity_id),
                EntityRelationship.target_entity_id == uuid.UUID(target_entity_id),
                EntityRelationship.relationship_type == relationship_type
            ).first()
            
            if existing:
                # Update existing relationship
                existing.strength = max(existing.strength, strength)
                existing.context = context
                self.db_session.commit()
                return str(existing.id)
            
            # Create new relationship
            relationship = EntityRelationship(
                id=uuid.uuid4(),
                source_entity_id=uuid.UUID(source_entity_id),
                target_entity_id=uuid.UUID(target_entity_id),
                relationship_type=relationship_type,
                strength=strength,
                context=context,
                created_at=datetime.utcnow()
            )
            
            self.db_session.add(relationship)
            self.db_session.commit()
            
            return str(relationship.id)
            
        except Exception as e:
            self.db_session.rollback()
            raise RuntimeError(f"Failed to add relationship: {e}")
    
    async def get_relationships(
        self, 
        entity_id: str, 
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get relationships for an entity."""
        try:
            query = self.db_session.query(EntityRelationship).filter(
                (EntityRelationship.source_entity_id == uuid.UUID(entity_id)) |
                (EntityRelationship.target_entity_id == uuid.UUID(entity_id))
            )
            
            if relationship_type:
                query = query.filter(EntityRelationship.relationship_type == relationship_type)
            
            relationships = query.all()
            
            result = []
            for rel in relationships:
                # Get the other entity in the relationship
                other_entity_id = (
                    rel.target_entity_id if str(rel.source_entity_id) == entity_id 
                    else rel.source_entity_id
                )
                
                other_entity = self.db_session.query(EntityMemory).filter(
                    EntityMemory.id == other_entity_id
                ).first()
                
                if other_entity:
                    result.append({
                        "relationship_id": str(rel.id),
                        "relationship_type": rel.relationship_type,
                        "strength": rel.strength,
                        "context": rel.context,
                        "direction": "outgoing" if str(rel.source_entity_id) == entity_id else "incoming",
                        "other_entity": {
                            "id": str(other_entity.id),
                            "name": other_entity.entity_name,
                            "type": other_entity.entity_type,
                            "confidence": other_entity.confidence_score
                        },
                        "created_at": rel.created_at
                    })
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"Failed to get relationships: {e}")
    
    async def get_by_type(self, entity_type: str, limit: int = 10) -> List[EntityItem]:
        """Get entities by type."""
        try:
            entities = self.db_session.query(EntityMemory).filter(
                EntityMemory.crew_id == self.crew_id,
                EntityMemory.entity_type == entity_type
            ).order_by(
                desc(EntityMemory.confidence_score),
                desc(EntityMemory.mention_count)
            ).limit(limit).all()
            
            return [
                EntityItem(
                    id=str(entity.id),
                    content=entity.description or entity.entity_name,
                    content_type="entity",
                    metadata=json.loads(entity.attributes) if entity.attributes else None,
                    created_at=entity.first_mentioned,
                    relevance_score=entity.confidence_score,
                    entity_name=entity.entity_name,
                    entity_type=entity.entity_type,
                    description=entity.description,
                    attributes=json.loads(entity.attributes) if entity.attributes else None,
                    confidence_score=entity.confidence_score,
                    mention_count=entity.mention_count,
                    first_mentioned=entity.first_mentioned,
                    last_updated=entity.last_updated
                )
                for entity in entities
            ]
            
        except Exception as e:
            raise RuntimeError(f"Failed to get entities by type: {e}")
    
    async def _find_similar_entity(
        self, 
        entity_name: str, 
        entity_type: Optional[str] = None
    ) -> Optional[EntityMemory]:
        """Find similar existing entity."""
        try:
            query = self.db_session.query(EntityMemory).filter(
                EntityMemory.crew_id == self.crew_id,
                EntityMemory.entity_name.ilike(f"%{entity_name}%")
            )
            
            if entity_type:
                query = query.filter(EntityMemory.entity_type == entity_type)
            
            return query.first()
            
        except Exception as e:
            return None
    
    async def _create_new_entity(
        self,
        content: str,
        entity_name: str,
        entity_type: Optional[str],
        description: Optional[str],
        attributes: Optional[Dict[str, Any]],
        confidence_score: float,
        metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Create a new entity."""
        # Generate embedding
        embedding_text = f"{entity_name} {entity_type or ''} {description or ''}"
        embedding = await self.embedding_service.get_embedding(embedding_text)
        
        # Create entity record
        entity = EntityMemory(
            id=uuid.uuid4(),
            crew_id=self.crew_id,
            entity_name=entity_name,
            entity_type=entity_type or "unknown",
            description=description,
            attributes=json.dumps(attributes) if attributes else None,
            embedding=embedding,
            confidence_score=confidence_score,
            first_mentioned=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            mention_count=1
        )
        
        self.db_session.add(entity)
        self.db_session.commit()
        
        return str(entity.id)
    
    async def _update_existing_entity(
        self,
        entity: EntityMemory,
        content: str,
        description: Optional[str],
        attributes: Optional[Dict[str, Any]],
        confidence_score: float
    ) -> str:
        """Update an existing entity."""
        # Update fields
        if description and not entity.description:
            entity.description = description
            # Regenerate embedding
            embedding_text = f"{entity.entity_name} {entity.entity_type} {description}"
            entity.embedding = await self.embedding_service.get_embedding(embedding_text)
        
        if attributes:
            existing_attrs = json.loads(entity.attributes) if entity.attributes else {}
            existing_attrs.update(attributes)
            entity.attributes = json.dumps(existing_attrs)
        
        # Update confidence (take maximum)
        entity.confidence_score = max(entity.confidence_score, confidence_score)
        entity.mention_count += 1
        entity.last_updated = datetime.utcnow()
        
        self.db_session.commit()
        return str(entity.id) 