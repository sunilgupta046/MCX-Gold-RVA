import uuid
from datetime import timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ingestion_log import IngestionLog
from app.schemas.ingestion import (
    FetchDateRequest,
    FetchRangeRequest,
    IngestionLogResponse,
    IngestionSummaryResponse,
)
from app.services.bhavcopy_parser import (
    parse_requested_date,
    parse_and_validate_bhavcopy_csv,
)
from app.services.mcx_adapter import MCXBhavcopyAdapter

router = APIRouter(prefix="/ingestion", tags=["Bhavcopy Ingestion"])


@router.post("/fetch-date", response_model=IngestionLogResponse)
async def fetch_single_date(req: FetchDateRequest, db: Session = Depends(get_db)):
    """
    Fetches daily Bhavcopy for a specific date from official MCX source.
    Expects date in DD/MM/YYYY format.
    Validates requested date against returned date (Rule 9).
    """
    try:
        target_date = parse_requested_date(req.date_str)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    adapter = MCXBhavcopyAdapter()
    result = await adapter.fetch_daily_bhavcopy(target_date)
    log_entry = adapter.save_parsed_records(db, result, source_type="MCX_HTTP_FETCH")
    return log_entry


@router.post("/fetch-range", response_model=List[IngestionLogResponse])
async def fetch_date_range(req: FetchRangeRequest, db: Session = Depends(get_db)):
    """
    Fetches Bhavcopy across a historical date range from official MCX source.
    Iterates sequentially through requested trading dates.
    """
    try:
        start_d = parse_requested_date(req.start_date_str)
        end_d = parse_requested_date(req.end_date_str)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if start_d > end_d:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date.")

    if (end_d - start_d).days > 60:
        raise HTTPException(status_code=400, detail="Date range exceeds maximum limit of 60 days per batch.")

    adapter = MCXBhavcopyAdapter()
    batch_id = str(uuid.uuid4())
    logs = []

    curr = start_d
    while curr <= end_d:
        result = await adapter.fetch_daily_bhavcopy(curr, batch_id=batch_id)
        log_entry = adapter.save_parsed_records(db, result, source_type="MCX_HTTP_FETCH")
        logs.append(log_entry)
        curr += timedelta(days=1)

    return logs


@router.post("/upload", response_model=IngestionLogResponse)
async def upload_manual_bhavcopy(
    file: UploadFile = File(...),
    requested_date_str: Optional[str] = Query(None, description="Optional expected date in DD/MM/YYYY format for validation"),
    db: Session = Depends(get_db)
):
    """
    Manual CSV upload endpoint when official HTTP download is blocked by exchange firewall.
    Performs full parsing, whitespace trimming, compact expiry decoding, date validation, and deduplication.
    """
    content = await file.read()
    req_date = None
    if requested_date_str:
        try:
            req_date = parse_requested_date(requested_date_str)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid requested date: {str(e)}")

    parsed_result = parse_and_validate_bhavcopy_csv(
        csv_content=content,
        requested_date=req_date,
        filename=file.filename
    )

    adapter = MCXBhavcopyAdapter()
    log_entry = adapter.save_parsed_records(db, parsed_result, source_type="MANUAL_CSV_UPLOAD")
    return log_entry


@router.get("/status", response_model=IngestionSummaryResponse)
def get_ingestion_status(db: Session = Depends(get_db)):
    """
    Returns aggregated ingestion status summary, categorized counts, and recent import logs.
    """
    logs = db.query(IngestionLog).order_by(IngestionLog.created_at.desc()).limit(100).all()

    total_sessions = len(logs)
    successful = sum(1 for l in logs if l.status in ("SUCCESS", "PARTIAL"))
    rejected = sum(1 for l in logs if "REJECTED" in l.status)
    holidays = sum(1 for l in logs if l.status == "HOLIDAY_OR_WEEKEND")
    unavailable = sum(1 for l in logs if l.status in ("UNAVAILABLE_FILE", "MISSING_CONTRACTS"))
    network_errors = sum(1 for l in logs if l.status == "NETWORK_ERROR")
    total_records = sum(l.records_imported for l in logs)

    return IngestionSummaryResponse(
        total_sessions=total_sessions,
        successful_sessions=successful,
        rejected_sessions=rejected,
        holiday_sessions=holidays,
        unavailable_sessions=unavailable,
        network_error_sessions=network_errors,
        total_records_imported=total_records,
        recent_logs=logs
    )


@router.get("/logs", response_model=List[IngestionLogResponse])
def get_ingestion_logs(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Fetches detailed ingestion logs with optional status filter."""
    query = db.query(IngestionLog)
    if status:
        query = query.filter(IngestionLog.status == status.upper())
    return query.order_by(IngestionLog.created_at.desc()).limit(limit).all()
