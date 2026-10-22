from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint, Index
from datetime import datetime
from app.database import Base


class NormalizedPrice(Base):
    __tablename__ = "normalized_prices"

    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, index=True, nullable=False)
    symbol = Column(String(32), index=True, nullable=False)
    expiry_date = Column(Date, nullable=False)
    raw_settle_price = Column(Float, nullable=False)
    price_per_gram = Column(Float, nullable=False)
    price_per_10g = Column(Float, nullable=False)
    price_per_pure_gram_999 = Column(Float, nullable=True)        # 999-purity normalized price per 1g
    price_per_pure_10g_999 = Column(Float, nullable=True)         # 999-purity normalized price per 10g
    days_to_expiry = Column(Integer, nullable=False)
    annualized_carry_rate = Column(Float, default=0.07)
    carry_rate_source = Column(String(64), default="FIXED_ASSUMPTION_7.0PCT")  # Labeled rate source
    carry_discount_factor = Column(Float, default=1.0)
    carry_adjusted_price_per_10g = Column(Float, nullable=False)
    carry_adjusted_price_pure_10g = Column(Float, nullable=True)  # 999-purity carry adjusted per 10g
    purity = Column(Float, default=999.0)                         # Contract purity fineness (995 or 999)
    quotation_base_grams = Column(Float, default=10.0)            # Quotation base in grams
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('trade_date', 'symbol', 'expiry_date', name='uix_norm_date_symbol_expiry'),
        Index('idx_norm_query', 'trade_date', 'symbol'),
    )
