from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1 import crews, agents, llm_providers, health

app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    description="CrewAI Backend API for managing crews, agents, and executions",
    debug=settings.debug
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(
    crews.router,
    prefix=f"{settings.api_v1_str}/crews",
    tags=["crews"]
)
app.include_router(
    agents.router,
    prefix=f"{settings.api_v1_str}/agents",
    tags=["agents"]
)
app.include_router(
    llm_providers.router,
    prefix=f"{settings.api_v1_str}/llm-providers",
    tags=["llm-providers"]
)


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "Welcome to CrewAI Backend API",
        "version": "1.0.0",
        "docs": "/docs"
    }
