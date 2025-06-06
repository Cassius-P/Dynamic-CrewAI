# CrewAI Backend Development Project

You are a senior Python developer tasked with building a comprehensive backend system for managing CrewAI crews and agents. You will develop this project using Test-Driven Development (TDD) principles across multiple phases.

## Core Requirements

Build a FastAPI-based backend that enables:
- **Static Crews**: User-managed agents and tools
- **Dynamic Crews**: AI-generated crews using specialized tools
- **Real-time Execution**: WebSocket updates for crew execution states
- **Memory System**: PostgreSQL-based short-term, long-term, and entity memory for CrewAI using pgvector for semantic search
- **Queue System**: Task parallelization and dependency management
- **Tool Registry**: Centralized tool management (CrewAI + custom tools)
- **Multi-LLM Support**: OpenAI, Anthropic, and Ollama integration
- **Caching Layer**: Redis for performance optimization
- **Monitoring**: Health checks and metrics collection

## Development Strategy

### TDD Approach
1. Write failing tests first for each feature
2. Implement minimal code to pass tests
3. Refactor while keeping tests green
4. **ALL TESTS MUST PASS** before proceeding to next phase

### Phase Progression Rules
- Each phase must be a **working version** with complete functionality for implemented features
- After completing each phase, run all tests and ensure 100% pass rate
- **PAUSE** after each phase completion and wait for explicit approval to continue
- If tests fail, debug and fix until all tests pass before pausing
- If uncertain about any implementation detail, **PAUSE** and ask for clarification

### Reference Documentation
- For CrewAI-specific questions, consult: https://docs.crewai.com/introduction
- Implement PostgreSQL memory classes as CrewAI doesn't provide them natively

## Project File Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── crews.py
│   │   │   ├── agents.py
│   │   │   ├── tools.py
│   │   │   ├── executions.py
│   │   │   ├── llm_providers.py
│   │   │   ├── health.py
│   │   │   └── metrics.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── crew_wrapper.py
│   │   ├── agent_wrapper.py
│   │   ├── llm_wrapper.py
│   │   ├── tool_registry.py
│   │   ├── dynamic_crew_generator.py
│   │   └── execution_engine.py
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── base_memory.py
│   │   ├── short_term_memory.py
│   │   ├── long_term_memory.py
│   │   └── entity_memory.py
│   ├── queue/
│   │   ├── __init__.py
│   │   ├── task_queue.py
│   │   ├── task_manager.py
│   │   └── dependency_resolver.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── crew.py
│   │   ├── agent.py
│   │   ├── execution.py
│   │   ├── memory.py
│   │   ├── llm_provider.py
│   │   └── metrics.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── crew.py
│   │   ├── agent.py
│   │   ├── execution.py
│   │   ├── memory.py
│   │   └── health.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── crew_service.py
│   │   ├── agent_service.py
│   │   ├── execution_service.py
│   │   ├── memory_service.py
│   │   ├── llm_service.py
│   │   └── metrics_service.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── custom_tools.py
│   │   └── tool_implementations/
│   │       ├── __init__.py
│   │       ├── web_search.py
│   │       ├── file_operations.py
│   │       └── data_analysis.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   ├── validation.py
│   │   ├── logging.py
│   │   └── websocket_manager.py
│   └── websocket/
│       ├── __init__.py
│       ├── connection_manager.py
│       └── events.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   │   ├── __init__.py
│   │   ├── test_crews.py
│   │   ├── test_agents.py
│   │   ├── test_executions.py
│   │   └── test_health.py
│   ├── test_core/
│   │   ├── __init__.py
│   │   ├── test_crew_wrapper.py
│   │   ├── test_agent_wrapper.py
│   │   ├── test_tool_registry.py
│   │   └── test_execution_engine.py
│   ├── test_memory/
│   │   ├── __init__.py
│   │   ├── test_short_term_memory.py
│   │   ├── test_long_term_memory.py
│   │   └── test_entity_memory.py
│   ├── test_queue/
│   │   ├── __init__.py
│   │   ├── test_task_queue.py
│   │   └── test_dependency_resolver.py
│   ├── test_services/
│   │   ├── __init__.py
│   │   ├── test_crew_service.py
│   │   ├── test_agent_service.py
│   │   └── test_execution_service.py
│   └── integration/
│       ├── __init__.py
│       ├── test_crew_execution.py
│       └── test_websocket.py
├── alembic/
│   ├── versions/
│   ├── env.py
│   ├── script.py.mako
│   └── alembic.ini
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.test.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── pytest.ini
```

## Required Libraries

```
fastapi
uvicorn
sqlalchemy
alembic
psycopg2-binary
pgvector
redis
celery
pydantic
python-multipart
websockets
crewai
openai
anthropic
ollama
pytest
pytest-asyncio
pytest-cov
httpx
factory-boy
fakeredis
testcontainers
python-dotenv
structlog
prometheus-client
```

## Development Phases

### Phase 1: Foundation & Basic CRUD
**Objective**: Establish project structure, database models, and basic API endpoints

**Features**:
- FastAPI application setup with Swagger documentation
- PostgreSQL database connection and SQLAlchemy models
- Basic CRUD operations for crews and agents
- Pydantic schemas for request/response validation
- Environment configuration management
- Health check endpoint

**Key Deliverables**:
- Working FastAPI server
- Database models for Crew, Agent, LLMProvider
- API endpoints: POST/GET/PUT/DELETE for crews and agents
- Comprehensive test suite for all CRUD operations

### Phase 2: CrewAI Integration
**Objective**: Implement CrewAI wrappers and basic crew execution

**Features**:
- CrewAI crew and agent wrapper classes
- LLM provider management (OpenAI, Anthropic, Ollama)
- Tool registry with CrewAI built-in tools
- Basic crew execution without memory or queuing
- Configuration-to-CrewAI object conversion

**Key Deliverables**:
- Functional crew execution from stored configurations
- LLM provider switching capability
- Tool registry listing available tools
- Execution tracking and basic logging

### Phase 3: Custom Memory Implementation
**Objective**: Implement PostgreSQL-backed memory system for CrewAI

**Features**:
- Custom memory classes implementing CrewAI memory interface
- Short-term memory (conversation context)
- Long-term memory (persistent knowledge)
- Entity memory (structured entity information)
- Memory retrieval and storage mechanisms

**Key Deliverables**:
- PostgreSQL memory backend fully integrated with CrewAI
- Memory persistence across crew executions
- Memory query and retrieval APIs
- Memory cleanup and management policies

### Phase 4: Queue System & Task Management
**Objective**: Implement task queuing and dependency resolution

**Features**:
- Celery-based task queue system
- Task dependency resolution (DAG-based)
- Manager agent support for crew coordination
- Parallel task execution capability
- Task retry and failure handling

**Key Deliverables**:
- Functional task queue with Redis backend
- Manager agent automatically assigned to dynamic crews
- Parallel execution of independent tasks
- Robust error handling and recovery

### Phase 5: Caching & Performance
**Objective**: Implement Redis caching and performance optimizations

**Features**:
- Redis caching layer for frequently accessed data
- Connection pooling for database and external APIs
- Query optimization and caching strategies
- Performance monitoring and metrics collection
- Resource limit enforcement

**Key Deliverables**:
- Significant performance improvements through caching
- Metrics collection for monitoring performance
- Resource usage monitoring and limits
- Optimized database queries

### Phase 6: Real-time Updates
**Objective**: Implement WebSocket support for real-time execution updates

**Features**:
- WebSocket connection management
- Real-time crew execution status updates
- Event-driven architecture for state changes
- Connection handling and reconnection logic
- Broadcasting execution progress to connected clients

**Key Deliverables**:
- WebSocket endpoints for real-time updates
- Event system for execution state changes
- Robust connection management
- Real-time execution monitoring

### Phase 7: Dynamic Crew Generation
**Objective**: Implement AI-powered dynamic crew creation

**Features**:
- Dynamic crew generator using LLM
- Automatic crew composition based on task requirements
- Intelligent agent and tool selection
- Dynamic crew optimization and validation
- Integration with existing crew execution pipeline

**Key Deliverables**:
- Functional dynamic crew generation
- Automatic crew optimization
- Seamless integration with static crews
- Comprehensive validation of generated crews

### Phase 8: Monitoring & Finalization
**Objective**: Complete monitoring system and final optimizations

**Features**:
- Comprehensive health check system
- Detailed metrics and analytics collection
- Alert system for failures and performance issues
- Final performance optimizations
- Complete API documentation
- Docker containerization

**Key Deliverables**:
- Full monitoring and alerting system
- Complete API documentation with examples
- Production-ready Docker configuration
- Comprehensive test coverage (>90%)
- Performance benchmarks and optimization

## Success Criteria for Each Phase

1. **All tests pass** (100% pass rate)
2. **API endpoints respond correctly** with proper status codes
3. **Database operations complete successfully** without errors
4. **Integration tests validate** end-to-end functionality
5. **Performance tests meet** acceptable thresholds
6. **Code coverage exceeds** 85% for each phase

## Response Guidelines

- **Be concise** in explanations and code comments
- **Show only relevant code** for the current task
- **Include test files** for every feature implemented
- **Use proper error handling** and validation
- **Follow Python best practices** and PEP 8 conventions
- **Implement proper logging** for debugging and monitoring

## Important Notes

- **Never version-pin** dependencies in requirements.txt
- **Use latest stable versions** compatible with Python 3.11
- **Implement proper input validation** for all API endpoints
- **Use design patterns** appropriate for each component
- **Maintain clean separation** of concerns between layers
- **Write comprehensive tests** before implementing features

## Getting Started

Begin with Phase 1. Create the basic project structure, implement the foundation components, and ensure all tests pass before requesting approval to proceed to Phase 2.

Remember: **PAUSE** after each phase completion and wait for explicit approval to continue to the next phase.