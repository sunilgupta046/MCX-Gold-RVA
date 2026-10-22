from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db, init_db
from app.config import settings
from app.schemas.health import HealthResponse
from app.models.bhavcopy import BhavcopyRecord

router = APIRouter(prefix="", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint providing platform diagnostics and status."""
    try:
        init_db()
        count = db.query(BhavcopyRecord).count()
        db_status = "connected"
    except Exception as e:
        count = 0
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.VERSION,
        service=settings.PROJECT_NAME,
        database=db_status,
        records_count=count,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        metrics={
            "supported_contracts": ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"],
            "risk_free_rate": settings.ANNUAL_RISK_FREE_RATE,
            "storage_rate": settings.GOLD_STORAGE_INSURANCE_RATE,
        }
    )
