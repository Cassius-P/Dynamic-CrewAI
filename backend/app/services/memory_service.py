"""Memory service for managing crew memory operations."""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union, cast
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.memory import MemoryConfiguration, MemoryCleanupLog
from app.memory.base_memory import MemoryItem, SearchResult
import os

# Use mock implementations for testing
if os.getenv("USE_MOCK_MEMORY", "false").lower() == "true":
    from app.memory.mock_memory_impl import MockMemoryImpl as ShortTermMemoryImpl
    from app.memory.mock_memory_impl import MockMemoryImpl as LongTermMemoryImpl
    from app.memory.mock_memory_impl import MockMemoryImpl as EntityMemoryImpl
    from app.memory.base_memory import MemoryItem as EntityItem
else:
    from app.memory.short_term_memory import ShortTermMemoryImpl
    from app.memory.long_term_memory import LongTermMemoryImpl
    from app.memory.entity_memory import EntityMemoryImpl, EntityItem

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for managing crew memory operations."""
    
    def __init__(self, db_session: Session):
        """Initialize memory service."""
        self.db_session = db_session
        self._memory_instances: Dict[int, Dict[str, Any]] = {}
    
    def get_memory_config(self, crew_id: int) -> Dict[str, Any]:
        """Get memory configuration for a crew."""
        config = self.db_session.query(MemoryConfiguration).filter(
            MemoryConfiguration.crew_id == crew_id
        ).first()
        
        if not config:
            # Create default configuration
            config = MemoryConfiguration(
                crew_id=crew_id,
                short_term_retention_hours=24,
                short_term_max_entries=100,
                long_term_consolidation_threshold=0.7,
                long_term_max_entries=1000,
                entity_confidence_threshold=0.6,
                entity_similarity_threshold=0.8,
                embedding_provider="openai",
                embedding_model="text-embedding-3-small",
                cleanup_enabled=True,
                cleanup_interval_hours=24
            )
            self.db_session.add(config)
            self.db_session.commit()
        
        return {
            "short_term_retention_hours": config.short_term_retention_hours,
            "short_term_max_entries": config.short_term_max_entries,
            "long_term_consolidation_threshold": config.long_term_consolidation_threshold,
            "long_term_max_entries": config.long_term_max_entries,
            "entity_confidence_threshold": config.entity_confidence_threshold,
            "entity_similarity_threshold": config.entity_similarity_threshold,
            "embedding_provider": config.embedding_provider,
            "embedding_model": config.embedding_model,
            "cleanup_enabled": config.cleanup_enabled,
            "cleanup_interval_hours": config.cleanup_interval_hours
        }
    
    def get_short_term_memory(self, crew_id: int) -> ShortTermMemoryImpl:
        """Get short-term memory instance for a crew."""
        if crew_id not in self._memory_instances:
            self._memory_instances[crew_id] = {}
        
        if "short_term" not in self._memory_instances[crew_id]:
            config = self.get_memory_config(crew_id)
            self._memory_instances[crew_id]["short_term"] = ShortTermMemoryImpl(
                self.db_session, crew_id, config
            )
        
        return self._memory_instances[crew_id]["short_term"]
    
    def get_long_term_memory(self, crew_id: int) -> LongTermMemoryImpl:
        """Get long-term memory instance for a crew."""
        if crew_id not in self._memory_instances:
            self._memory_instances[crew_id] = {}
        
        if "long_term" not in self._memory_instances[crew_id]:
            config = self.get_memory_config(crew_id)
            self._memory_instances[crew_id]["long_term"] = LongTermMemoryImpl(
                self.db_session, crew_id, config
            )
        
        return self._memory_instances[crew_id]["long_term"]
    
    def get_entity_memory(self, crew_id: int) -> EntityMemoryImpl:
        """Get entity memory instance for a crew."""
        if crew_id not in self._memory_instances:
            self._memory_instances[crew_id] = {}
        
        if "entity" not in self._memory_instances[crew_id]:
            config = self.get_memory_config(crew_id)
            self._memory_instances[crew_id]["entity"] = EntityMemoryImpl(
                self.db_session, crew_id, config
            )
        
        return self._memory_instances[crew_id]["entity"]
    
    async def store_memory(
        self,
        crew_id: int,
        content: str,
        memory_type: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Store memory in the appropriate memory type."""
        try:
            if memory_type == "short_term":
                memory = self.get_short_term_memory(crew_id)
                return await memory.store(content, content_type, metadata, **kwargs)
            elif memory_type == "long_term":
                memory = self.get_long_term_memory(crew_id)
                return await memory.store(content, content_type, metadata, **kwargs)
            elif memory_type == "entity":
                memory = self.get_entity_memory(crew_id)
                return await memory.store(content, content_type, metadata, **kwargs)
            else:
                raise ValueError(f"Unknown memory type: {memory_type}")
        
        except Exception as e:
            logger.error(f"Failed to store memory for crew {crew_id}: {e}")
            raise
    
    async def retrieve_memories(
        self,
        crew_id: int,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 10,
        similarity_threshold: float = 0.5,
        **kwargs
    ) -> Dict[str, List[SearchResult]]:
        """Retrieve memories from specified memory types."""
        if memory_types is None:
            memory_types = ["short_term", "long_term", "entity"]
        
        results = {}
        
        try:
            for memory_type in memory_types:
                if memory_type == "short_term":
                    memory = self.get_short_term_memory(crew_id)
                    results[memory_type] = await memory.retrieve(
                        query, limit, similarity_threshold, **kwargs
                    )
                elif memory_type == "long_term":
                    memory = self.get_long_term_memory(crew_id)
                    results[memory_type] = await memory.retrieve(
                        query, limit, similarity_threshold, **kwargs
                    )
                elif memory_type == "entity":
                    memory = self.get_entity_memory(crew_id)
                    results[memory_type] = await memory.retrieve(
                        query, limit, similarity_threshold, **kwargs
                    )
        
        except Exception as e:
            logger.error(f"Failed to retrieve memories for crew {crew_id}: {e}")
            raise
        
        return results
    
    async def get_conversation_context(
        self,
        crew_id: int,
        limit: int = 20,
        execution_id: Optional[int] = None
    ) -> List[MemoryItem]:
        """Get conversation context from short-term memory."""
        try:
            short_term = self.get_short_term_memory(crew_id)
            return await short_term.get_conversation_context(limit, execution_id)
        
        except Exception as e:
            logger.error(f"Failed to get conversation context for crew {crew_id}: {e}")
            raise
    
    async def get_insights(
        self,
        crew_id: int,
        limit: int = 10
    ) -> List[MemoryItem]:
        """Get high-importance insights from long-term memory."""
        try:
            long_term = self.get_long_term_memory(crew_id)
            return await long_term.get_insights(limit)
        
        except Exception as e:
            logger.error(f"Failed to get insights for crew {crew_id}: {e}")
            raise
    
    async def get_entities_by_type(
        self,
        crew_id: int,
        entity_type: str,
        limit: int = 10
    ) -> List[Any]:
        """Get entities by type."""
        try:
            entity_memory = self.get_entity_memory(crew_id)
            return await entity_memory.get_by_type(entity_type, limit)
        
        except Exception as e:
            logger.error(f"Failed to get entities by type for crew {crew_id}: {e}")
            raise
    
    async def add_entity_relationship(
        self,
        crew_id: int,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        strength: float = 0.5,
        context: Optional[str] = None
    ) -> str:
        """Add a relationship between entities."""
        try:
            entity_memory = self.get_entity_memory(crew_id)
            return await entity_memory.add_relationship(
                source_entity_id, target_entity_id, relationship_type, strength, context
            )
        
        except Exception as e:
            logger.error(f"Failed to add entity relationship for crew {crew_id}: {e}")
            raise
    
    async def get_entity_relationships(
        self,
        crew_id: int,
        entity_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get relationships for an entity."""
        try:
            entity_memory = self.get_entity_memory(crew_id)
            return await entity_memory.get_relationships(entity_id, relationship_type)
        
        except Exception as e:
            logger.error(f"Failed to get entity relationships for crew {crew_id}: {e}")
            raise
    
    async def consolidate_memories(self, crew_id: int) -> Dict[str, int]:
        """Consolidate short-term memories into long-term storage."""
        try:
            short_term = self.get_short_term_memory(crew_id)
            long_term = self.get_long_term_memory(crew_id)
            
            # Get high-relevance short-term memories
            config = self.get_memory_config(crew_id)
            threshold = config["long_term_consolidation_threshold"]
            
            recent_memories = await short_term.get_recent(limit=50)
            high_relevance = [
                memory for memory in recent_memories 
                if (memory.relevance_score or 0) >= threshold
            ]
            
            # Consolidate into long-term memory
            consolidated_count = await long_term.consolidate_from_short_term(threshold)
            
            return {
                "evaluated": len(recent_memories),
                "consolidated": consolidated_count,
                "threshold": threshold
            }
        
        except Exception as e:
            logger.error(f"Failed to consolidate memories for crew {crew_id}: {e}")
            raise
    
    async def cleanup_memories(self, crew_id: int) -> Dict[str, Any]:
        """Perform cleanup operations on all memory types."""
        try:
            start_time = datetime.utcnow()
            
            short_term = self.get_short_term_memory(crew_id)
            long_term = self.get_long_term_memory(crew_id)
            entity_memory = self.get_entity_memory(crew_id)
            
            # Perform cleanup
            short_term_cleaned = await short_term.cleanup()
            long_term_cleaned = await long_term.cleanup()
            entity_cleaned = await entity_memory.cleanup()
            
            total_cleaned = short_term_cleaned + long_term_cleaned + entity_cleaned
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Log cleanup operation
            cleanup_log = MemoryCleanupLog(
                crew_id=crew_id,
                cleanup_type="full",
                entries_removed=total_cleaned,
                cleanup_reason="scheduled_cleanup",
                execution_time_seconds=execution_time
            )
            self.db_session.add(cleanup_log)
            self.db_session.commit()
            
            return {
                "short_term_cleaned": short_term_cleaned,
                "long_term_cleaned": long_term_cleaned,
                "entity_cleaned": entity_cleaned,
                "total_cleaned": total_cleaned,
                "execution_time": execution_time
            }
        
        except Exception as e:
            logger.error(f"Failed to cleanup memories for crew {crew_id}: {e}")
            raise
    
    async def clear_all_memories(self, crew_id: int) -> Dict[str, int]:
        """Clear all memories for a crew."""
        try:
            short_term = self.get_short_term_memory(crew_id)
            long_term = self.get_long_term_memory(crew_id)
            entity_memory = self.get_entity_memory(crew_id)
            
            # Clear all memory types
            short_term_cleared = await short_term.clear_all()
            long_term_cleared = await long_term.clear_all()
            entity_cleared = await entity_memory.clear_all()
            
            total_cleared = short_term_cleared + long_term_cleared + entity_cleared
            
            # Log cleanup operation
            cleanup_log = MemoryCleanupLog(
                crew_id=crew_id,
                cleanup_type="full",
                entries_removed=total_cleared,
                cleanup_reason="manual_clear",
                execution_time_seconds=0.0
            )
            self.db_session.add(cleanup_log)
            self.db_session.commit()
            
            # Clear cached instances
            if crew_id in self._memory_instances:
                del self._memory_instances[crew_id]
            
            return {
                "short_term_cleared": short_term_cleared,
                "long_term_cleared": long_term_cleared,
                "entity_cleared": entity_cleared,
                "total_cleared": total_cleared
            }
        
        except Exception as e:
            logger.error(f"Failed to clear memories for crew {crew_id}: {e}")
            raise
    
    async def get_memory_stats(self, crew_id: int) -> Dict[str, Any]:
        """Get memory statistics for a crew."""
        try:
            from sqlalchemy import func
            from app.models.memory import ShortTermMemory, LongTermMemory, EntityMemory
            
            # Get counts for each memory type
            short_term_count = self.db_session.query(func.count(ShortTermMemory.id)).filter(
                ShortTermMemory.crew_id == crew_id
            ).scalar()
            
            long_term_count = self.db_session.query(func.count(LongTermMemory.id)).filter(
                LongTermMemory.crew_id == crew_id
            ).scalar()
            
            entity_count = self.db_session.query(func.count(EntityMemory.id)).filter(
                EntityMemory.crew_id == crew_id
            ).scalar()
            
            # Get recent cleanup logs
            recent_cleanups = self.db_session.query(MemoryCleanupLog).filter(
                MemoryCleanupLog.crew_id == crew_id
            ).order_by(MemoryCleanupLog.created_at.desc()).limit(5).all()
            
            # Get memory configuration
            config = self.get_memory_config(crew_id)
            
            return {
                "crew_id": crew_id,
                "counts": {
                    "short_term": short_term_count,
                    "long_term": long_term_count,
                    "entity": entity_count,
                    "total": short_term_count + long_term_count + entity_count
                },
                "limits": {
                    "short_term_max": config["short_term_max_entries"],
                    "long_term_max": config["long_term_max_entries"]
                },
                "utilization": {
                    "short_term": (short_term_count / config["short_term_max_entries"]) * 100,
                    "long_term": (long_term_count / config["long_term_max_entries"]) * 100
                },
                "recent_cleanups": [
                    {
                        "type": log.cleanup_type,
                        "entries_removed": log.entries_removed,
                        "reason": log.cleanup_reason,
                        "execution_time": log.execution_time_seconds,
                        "created_at": log.created_at
                    }
                    for log in recent_cleanups
                ],
                "configuration": config
            }
        
        except Exception as e:
            logger.error(f"Failed to get memory stats for crew {crew_id}: {e}")
            raise
    
    async def update_memory_config(
        self,
        crew_id: int,
        config_updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update memory configuration for a crew."""
        try:
            config = self.db_session.query(MemoryConfiguration).filter(
                MemoryConfiguration.crew_id == crew_id
            ).first()
            
            if not config:
                raise ValueError(f"No memory configuration found for crew {crew_id}")
            
            # Update configuration fields
            for key, value in config_updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            # Use setattr to avoid type checker issues with SQLAlchemy columns
            setattr(config, 'updated_at', datetime.utcnow())
            self.db_session.commit()
            
            # Clear cached memory instances to pick up new config
            if crew_id in self._memory_instances:
                del self._memory_instances[crew_id]
            
            return self.get_memory_config(crew_id)
        
        except Exception as e:
            logger.error(f"Failed to update memory config for crew {crew_id}: {e}")
            raise


class MemoryScheduler:
    """Scheduler for automatic memory operations."""
    
    def __init__(self, memory_service: MemoryService):
        """Initialize memory scheduler."""
        self.memory_service = memory_service
        self._running = False
        self._task = None
    
    async def start(self):
        """Start the memory scheduler."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Memory scheduler started")
    
    async def stop(self):
        """Stop the memory scheduler."""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Memory scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                await self._run_scheduled_operations()
                await asyncio.sleep(3600)  # Run every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory scheduler: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _run_scheduled_operations(self):
        """Run scheduled memory operations."""
        try:
            # Get all crews with cleanup enabled
            from app.models.memory import MemoryConfiguration
            
            configs = self.memory_service.db_session.query(MemoryConfiguration).filter(
                MemoryConfiguration.cleanup_enabled == True
            ).all()
            
            for config in configs:
                # Cast config attributes to their runtime types to avoid type checker issues
                config_crew_id = cast(int, config.crew_id)
                config_cleanup_interval_hours = cast(int, config.cleanup_interval_hours)
                
                # Check if cleanup is due
                last_cleanup = self.memory_service.db_session.query(MemoryCleanupLog).filter(
                    MemoryCleanupLog.crew_id == config_crew_id,
                    MemoryCleanupLog.cleanup_type == "scheduled"
                ).order_by(MemoryCleanupLog.created_at.desc()).first()
                
                # Cast last_cleanup attributes if it exists
                if last_cleanup:
                    last_cleanup_created_at = cast(datetime, last_cleanup.created_at)
                    cleanup_due = datetime.utcnow() - last_cleanup_created_at > timedelta(hours=config_cleanup_interval_hours)
                else:
                    cleanup_due = True
                
                if cleanup_due:
                    logger.info(f"Running scheduled cleanup for crew {config_crew_id}")
                    await self.memory_service.cleanup_memories(config_crew_id)
                    
                    # Also run consolidation
                    await self.memory_service.consolidate_memories(config_crew_id)
        
        except Exception as e:
            logger.error(f"Error in scheduled operations: {e}")


# Global memory service instance
_memory_service = None
_memory_scheduler = None


def get_memory_service() -> MemoryService:
    """Get the global memory service instance."""
    global _memory_service
    if _memory_service is None:
        db_session = next(get_db())
        _memory_service = MemoryService(db_session)
    return _memory_service


def get_memory_scheduler() -> MemoryScheduler:
    """Get the global memory scheduler instance."""
    global _memory_scheduler
    if _memory_scheduler is None:
        _memory_scheduler = MemoryScheduler(get_memory_service())
    return _memory_scheduler 