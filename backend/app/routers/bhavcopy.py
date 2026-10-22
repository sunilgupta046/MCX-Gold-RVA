from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.database import get_db
from app.models.bhavcopy import BhavcopyRecord
from app.schemas.bhavcopy import BhavcopyRecordResponse, BhavcopyIngestionResult
from app.services.ingestion import generate_synthetic_demo_bhavcopy, parse_and_ingest_csv

router = APIRouter(prefix="/bhavcopy", tags=["Bhavcopy"])


@router.get("", response_model=List[BhavcopyRecordResponse])
def get_bhavcopy_records(
    symbol: Optional[str] = Query(None, description="Filter by contract symbol (e.g. GOLDM)"),
    start_date: Optional[date] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="End date YYYY-MM-DD"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Fetches ingested Bhavcopy settlement data records."""
    query = db.query(BhavcopyRecord)
    if symbol:
        query = query.filter(BhavcopyRecord.symbol == symbol.upper())
    if start_date:
        query = query.filter(BhavcopyRecord.trade_date >= start_date)
    if end_date:
        query = query.filter(BhavcopyRecord.trade_date <= end_date)

    return query.order_by(BhavcopyRecord.trade_date.desc(), BhavcopyRecord.symbol.asc()).limit(limit).all()


@router.get("/dates")
def get_bhavcopy_dates(db: Session = Depends(get_db)):
    """Returns available trade dates in the database."""
    dates = (
        db.query(BhavcopyRecord.trade_date)
        .distinct()
        .order_by(BhavcopyRecord.trade_date.desc())
        .all()
    )
    return [d[0] for d in dates]


@router.post("/seed-demo", response_model=BhavcopyIngestionResult)
def seed_demo(days: int = Query(90, ge=10, le=365), db: Session = Depends(get_db)):
    """
    Seeds realistic synthetic demo market data for development & testing.
    Strictly tagged with `is_demo=True` and clear provenance.
    """
    return generate_synthetic_demo_bhavcopy(db, days=days)


@router.post("/upload", response_model=BhavcopyIngestionResult)
async def upload_bhavcopy(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Uploads and ingests a real public MCX Bhavcopy CSV file."""
    contents = await file.read()
    return parse_and_ingest_csv(db, contents, file.filename)
