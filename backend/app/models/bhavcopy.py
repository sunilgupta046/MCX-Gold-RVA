from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, UniqueConstraint, Index
from datetime import datetime
from app.database import Base


class BhavcopyRecord(Base):
    __tablename__ = "bhavcopy_records"

    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, index=True, nullable=False)
    symbol = Column(String(32), index=True, nullable=False)
    expiry_date = Column(Date, index=True, nullable=False)
    open_price = Column(Float, nullable=True)
    high_price = Column(Float, nullable=True)
    low_price = Column(Float, nullable=True)
    close_price = Column(Float, nullable=True)
    settle_price = Column(Float, nullable=False)
    volume_lots = Column(Integer, default=0)
    volume_value_lakhs = Column(Float, default=0.0)
    open_interest = Column(Integer, default=0)
    change_in_oi = Column(Integer, default=0)
    is_demo = Column(Boolean, default=False, nullable=False)
    data_source = Column(String(64), default="MCX_PUBLIC_BHAVCOPY")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('trade_date', 'symbol', 'expiry_date', name='uix_date_symbol_expiry'),
        Index('idx_bhavcopy_query', 'trade_date', 'symbol'),
    )
