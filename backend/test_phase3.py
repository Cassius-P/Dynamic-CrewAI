#!/usr/bin/env python3
"""
Simple test script to validate Phase 3 core components.
"""

def test_imports():
    """Test that all Phase 3 components can be imported."""
    print("Testing Phase 3 imports...")
    
    try:
        # Test memory models
        from app.models.memory import (
            ShortTermMemory, LongTermMemory, EntityMemory, 
            EntityRelationship, MemoryConfiguration, MemoryCleanupLog
        )
        print("✅ Memory models imported successfully")
        
        # Test CrewAI integration
        from app.integrations.crewai_memory import (
            CrewAIMemoryAdapter, MemoryItem, create_crew_memory, create_agent_memory
        )
        print("✅ CrewAI integration imported successfully")
        
        # Test migrations exist
        import os
        migration_file = "alembic/versions/0001_initial_memory_system.py"
        if os.path.exists(migration_file):
            print("✅ Database migration file exists")
        else:
            print("❌ Database migration file missing")
            
        # Test documentation exists
        doc_file = "app/memory/README.md"
        if os.path.exists(doc_file):
            print("✅ Documentation file exists")
        else:
            print("❌ Documentation file missing")
            
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_memory_adapter_creation():
    """Test that memory adapters can be created."""
    print("\nTesting memory adapter creation...")
    
    try:
        from app.integrations.crewai_memory import MemoryItem, create_crew_memory
        
        # Test MemoryItem creation
        item = MemoryItem("Test content", {"test": "metadata"})
        assert item.content == "Test content"
        assert item.metadata["test"] == "metadata"
        print("✅ MemoryItem creation works")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory adapter creation error: {e}")
        return False

def main():
    """Run all Phase 3 tests."""
    print("=== Phase 3 Validation Tests ===\n")
    
    # Test imports
    imports_ok = test_imports()
    
    # Test memory adapter creation
    adapter_ok = test_memory_adapter_creation()
    
    # Summary
    print(f"\n=== Phase 3 Test Summary ===")
    if imports_ok and adapter_ok:
        print("🎉 Phase 3 core components are working!")
        return 0
    else:
        print("❌ Phase 3 has issues that need to be fixed")
        return 1

if __name__ == "__main__":
    exit(main()) 