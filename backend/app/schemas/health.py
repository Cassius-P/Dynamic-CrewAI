from pydantic import BaseModel
from typing import Dict, Any


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    database: str
    timestamp: str
    details: Dict[str, Any] = {}
