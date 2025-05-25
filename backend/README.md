# CrewAI Backend

A comprehensive FastAPI-based backend system for managing CrewAI crews and agents.

## Phase 1 Features

This is the initial implementation (Phase 1) that includes:

- ✅ FastAPI application setup with Swagger documentation
- ✅ PostgreSQL database connection and SQLAlchemy models
- ✅ Basic CRUD operations for crews, agents, and LLM providers
- ✅ Pydantic schemas for request/response validation
- ✅ Environment configuration management
- ✅ Health check endpoint
- ✅ Comprehensive test suite

## Requirements

- Python 3.11+
- PostgreSQL (for production) or SQLite (for development/testing)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment configuration:
```bash
cp .env.example .env
```

5. Update the `.env` file with your database connection details.

## Running the Application

### Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Swagger Documentation: http://localhost:8000/docs
- ReDoc Documentation: http://localhost:8000/redoc

### Health Check

```bash
curl http://localhost:8000/health/
```

## API Endpoints

### Core Endpoints

- `GET /` - Root endpoint with API information
- `GET /health/` - Health check endpoint

### Crews

- `POST /api/v1/crews/` - Create a new crew
- `GET /api/v1/crews/` - List all crews
- `GET /api/v1/crews/{crew_id}` - Get crew by ID
- `PUT /api/v1/crews/{crew_id}` - Update crew
- `DELETE /api/v1/crews/{crew_id}` - Delete crew

### Agents

- `POST /api/v1/agents/` - Create a new agent
- `GET /api/v1/agents/` - List all agents
- `GET /api/v1/agents/{agent_id}` - Get agent by ID
- `PUT /api/v1/agents/{agent_id}` - Update agent
- `DELETE /api/v1/agents/{agent_id}` - Delete agent

### LLM Providers

- `POST /api/v1/llm-providers/` - Create a new LLM provider
- `GET /api/v1/llm-providers/` - List all LLM providers
- `GET /api/v1/llm-providers/{provider_id}` - Get LLM provider by ID
- `PUT /api/v1/llm-providers/{provider_id}` - Update LLM provider
- `DELETE /api/v1/llm-providers/{provider_id}` - Delete LLM provider

## Testing

Run the test suite:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=app --cov-report=html
```

## Database Models

### Crew
- Basic crew configuration and metadata
- Supports sequential and hierarchical processes
- Memory and verbosity settings

### Agent
- Agent roles, goals, and backstory
- Delegation and iteration controls
- Tool and LLM configuration support

### LLM Provider
- Multi-provider support (OpenAI, Anthropic, Ollama)
- Secure API key storage
- Model-specific configurations

### Execution
- Execution tracking and status
- Input/output storage
- Error handling and timing

## Environment Variables

See `.env.example` for all available configuration options:

- `DATABASE_URL` - PostgreSQL connection string
- `API_V1_STR` - API version prefix (default: /api/v1)
- `PROJECT_NAME` - Project name for documentation
- `DEBUG` - Enable debug mode
- `SECRET_KEY` - Security key for session management
- `LOG_LEVEL` - Logging level

## Development

This project follows Test-Driven Development (TDD) principles. All features are implemented with comprehensive test coverage.

### Project Structure

```
backend/
├── app/
│   ├── api/          # API endpoints
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   ├── config.py     # Configuration
│   ├── database.py   # Database setup
│   └── main.py       # FastAPI app
├── tests/            # Test suite
├── requirements.txt  # Dependencies
└── README.md        # This file
```

## Next Phases

Future phases will include:
- CrewAI integration and execution
- Custom memory implementation
- Task queuing system
- Redis caching
- WebSocket real-time updates
- Dynamic crew generation
- Monitoring and metrics

## Contributing

1. Write tests first for any new features
2. Ensure all tests pass before submitting
3. Follow Python best practices and PEP 8
4. Maintain test coverage above 85%
