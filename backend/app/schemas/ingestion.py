from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime


class FetchDateRequest(BaseModel):
    date_str: str = Field(..., description="Target trading date in DD/MM/YYYY format (e.g. 21/10/2026)")


class FetchRangeRequest(BaseModel):
    start_date_str: str = Field(..., description="Start trading date in DD/MM/YYYY format")
    end_date_str: str = Field(..., description="End trading date in DD/MM/YYYY format")


class IngestionLogResponse(BaseModel):
    id: int
    batch_id: str
    requested_date: Optional[date] = None
    requested_date_str: Optional[str] = None
    returned_date: Optional[date] = None
    returned_date_str: Optional[str] = None
    source_type: str
    status: str
    records_imported: int
    contracts_found: Optional[List[str]] = []
    missing_contracts: Optional[List[str]] = []
    error_message: Optional[str] = None
    validation_errors: Optional[Any] = None
    raw_file_name: Optional[str] = None
    raw_file_size: Optional[int] = None
    http_status_code: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngestionSummaryResponse(BaseModel):
    total_sessions: int
    successful_sessions: int
    rejected_sessions: int
    holiday_sessions: int
    unavailable_sessions: int
    network_error_sessions: int
    total_records_imported: int
    recent_logs: List[IngestionLogResponse]
