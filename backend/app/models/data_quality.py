from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, JSON
from datetime import datetime
from app.database import Base


class DataQualityLog(Base):
    __tablename__ = "data_quality_logs"

    id = Column(Integer, primary_key=True, index=True)
    audit_date = Column(DateTime, default=datetime.utcnow)
    total_records = Column(Integer, default=0)
    distinct_dates = Column(Integer, default=0)
    contracts_checked = Column(Integer, default=0)
    missing_dates_detected = Column(Integer, default=0)
    zero_volume_days = Column(Integer, default=0)
    price_jump_anomalies = Column(Integer, default=0)
    overall_health_score = Column(Float, default=100.0)  # 0 to 100%
    status = Column(String(32), default="HEALTHY")       # HEALTHY, WARNING, CRITICAL
    details = Column(JSON, nullable=True)
