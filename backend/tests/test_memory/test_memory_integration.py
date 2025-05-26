"""Tests for memory system integration."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.services.memory_service import MemoryService
from app.integrations.crewai_memory import CrewAIMemoryAdapter, MemoryItem, create_crew_memory
from app.models.memory import MemoryConfiguration


class TestMemoryIntegration:
    """Test memory system integration."""
    
    @pytest.fixture
    def memory_service(self, db_session):
        """Create memory service instance."""
        return MemoryService(db_session)
    
    @pytest.fixture
    def crew_memory_adapter(self, db_session):
        """Create CrewAI memory adapter."""
        return CrewAIMemoryAdapter(crew_id=1, db_session=db_session)
    
    def test_memory_configuration_creation(self, memory_service):
        """Test memory configuration is created automatically."""
        config = memory_service.get_memory_config(crew_id=1)
        
        assert config is not None
        assert config["short_term_retention_hours"] == 24
        assert config["short_term_max_entries"] == 100
        assert config["long_term_consolidation_threshold"] == 0.7
        assert config["embedding_provider"] == "openai"
    
    def test_crewai_adapter_initialization(self, crew_memory_adapter):
        """Test CrewAI adapter initializes correctly."""
        assert crew_memory_adapter.crew_id == 1
        assert crew_memory_adapter.memory_service is not None
        assert not crew_memory_adapter._initialized
        
        # Trigger initialization
        crew_memory_adapter._ensure_initialized()
        assert crew_memory_adapter._initialized
    
    @patch('app.services.memory_service.MemoryService.store_memory')
    def test_memory_item_storage(self, mock_store, crew_memory_adapter):
        """Test storing memory items through CrewAI adapter."""
        # Create a completed future-like object
        async def mock_store_func(*args, **kwargs):
            return "memory_id_123"
        mock_store.return_value = mock_store_func()
        
        memory_item = MemoryItem(
            content="Test memory content",
            metadata={"type": "test", "importance": 0.8}
        )
        
        result = crew_memory_adapter.store(memory_item)
        
        assert result is True
        mock_store.assert_called_once()
        call_args = mock_store.call_args
        assert call_args[1]["crew_id"] == 1
        assert call_args[1]["content"] == "Test memory content"
        assert call_args[1]["memory_type"] == "short_term"
        assert call_args[1]["content_type"] == "text"
    
    @patch('app.services.memory_service.MemoryService.retrieve_memories')
    def test_memory_item_retrieval(self, mock_retrieve, crew_memory_adapter):
        """Test retrieving memory items through CrewAI adapter."""
        from app.memory.base_memory import MemoryItem as BaseMemoryItem, SearchResult
        
        # Mock search results
        mock_memory_item = BaseMemoryItem(
            id="test_id",
            content="Retrieved content",
            content_type="text",
            metadata={"test": "data"},
            created_at=datetime.utcnow()
        )
        mock_search_result = SearchResult(
            item=mock_memory_item,
            similarity_score=0.9,
            rank=1
        )
        
        # Return the actual result directly (not a coroutine)
        mock_retrieve.return_value = {"short_term": [mock_search_result]}
        
        results = crew_memory_adapter.retrieve("test query", limit=5)
        
        assert len(results) == 1
        assert results[0].content == "Retrieved content"
        assert results[0].metadata["similarity_score"] == 0.9
        assert results[0].metadata["memory_type"] == "short_term"
        
        mock_retrieve.assert_called_once()
        call_args = mock_retrieve.call_args
        assert call_args[1]["crew_id"] == 1
        assert call_args[1]["query"] == "test query"
        assert call_args[1]["limit"] == 5
    
    def test_memory_type_specific_storage(self, crew_memory_adapter):
        """Test storing to specific memory types."""
        memory_item = MemoryItem("Test content")
        
        with patch.object(crew_memory_adapter, '_store_memory') as mock_store:
            mock_store.return_value = True
            
            # Test short-term storage
            crew_memory_adapter.store_short_term(memory_item)
            mock_store.assert_called_with(memory_item, "short_term")
            
            # Test long-term storage
            crew_memory_adapter.store_long_term(memory_item)
            mock_store.assert_called_with(memory_item, "long_term")
            
            # Test entity storage
            crew_memory_adapter.store_entity(memory_item)
            mock_store.assert_called_with(memory_item, "entity")
    
    def test_memory_type_specific_retrieval(self, crew_memory_adapter):
        """Test retrieving from specific memory types."""
        with patch.object(crew_memory_adapter, '_retrieve_memory') as mock_retrieve:
            mock_retrieve.return_value = []
            
            # Test short-term retrieval
            crew_memory_adapter.get_short_term_memory("query")
            mock_retrieve.assert_called_with("query", 10, "short_term")
            
            # Test long-term retrieval
            crew_memory_adapter.get_long_term_memory("query", 5)
            mock_retrieve.assert_called_with("query", 5, "long_term")
            
            # Test entity retrieval
            crew_memory_adapter.get_entity_memory("query", 15)
            mock_retrieve.assert_called_with("query", 15, "entity")
    
    @patch('app.services.memory_service.MemoryService.clear_all_memories')
    def test_memory_clearing(self, mock_clear, crew_memory_adapter):
        """Test clearing memory."""
        # Create a completed future-like object
        async def mock_clear_func(*args, **kwargs):
            return {"total_cleared": 10}
        mock_clear.return_value = mock_clear_func()
        
        crew_memory_adapter.clear()
        
        mock_clear.assert_called_once_with(1)
    
    @patch('app.services.memory_service.MemoryService.get_memory_stats')
    def test_memory_statistics(self, mock_stats, crew_memory_adapter):
        """Test getting memory statistics."""
        # Return the actual result directly (not a coroutine)
        mock_stats.return_value = {
            "crew_id": 1,
            "counts": {"short_term": 5, "long_term": 3, "entity": 2},
            "total": 10
        }
        
        stats = crew_memory_adapter.get_stats()
        
        assert stats["crew_id"] == 1
        assert stats["counts"]["short_term"] == 5
        assert stats["total"] == 10
        
        mock_stats.assert_called_once_with(1)
    
    def test_factory_function(self):
        """Test factory function for creating crew memory."""
        config = {"test": "config"}
        adapter = create_crew_memory(crew_id=2, config=config)
        
        assert isinstance(adapter, CrewAIMemoryAdapter)
        assert adapter.crew_id == 2
        assert adapter.config == config
    
    def test_error_handling_in_storage(self, crew_memory_adapter):
        """Test error handling during memory storage."""
        memory_item = MemoryItem("Test content")
        
        with patch.object(crew_memory_adapter.memory_service, 'store_memory') as mock_store:
            mock_store.side_effect = Exception("Storage error")
            
            result = crew_memory_adapter.store(memory_item)
            
            assert result is False
    
    def test_error_handling_in_retrieval(self, crew_memory_adapter):
        """Test error handling during memory retrieval."""
        with patch.object(crew_memory_adapter.memory_service, 'retrieve_memories') as mock_retrieve:
            mock_retrieve.side_effect = Exception("Retrieval error")
            
            results = crew_memory_adapter.retrieve("test query")
            
            assert results == []
    
    def test_memory_item_metadata_handling(self, crew_memory_adapter):
        """Test proper handling of memory item metadata."""
        memory_item = MemoryItem(
            content="Test content",
            metadata={
                "content_type": "conversation",
                "agent_id": 123,
                "importance": 0.9
            }
        )
        
        with patch.object(crew_memory_adapter.memory_service, 'store_memory') as mock_store:
            # Create a completed future-like object
            async def mock_store_func(*args, **kwargs):
                return "memory_id"
            mock_store.return_value = mock_store_func()
            
            crew_memory_adapter.store(memory_item)
            
            call_args = mock_store.call_args
            assert call_args[1]["content_type"] == "conversation"
            assert call_args[1]["metadata"]["agent_id"] == 123
            assert call_args[1]["metadata"]["importance"] == 0.9


class TestAgentMemory:
    """Test agent-specific memory functionality."""
    
    def test_agent_memory_creation(self):
        """Test creating agent-specific memory."""
        from app.integrations.crewai_memory import create_agent_memory
        
        agent_memory = create_agent_memory(crew_id=1, agent_id=42)
        
        assert isinstance(agent_memory, CrewAIMemoryAdapter)
        assert agent_memory.crew_id == 1
    
    def test_agent_memory_metadata_injection(self):
        """Test that agent ID is injected into metadata."""
        from app.integrations.crewai_memory import create_agent_memory
        
        agent_memory = create_agent_memory(crew_id=1, agent_id=42)
        memory_item = MemoryItem("Test content", {"existing": "metadata"})
        
        with patch.object(agent_memory.memory_service, 'get_memory_config') as mock_config, \
             patch.object(agent_memory.memory_service, 'store_memory') as mock_store:
            
            # Mock the config to avoid database access
            mock_config.return_value = {"test": "config"}
            
            # Create a completed future-like object
            async def mock_store_func(*args, **kwargs):
                return "memory_id"
            mock_store.return_value = mock_store_func()
            
            agent_memory.store(memory_item)
            
            # Check that agent_id was added to metadata
            call_args = mock_store.call_args
            assert call_args[1]["metadata"]["agent_id"] == 42
            assert call_args[1]["metadata"]["existing"] == "metadata"


class TestMemoryServiceIntegration:
    """Test memory service integration with different memory types."""
    
    @pytest.fixture
    def memory_service(self, db_session):
        """Create memory service instance."""
        return MemoryService(db_session)
    
    def test_memory_type_instances(self, memory_service):
        """Test that memory type instances are created correctly."""
        crew_id = 1
        
        short_term = memory_service.get_short_term_memory(crew_id)
        long_term = memory_service.get_long_term_memory(crew_id)
        entity = memory_service.get_entity_memory(crew_id)
        
        assert short_term is not None
        assert long_term is not None
        assert entity is not None
        
        # Test that instances are cached
        assert memory_service.get_short_term_memory(crew_id) is short_term
        assert memory_service.get_long_term_memory(crew_id) is long_term
        assert memory_service.get_entity_memory(crew_id) is entity
    
    @pytest.mark.asyncio
    async def test_short_term_memory_storage(self, memory_service):
        """Test storing to short-term memory."""
        # Mock the short-term memory instance
        with patch.object(memory_service, 'get_short_term_memory') as mock_get_memory:
            mock_memory = Mock()
            
            async def mock_store(*args, **kwargs):
                return "memory_id"
            mock_memory.store = mock_store
            mock_get_memory.return_value = mock_memory
            
            result = await memory_service.store_memory(
                crew_id=1,
                content="Test content",
                memory_type="short_term",
                content_type="text",
                metadata={"test": "data"}
            )
            
            assert result == "memory_id"
            # Note: We can't easily assert on async mock calls, but the test passing means it worked
    
    @pytest.mark.asyncio
    async def test_long_term_memory_storage(self, memory_service):
        """Test storing to long-term memory."""
        # Mock the long-term memory instance
        with patch.object(memory_service, 'get_long_term_memory') as mock_get_memory:
            mock_memory = Mock()
            
            async def mock_store(*args, **kwargs):
                return "memory_id"
            mock_memory.store = mock_store
            mock_get_memory.return_value = mock_memory
            
            result = await memory_service.store_memory(
                crew_id=1,
                content="Important insight",
                memory_type="long_term",
                content_type="insight",
                metadata={"importance": 0.9}
            )
            
            assert result == "memory_id"
            # Note: We can't easily assert on async mock calls, but the test passing means it worked
    
    @pytest.mark.asyncio
    async def test_entity_memory_storage(self, memory_service):
        """Test storing to entity memory."""
        # Mock the entity memory instance
        with patch.object(memory_service, 'get_entity_memory') as mock_get_memory:
            mock_memory = Mock()
            
            async def mock_store(*args, **kwargs):
                return "entity_id"
            mock_memory.store = mock_store
            mock_get_memory.return_value = mock_memory
            
            result = await memory_service.store_memory(
                crew_id=1,
                content="Entity information",
                memory_type="entity",
                content_type="entity",
                metadata={"entity_type": "person", "entity_name": "John"}
            )
            
            assert result == "entity_id"
            # Note: We can't easily assert on async mock calls, but the test passing means it worked
    
    def test_invalid_memory_type(self, memory_service):
        """Test handling of invalid memory type."""
        with pytest.raises(ValueError, match="Unknown memory type"):
            asyncio.run(memory_service.store_memory(
                crew_id=1,
                content="Test",
                memory_type="invalid_type",
                content_type="text"
            )) 