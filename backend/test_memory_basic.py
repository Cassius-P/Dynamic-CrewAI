#!/usr/bin/env python3
"""
Basic memory integration test focusing on CrewAI adapter.
"""

def test_crewai_adapter_basic():
    """Test basic CrewAI adapter functionality."""
    print("Testing CrewAI adapter basic functionality...")
    
    try:
        from app.integrations.crewai_memory import MemoryItem, CrewAIMemoryAdapter
        from unittest.mock import Mock
        
        # Create a mock database session
        mock_db = Mock()
        
        # Create adapter
        adapter = CrewAIMemoryAdapter(crew_id=1, db_session=mock_db)
        print("✅ CrewAI adapter created successfully")
        
        # Test MemoryItem
        item = MemoryItem("Test memory", {"type": "test"})
        assert item.content == "Test memory"
        assert item.metadata["type"] == "test"
        print("✅ MemoryItem works correctly")
        
        # Test adapter attributes
        assert adapter.crew_id == 1
        assert adapter.db_session == mock_db
        print("✅ Adapter attributes correct")
        
        return True
        
    except Exception as e:
        print(f"❌ CrewAI adapter test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_factory_functions():
    """Test factory functions."""
    print("\nTesting factory functions...")
    
    try:
        from app.integrations.crewai_memory import create_crew_memory, create_agent_memory
        from unittest.mock import patch
        
        # Mock the database session
        from unittest.mock import Mock
        with patch('app.integrations.crewai_memory.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = iter([mock_db])
            
            # Test crew memory factory
            crew_memory = create_crew_memory(crew_id=1)
            assert crew_memory.crew_id == 1
            print("✅ create_crew_memory works")
            
            # Test agent memory factory (with additional mocking)
            with patch('app.integrations.crewai_memory.CrewAIMemoryAdapter') as mock_adapter_class:
                mock_adapter = Mock()
                mock_adapter.crew_id = 1
                mock_adapter_class.return_value = mock_adapter
                
                agent_memory = create_agent_memory(crew_id=1, agent_id=42)
                assert mock_adapter_class.called
                print("✅ create_agent_memory works")
        
        return True
        
    except Exception as e:
        print(f"❌ Factory functions test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_types():
    """Test memory type methods exist."""
    print("\nTesting memory type methods...")
    
    try:
        from app.integrations.crewai_memory import CrewAIMemoryAdapter
        from unittest.mock import Mock
        
        mock_db = Mock()
        adapter = CrewAIMemoryAdapter(crew_id=1, db_session=mock_db)
        
        # Check that all expected methods exist
        methods = [
            'store', 'retrieve', 'search',
            'store_short_term', 'store_long_term', 'store_entity',
            'get_short_term_memory', 'get_long_term_memory', 'get_entity_memory',
            'clear', 'get_stats'
        ]
        
        for method in methods:
            assert hasattr(adapter, method), f"Method {method} missing"
            assert callable(getattr(adapter, method)), f"Method {method} not callable"
        
        print("✅ All required memory methods exist")
        return True
        
    except Exception as e:
        print(f"❌ Memory type methods test error: {e}")
        return False

def main():
    """Run all basic memory tests."""
    print("=== Basic Memory Integration Tests ===\n")
    
    # Run tests
    adapter_ok = test_crewai_adapter_basic()
    factory_ok = test_factory_functions()
    methods_ok = test_memory_types()
    
    # Summary
    print(f"\n=== Test Summary ===")
    if adapter_ok and factory_ok and methods_ok:
        print("🎉 Basic memory integration tests passed!")
        return 0
    else:
        print("❌ Some memory integration tests failed")
        return 1

if __name__ == "__main__":
    exit(main()) 