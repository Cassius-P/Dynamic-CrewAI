"""Memory API endpoints for CrewAI backend."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.memory_service import get_memory_service
from app.schemas.memory import (
    # Short-term memory schemas
    ShortTermMemoryCreate, ShortTermMemoryResponse, ShortTermMemorySearch,
    # Long-term memory schemas  
    LongTermMemoryCreate, LongTermMemoryResponse, LongTermMemoryUpdate, LongTermMemorySearch,
    # Entity memory schemas
    EntityMemoryCreate, EntityMemoryResponse, EntityMemoryUpdate, EntityMemorySearch,
    EntityRelationshipCreate, EntityRelationshipResponse,
    # Configuration schemas
    MemoryConfigurationUpdate, MemoryConfigurationResponse,
    # Operation schemas
    MemorySearchRequest, MemorySearchResponse, ConversationContextRequest,
    ConsolidationResponse, CleanupResponse, ClearMemoryResponse, MemoryStats,
    # Response schemas
    SearchResult, MemoryItemResponse
)

router = APIRouter()


# Short-term memory endpoints
@router.post("/crews/{crew_id}/short-term", response_model=MemoryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_short_term_memory(
    crew_id: int,
    memory: ShortTermMemoryCreate,
    db: Session = Depends(get_db)
):
    """Create a short-term memory."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        memory_id = await memory_service.store_memory(
            crew_id=crew_id,
            content=memory.content,
            memory_type="short_term",
            content_type=memory.content_type,
            metadata=memory.metadata,
            agent_id=memory.agent_id,
            execution_id=memory.execution_id,
            relevance_score=memory.relevance_score
        )
        
        # Retrieve the created memory for response
        short_term = memory_service.get_short_term_memory(crew_id)
        created_memory = await short_term.get_by_id(memory_id)
        
        if not created_memory:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created memory"
            )
        
        return created_memory
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create short-term memory: {str(e)}"
        )


@router.post("/crews/{crew_id}/short-term/search", response_model=List[SearchResult])
async def search_short_term_memory(
    crew_id: int,
    search_request: ShortTermMemorySearch,
    db: Session = Depends(get_db)
):
    """Search short-term memories."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        short_term = memory_service.get_short_term_memory(crew_id)
        results = await short_term.retrieve(
            query=search_request.query,
            limit=search_request.limit,
            similarity_threshold=search_request.similarity_threshold,
            content_type=search_request.content_type,
            agent_id=search_request.agent_id
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search short-term memories: {str(e)}"
        )


@router.get("/crews/{crew_id}/short-term/conversation", response_model=List[MemoryItemResponse])
async def get_conversation_context(
    crew_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    execution_id: int = Query(default=None),
    db: Session = Depends(get_db)
):
    """Get conversation context from short-term memory."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        context = await memory_service.get_conversation_context(
            crew_id=crew_id,
            limit=limit,
            execution_id=execution_id
        )
        
        return context
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation context: {str(e)}"
        )


# Long-term memory endpoints
@router.post("/crews/{crew_id}/long-term", response_model=MemoryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_long_term_memory(
    crew_id: int,
    memory: LongTermMemoryCreate,
    db: Session = Depends(get_db)
):
    """Create a long-term memory."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        memory_id = await memory_service.store_memory(
            crew_id=crew_id,
            content=memory.content,
            memory_type="long_term",
            content_type=memory.content_type,
            metadata=memory.metadata,
            importance_score=memory.importance_score,
            source_execution_id=memory.source_execution_id,
            tags=memory.tags,
            summary=memory.summary
        )
        
        # Retrieve the created memory for response
        long_term = memory_service.get_long_term_memory(crew_id)
        created_memory = await long_term.get_by_id(memory_id)
        
        if not created_memory:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created memory"
            )
        
        return created_memory
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create long-term memory: {str(e)}"
        )


@router.post("/crews/{crew_id}/long-term/search", response_model=List[SearchResult])
async def search_long_term_memory(
    crew_id: int,
    search_request: LongTermMemorySearch,
    db: Session = Depends(get_db)
):
    """Search long-term memories."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        long_term = memory_service.get_long_term_memory(crew_id)
        
        # Build kwargs dynamically to handle optional parameters
        retrieve_kwargs = {
            "query": search_request.query,
            "limit": search_request.limit,
            "similarity_threshold": search_request.similarity_threshold,
        }
        if search_request.content_type:
            retrieve_kwargs["content_type"] = search_request.content_type
        if search_request.min_importance is not None:
            retrieve_kwargs["min_importance"] = search_request.min_importance
        if search_request.tags:
            retrieve_kwargs["tags"] = search_request.tags
            
        results = await long_term.retrieve(**retrieve_kwargs)
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search long-term memories: {str(e)}"
        )


@router.put("/crews/{crew_id}/long-term/{memory_id}", response_model=MemoryItemResponse)
async def update_long_term_memory(
    crew_id: int,
    memory_id: str,
    memory_update: LongTermMemoryUpdate,
    db: Session = Depends(get_db)
):
    """Update a long-term memory."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        long_term = memory_service.get_long_term_memory(crew_id)
        
        success = await long_term.update(
            memory_id=memory_id,
            content=memory_update.content,
            metadata=memory_update.metadata
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Long-term memory not found"
            )
        
        # Return updated memory
        updated_memory = await long_term.get_by_id(memory_id)
        return updated_memory
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update long-term memory: {str(e)}"
        )


@router.get("/crews/{crew_id}/long-term/insights", response_model=List[MemoryItemResponse])
async def get_insights(
    crew_id: int,
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get high-importance insights from long-term memory."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        insights = await memory_service.get_insights(crew_id=crew_id, limit=limit)
        return insights
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get insights: {str(e)}"
        )


# Entity memory endpoints
@router.post("/crews/{crew_id}/entities", response_model=MemoryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_entity(
    crew_id: int,
    entity: EntityMemoryCreate,
    db: Session = Depends(get_db)
):
    """Create an entity memory."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        memory_id = await memory_service.store_memory(
            crew_id=crew_id,
            content=entity.content,
            memory_type="entity",
            content_type=entity.content_type,
            metadata=entity.metadata,
            entity_name=entity.entity_name,
            entity_type=entity.entity_type,
            description=entity.description,
            attributes=entity.attributes,
            confidence_score=entity.confidence_score
        )
        
        # Retrieve the created entity for response
        entity_memory = memory_service.get_entity_memory(crew_id)
        created_entity = await entity_memory.get_by_id(memory_id)
        
        if not created_entity:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created entity"
            )
        
        return created_entity
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create entity: {str(e)}"
        )


@router.post("/crews/{crew_id}/entities/search", response_model=List[SearchResult])
async def search_entities(
    crew_id: int,
    search_request: EntityMemorySearch,
    db: Session = Depends(get_db)
):
    """Search entity memories."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        entity_memory = memory_service.get_entity_memory(crew_id)
        
        # Build kwargs dynamically to handle optional parameters
        retrieve_kwargs = {
            "query": search_request.query,
            "limit": search_request.limit,
            "similarity_threshold": search_request.similarity_threshold,
        }
        if search_request.entity_type:
            retrieve_kwargs["entity_type"] = search_request.entity_type
        if search_request.min_confidence is not None:
            retrieve_kwargs["min_confidence"] = search_request.min_confidence
            
        results = await entity_memory.retrieve(**retrieve_kwargs)
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search entities: {str(e)}"
        )


@router.get("/crews/{crew_id}/entities/types/{entity_type}", response_model=List[MemoryItemResponse])
async def get_entities_by_type(
    crew_id: int,
    entity_type: str,
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get entities by type."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        entities = await memory_service.get_entities_by_type(
            crew_id=crew_id,
            entity_type=entity_type,
            limit=limit
        )
        
        return entities
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get entities by type: {str(e)}"
        )


@router.post("/crews/{crew_id}/entities/relationships", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_entity_relationship(
    crew_id: int,
    relationship: EntityRelationshipCreate,
    db: Session = Depends(get_db)
):
    """Create a relationship between entities."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        relationship_id = await memory_service.add_entity_relationship(
            crew_id=crew_id,
            source_entity_id=relationship.source_entity_id,
            target_entity_id=relationship.target_entity_id,
            relationship_type=relationship.relationship_type,
            strength=relationship.strength,
            context=relationship.context
        )
        
        return {"relationship_id": relationship_id}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create entity relationship: {str(e)}"
        )


@router.get("/crews/{crew_id}/entities/{entity_id}/relationships", response_model=List[EntityRelationshipResponse])
async def get_entity_relationships(
    crew_id: int,
    entity_id: str,
    relationship_type: str = Query(default=None),
    db: Session = Depends(get_db)
):
    """Get relationships for an entity."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        relationships = await memory_service.get_entity_relationships(
            crew_id=crew_id,
            entity_id=entity_id,
            relationship_type=relationship_type
        )
        
        return relationships
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get entity relationships: {str(e)}"
        )


# Unified memory operations
@router.post("/crews/{crew_id}/search", response_model=MemorySearchResponse)
async def search_all_memories(
    crew_id: int,
    search_request: MemorySearchRequest,
    db: Session = Depends(get_db)
):
    """Search across all memory types."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        results = await memory_service.retrieve_memories(
            crew_id=crew_id,
            query=search_request.query,
            memory_types=search_request.memory_types,
            limit=search_request.limit,
            similarity_threshold=search_request.similarity_threshold
        )
        
        # Convert base_memory.SearchResult to schemas.memory.SearchResult
        converted_results = {}
        for memory_type, search_results in results.items():
            if search_results:
                converted_results[memory_type] = [
                    SearchResult(
                        item=MemoryItemResponse(
                            id=result.item.id,
                            content=result.item.content,
                            content_type=result.item.content_type,
                            metadata=result.item.metadata,
                            created_at=result.item.created_at,
                            relevance_score=result.item.relevance_score
                        ),
                        similarity_score=result.similarity_score,
                        rank=result.rank
                    )
                    for result in search_results
                ]
            else:
                converted_results[memory_type] = None
        
        return MemorySearchResponse(**converted_results)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search memories: {str(e)}"
        )


# Memory management operations
@router.post("/crews/{crew_id}/consolidate", response_model=ConsolidationResponse)
async def consolidate_memories(
    crew_id: int,
    db: Session = Depends(get_db)
):
    """Consolidate short-term memories into long-term storage."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        result = await memory_service.consolidate_memories(crew_id)
        return ConsolidationResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to consolidate memories: {str(e)}"
        )


@router.post("/crews/{crew_id}/cleanup", response_model=CleanupResponse)
async def cleanup_memories(
    crew_id: int,
    db: Session = Depends(get_db)
):
    """Perform cleanup operations on all memory types."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        result = await memory_service.cleanup_memories(crew_id)
        return CleanupResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup memories: {str(e)}"
        )


@router.delete("/crews/{crew_id}/clear", response_model=ClearMemoryResponse)
async def clear_all_memories(
    crew_id: int,
    db: Session = Depends(get_db)
):
    """Clear all memories for a crew."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        result = await memory_service.clear_all_memories(crew_id)
        return ClearMemoryResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear memories: {str(e)}"
        )


# Memory configuration endpoints
@router.get("/crews/{crew_id}/config", response_model=MemoryConfigurationResponse)
async def get_memory_configuration(
    crew_id: int,
    db: Session = Depends(get_db)
):
    """Get memory configuration for a crew."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        config = memory_service.get_memory_config(crew_id)
        
        # Add crew_id and timestamps (they would come from the database model)
        config_response = {
            "crew_id": crew_id,
            **config,
            "created_at": "2024-01-01T00:00:00Z",  # This would come from the actual DB record
            "updated_at": "2024-01-01T00:00:00Z"   # This would come from the actual DB record
        }
        
        return MemoryConfigurationResponse(**config_response)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory configuration: {str(e)}"
        )


@router.put("/crews/{crew_id}/config", response_model=MemoryConfigurationResponse)
async def update_memory_configuration(
    crew_id: int,
    config_update: MemoryConfigurationUpdate,
    db: Session = Depends(get_db)
):
    """Update memory configuration for a crew."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        config = await memory_service.update_memory_config(
            crew_id=crew_id,
            config_updates=config_update.model_dump(exclude_unset=True)
        )
        
        # Add crew_id and timestamps
        config_response = {
            "crew_id": crew_id,
            **config,
            "created_at": "2024-01-01T00:00:00Z",  # This would come from the actual DB record
            "updated_at": "2024-01-01T00:00:00Z"   # This would come from the actual DB record
        }
        
        return MemoryConfigurationResponse(**config_response)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update memory configuration: {str(e)}"
        )


# Memory statistics endpoint
@router.get("/crews/{crew_id}/stats", response_model=MemoryStats)
async def get_memory_statistics(
    crew_id: int,
    db: Session = Depends(get_db)
):
    """Get memory statistics for a crew."""
    try:
        memory_service = get_memory_service()
        memory_service.db_session = db
        
        stats = await memory_service.get_memory_stats(crew_id)
        return MemoryStats(**stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory statistics: {str(e)}"
        ) 