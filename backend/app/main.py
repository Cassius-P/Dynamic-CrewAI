"""
Main FastAPI application with simplified monitoring.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

from app.config import settings
from app.api.v1 import (
    health, metrics, crews, agents, memory, 
    llm_providers
)
from app.database import get_db
from app.services.metrics_service import MetricsService

# Global monitoring task
monitoring_task = None

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
    lifespan=lifespan
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
