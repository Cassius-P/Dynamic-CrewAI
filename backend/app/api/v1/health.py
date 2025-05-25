from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from app.api.deps import get_db
from app.schemas.health import HealthResponse
from app.config import settings

router = APIRouter()


@router.get("/", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        database_status = "healthy"
    except Exception as e:
        database_status = f"unhealthy: {str(e)}"
    
    return HealthResponse(
        status="healthy" if database_status == "healthy" else "unhealthy",
        version="1.0.0",
        database=database_status,
        timestamp=datetime.utcnow().isoformat(),
        details={
            "project_name": settings.project_name,
            "debug": settings.debug
        }
    )
