from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class AnomalyItem(BaseModel):
    date: str
    symbol: str
    anomaly_type: str
    description: str
    severity: str  # LOW, MEDIUM, HIGH


class DataQualityAuditResponse(BaseModel):
    audit_date: datetime
    total_records: int
    distinct_dates: int
    contracts_checked: int
    missing_dates_detected: int
    zero_volume_days: int
    price_jump_anomalies: int
    overall_health_score: float
    status: str
    anomalies: List[AnomalyItem]
    warnings: List[str]
    is_demo_dataset: bool
