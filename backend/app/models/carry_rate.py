from sqlalchemy import Column, Integer, Float, Date, DateTime, String
from datetime import datetime
from app.database import Base


class CarryRateHistory(Base):
    """
    Stores historical annualized cost-of-carry rate inputs (financing rate + storage/insurance fee).
    When historical rates are unavailable for a date, the platform defaults to the
    fixed-rate assumption and explicitly labels it.
    """
    __tablename__ = "carry_rate_history"

    id = Column(Integer, primary_key=True, index=True)
    rate_date = Column(Date, unique=True, index=True, nullable=False)
    risk_free_rate = Column(Float, nullable=False)        # Annualized financing rate e.g. 0.065
    storage_rate = Column(Float, nullable=False)          # Annualized storage/insurance rate e.g. 0.005
    annualized_carry_rate = Column(Float, nullable=False) # Combined e.g. 0.070
    rate_source = Column(String(64), nullable=False)      # e.g. "HISTORICAL_RBI_REPO", "FIXED_ASSUMPTION_7.0PCT"
    created_at = Column(DateTime, default=datetime.utcnow)
