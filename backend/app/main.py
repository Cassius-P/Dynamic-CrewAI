"""
Main FastAPI application with simplified monitoring.
"""
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from datetime import datetime
from scalar_fastapi import get_scalar_api_reference

# Add alembic imports for migration functionality
from alembic.config import Config
from alembic import command
from sqlalchemy.exc import OperationalError
import structlog

from app.config import settings
from app.api.v1 import (
    health, metrics, crews, agents, memory, 
    llm_providers, manager_agents
)
from app.database import get_db, engine
from app.services.metrics_service import MetricsService

# Setup logging
logger = structlog.get_logger()

# Global monitoring task
monitoring_task = None

def run_migrations():
    """Run database migrations at startup."""
    try:
        logger.info("🔄 Running database migrations...")
        
        # Get the alembic.ini path
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_cfg_path = os.path.join(backend_dir, "alembic.ini")
        
        if not os.path.exists(alembic_cfg_path):
            logger.error(f"❌ Alembic config not found at: {alembic_cfg_path}")
            raise FileNotFoundError(f"Alembic configuration file not found: {alembic_cfg_path}")
        
        # Create Alembic configuration
        alembic_cfg = Config(alembic_cfg_path)
        
        # Override the database URL with our settings
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
        
        # Test database connection first
        with engine.connect() as conn:
            logger.info("✅ Database connection successful")
        
        # Run migrations to head
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Database migrations completed successfully")
        
    except OperationalError as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error("Please ensure PostgreSQL is running and accessible")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        # In development, we might want to continue anyway
        if settings.environment == "development":
            logger.warning("⚠️ Continuing in development mode despite migration failure")
        else:
            sys.exit(1)

async def run_monitoring_background():
    """Background task to run monitoring cycles periodically."""
    metrics_service = MetricsService()
    
    while True:
        try:
            # Get database session
            db = next(get_db())
            
            # Run monitoring cycle
            await metrics_service.run_monitoring_cycle(db)
            
            # Close database session
            db.close()
            
            # Wait for next cycle (5 minutes)
            await asyncio.sleep(300)
            
        except Exception as e:
            print(f"Error in monitoring background task: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global monitoring_task
    
    # Startup
    print("🚀 Starting CrewAI Backend with simplified monitoring...")
    
    # Run migrations
    run_migrations()
    
    # Start monitoring background task
    monitoring_task = asyncio.create_task(run_monitoring_background())
    print("📊 Monitoring background task started")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down CrewAI Backend...")
    
    # Cancel monitoring task
    if monitoring_task:
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        print("📊 Monitoring background task stopped")

app = FastAPI(
    title=settings.project_name,
    description="CrewAI Backend API with simplified monitoring",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # Disable default Swagger UI
    redoc_url=None  # Disable ReDoc
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])
app.include_router(crews.router, prefix="/api/v1/crews", tags=["crews"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(manager_agents.router, prefix="/api/v1/manager-agents", tags=["manager-agents"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["memory"])
app.include_router(llm_providers.router, prefix="/api/v1/llm-providers", tags=["llm-providers"])

@app.get("/")
async def root():
    """Root endpoint."""
    return JSONResponse({
        "message": "CrewAI Backend API",
        "version": "1.0.0",
        "status": "running",
        "monitoring": "simplified",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.get("/docs", include_in_schema=False)
async def scalar_docs():
    """Custom API documentation endpoint using Scalar."""
    return get_scalar_api_reference(
        openapi_url=app.openapi_url or "/openapi.json",
        title=app.title,
    )
