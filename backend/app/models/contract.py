from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
from app.database import Base


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    trading_unit_grams = Column(Float, nullable=False)
    quotation_unit_grams = Column(Float, nullable=False)
    quotation_base_grams = Column(Float, nullable=True)   # Explicit quotation base (may differ from trading unit)
    purity = Column(Float, default=999.0)                  # Contract fineness e.g. 995 or 999
    tick_size = Column(Float, default=1.0)
    contract_multiplier = Column(Float, default=1.0)
    description = Column(String(256), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
