from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, Text, JSON
from datetime import datetime
from app.database import Base


class IngestionLog(Base):
    __tablename__ = "ingestion_logs"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(64), index=True, nullable=False)
    requested_date = Column(Date, index=True, nullable=True)
    requested_date_str = Column(String(32), nullable=True)
    returned_date = Column(Date, nullable=True)
    returned_date_str = Column(String(32), nullable=True)
    source_type = Column(String(32), default="MCX_HTTP_FETCH")  # MCX_HTTP_FETCH, MANUAL_CSV_UPLOAD, DEMO_SYNTHETIC
    status = Column(String(64), nullable=False, index=True)      # SUCCESS, REJECTED, HOLIDAY_OR_WEEKEND, UNAVAILABLE, MALFORMED, NETWORK_ERROR, PARTIAL
    records_imported = Column(Integer, default=0)
    contracts_found = Column(JSON, default=list)                 # e.g., ["GOLDM", "GOLDPETAL"]
    missing_contracts = Column(JSON, default=list)               # e.g., ["GOLDTEN", "GOLDGUINEA"]
    error_message = Column(Text, nullable=True)
    validation_errors = Column(JSON, nullable=True)
    raw_file_name = Column(String(256), nullable=True)
    raw_file_size = Column(Integer, nullable=True)
    http_status_code = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
