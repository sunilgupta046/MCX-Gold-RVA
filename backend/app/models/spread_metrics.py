from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint, Index
from datetime import datetime
from app.database import Base


class SpreadMetric(Base):
    __tablename__ = "spread_metrics"

    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, index=True, nullable=False)
    pair_name = Column(String(64), index=True, nullable=False)  # e.g., "GOLDM_vs_GOLDPETAL"
    base_symbol = Column(String(32), nullable=False)
    quote_symbol = Column(String(32), nullable=False)
    raw_spread_per_10g = Column(Float, nullable=False)
    carry_adjusted_spread_per_10g = Column(Float, nullable=False)
    normalized_spread_per_pure_10g_999 = Column(Float, nullable=True)    # 999 purity basis spread
    carry_adjusted_spread_pure_10g = Column(Float, nullable=True)        # 999 purity carry-adjusted spread
    spread_pct = Column(Float, nullable=False)
    rolling_mean_20d = Column(Float, nullable=True)
    rolling_std_20d = Column(Float, nullable=True)
    z_score = Column(Float, nullable=True)
    percentile_rank = Column(Float, nullable=True)
    half_life_days = Column(Float, nullable=True)
    correlation_30d = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('trade_date', 'pair_name', name='uix_spread_date_pair'),
        Index('idx_spread_query', 'trade_date', 'pair_name'),
    )
