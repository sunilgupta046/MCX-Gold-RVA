from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime


class BhavcopyRecordBase(BaseModel):
    trade_date: date
    symbol: str
    expiry_date: date
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: Optional[float] = None
    settle_price: float
    volume_lots: int = 0
    volume_value_lakhs: float = 0.0
    open_interest: int = 0
    change_in_oi: int = 0
    is_demo: bool = False
    data_source: str = "MCX_PUBLIC_BHAVCOPY"


class BhavcopyRecordResponse(BhavcopyRecordBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BhavcopyIngestionResult(BaseModel):
    success: bool
    message: str
    records_processed: int
    dates_covered: List[str]
    is_demo: bool
