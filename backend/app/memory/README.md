# CrewAI Memory System

A comprehensive, PostgreSQL-backed memory system for CrewAI that provides persistent, intelligent memory capabilities across crew executions.

## Overview

The CrewAI Memory System implements three types of memory:

- **Short-Term Memory**: Temporary storage for recent interactions and context
- **Long-Term Memory**: Persistent storage for important insights and learnings
- **Entity Memory**: Structured storage for entities (people, places, concepts) and their relationships

## Architecture

### Core Components

```
app/memory/
├── base_memory.py          # Abstract base classes and interfaces
├── short_term_memory.py    # Short-term memory implementation
├── long_term_memory.py     # Long-term memory implementation
├── entity_memory.py        # Entity memory and relationship management
└── __init__.py            # Memory system exports

app/services/
└── memory_service.py       # Unified memory service interface

app/integrations/
└── crewai_memory.py       # CrewAI framework integration

app/models/
└── memory.py              # SQLAlchemy database models
```

### Database Schema

The memory system uses PostgreSQL with pgvector extension for vector similarity search:

- `memory_configurations`: Per-crew memory settings
- `short_term_memories`: Temporary memories with expiration
- `long_term_memories`: Persistent memories with importance scoring
- `entity_memories`: Entity information and attributes
- `entity_relationships`: Relationships between entities
- `memory_cleanup_logs`: Cleanup operation tracking

## Features

### 🧠 Intelligent Memory Types

- **Short-Term Memory**: Context-aware temporary storage
- **Long-Term Memory**: Importance-based persistent storage
- **Entity Memory**: Structured entity tracking with relationships

### 🔍 Vector Similarity Search

- OpenAI embeddings for semantic similarity
- Configurable similarity thresholds
- Efficient vector indexing with pgvector

### 🔄 Automatic Memory Management

- Configurable retention policies
- Automatic cleanup of expired memories
- Memory consolidation from short-term to long-term

### 📊 Memory Analytics

- Usage statistics and metrics
- Memory utilization tracking
- Cleanup operation logging

### 🔧 CrewAI Integration

- Drop-in replacement for CrewAI's built-in memory
- Compatible with existing CrewAI workflows
- Agent-specific memory isolation

## Quick Start

### 1. Basic Usage with CrewAI

```python
from app.integrations.crewai_memory import create_crew_memory

# Create memory adapter for a crew
memory = create_crew_memory(crew_id=1)

# Store memories
from app.integrations.crewai_memory import MemoryItem

memory.store_short_term(MemoryItem(
    content="User prefers detailed explanations",
    metadata={"type": "preference"}
))

memory.store_long_term(MemoryItem(
    content="Successfully completed data analysis task",
    metadata={"importance": 0.8, "task_type": "analysis"}
))

# Retrieve memories
recent_context = memory.get_short_term_memory("user preferences")
insights = memory.get_long_term_memory("data analysis")
```

### 2. Agent-Specific Memory

```python
from app.integrations.crewai_memory import create_agent_memory

# Create memory for specific agent
agent_memory = create_agent_memory(crew_id=1, agent_id=42)

# Agent memories are automatically tagged with agent_id
agent_memory.store(MemoryItem("Agent-specific observation"))
```

### 3. Direct Memory Service Usage

```python
from app.services.memory_service import MemoryService
from app.database import get_db

# Initialize service
db = next(get_db())
memory_service = MemoryService(db)

# Store memory
await memory_service.store_memory(
    crew_id=1,
    content="Important insight",
    memory_type="long_term",
    content_type="insight",
    metadata={"importance": 0.9}
)

# Retrieve memories
results = await memory_service.retrieve_memories(
    crew_id=1,
    query="data analysis",
    memory_types=["long_term"],
    limit=10
)
```

## Configuration

### Memory Configuration

Each crew has configurable memory settings:

```python
{
    "short_term_retention_hours": 24,      # How long to keep short-term memories
    "short_term_max_entries": 100,         # Maximum short-term memory entries
    "long_term_consolidation_threshold": 0.7,  # Threshold for promoting to long-term
    "long_term_max_entries": 1000,         # Maximum long-term memory entries
    "entity_confidence_threshold": 0.6,    # Minimum confidence for entity extraction
    "entity_similarity_threshold": 0.8,    # Threshold for entity deduplication
    "embedding_provider": "openai",        # Embedding service provider
    "embedding_model": "text-embedding-3-small",  # Embedding model
    "cleanup_enabled": True,               # Enable automatic cleanup
    "cleanup_interval_hours": 24          # Cleanup frequency
}
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/crewai_memory

# OpenAI (for embeddings)
OPENAI_API_KEY=your_openai_api_key
```

## Memory Types

### Short-Term Memory

Temporary storage for recent interactions and context:

- **Retention**: Configurable (default: 24 hours)
- **Capacity**: Limited by max entries
- **Use Cases**: Conversation context, recent actions, temporary state

```python
# Store short-term memory
memory.store_short_term(MemoryItem(
    content="User asked about quarterly sales",
    metadata={
        "agent_id": 1,
        "execution_id": 123,
        "relevance_score": 0.8
    }
))
```

### Long-Term Memory

Persistent storage for important insights and learnings:

- **Retention**: Permanent (until manually cleared)
- **Importance Scoring**: 0.0 to 1.0 scale
- **Use Cases**: Learned patterns, successful strategies, domain knowledge

```python
# Store long-term memory
memory.store_long_term(MemoryItem(
    content="Customer prefers email communication over phone",
    metadata={
        "importance": 0.9,
        "tags": ["customer_preference", "communication"],
        "source_execution_id": 123
    }
))
```

### Entity Memory

Structured storage for entities and their relationships:

- **Entity Types**: People, places, concepts, etc.
- **Attributes**: Flexible JSON storage
- **Relationships**: Typed connections between entities

```python
# Store entity memory
memory.store_entity(MemoryItem(
    content="John Smith is the project manager",
    metadata={
        "entity_type": "person",
        "entity_name": "John Smith",
        "attributes": {
            "role": "project_manager",
            "department": "engineering",
            "contact": "john@company.com"
        },
        "confidence": 0.95
    }
))
```

## Advanced Features

### Memory Consolidation

Automatic promotion of important short-term memories to long-term storage:

```python
# Manual consolidation
stats = await memory_service.consolidate_memories(crew_id=1)
print(f"Consolidated {stats['consolidated']} memories")
```

### Memory Cleanup

Automatic cleanup of expired and low-importance memories:

```python
# Manual cleanup
stats = await memory_service.cleanup_memories(crew_id=1)
print(f"Cleaned up {stats['total_cleaned']} memories")
```

### Memory Statistics

Track memory usage and performance:

```python
# Get memory statistics
stats = memory.get_stats()
print(f"Total memories: {stats['counts']['total']}")
print(f"Memory utilization: {stats['utilization']}")
```

### Entity Relationships

Track relationships between entities:

```python
# Add entity relationship
await memory_service.add_entity_relationship(
    crew_id=1,
    source_entity_id="person_1",
    target_entity_id="project_1",
    relationship_type="manages",
    strength=0.9,
    context="John manages the AI project"
)
```

## Database Migrations

The memory system includes Alembic migrations for database schema management:

```bash
# Run migrations
cd backend
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Add new memory feature"
```

## Testing

Comprehensive test suite covering all memory functionality:

```bash
# Run memory tests
pytest tests/test_memory/ -v

# Run integration tests
pytest tests/test_memory/test_memory_integration.py -v
```

## Performance Considerations

### Vector Search Optimization

- Use appropriate embedding dimensions
- Configure pgvector indexes for your query patterns
- Consider batch operations for bulk memory storage

### Memory Cleanup

- Configure appropriate retention policies
- Monitor memory usage with statistics
- Use cleanup logs to track performance

### Database Optimization

- Regular VACUUM and ANALYZE operations
- Monitor index usage and performance
- Consider partitioning for large datasets

## Troubleshooting

### Common Issues

1. **Embedding Generation Failures**
   - Check OpenAI API key configuration
   - Verify network connectivity
   - Monitor API rate limits

2. **Slow Vector Searches**
   - Check pgvector index configuration
   - Consider reducing embedding dimensions
   - Optimize similarity thresholds

3. **Memory Cleanup Issues**
   - Check cleanup configuration
   - Monitor cleanup logs
   - Verify database permissions

### Debugging

Enable debug logging for detailed memory operations:

```python
import logging
logging.getLogger('app.memory').setLevel(logging.DEBUG)
logging.getLogger('app.services.memory_service').setLevel(logging.DEBUG)
```

## Contributing

When contributing to the memory system:

1. Follow the existing architecture patterns
2. Add comprehensive tests for new features
3. Update documentation and examples
4. Consider performance implications
5. Test with realistic data volumes

## License

This memory system is part of the CrewAI backend project and follows the same licensing terms. 