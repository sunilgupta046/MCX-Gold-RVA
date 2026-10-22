from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime


class HealthResponse(BaseModel):
    status: str
    version: str
    service: str
    database: str
    records_count: int
    environment: str
    timestamp: datetime
    metrics: Optional[Dict[str, Any]] = None
