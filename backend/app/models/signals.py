from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, Text
from datetime import datetime
from app.database import Base


class RVASignal(Base):
    __tablename__ = "rva_signals"

    id = Column(Integer, primary_key=True, index=True)
    signal_date = Column(Date, index=True, nullable=False)
    pair_name = Column(String(64), index=True, nullable=False)
    base_symbol = Column(String(32), nullable=False)
    quote_symbol = Column(String(32), nullable=False)
    
    # Contract Expiry Dates & Normalized Settlement Prices
    base_expiry_date = Column(Date, nullable=True)
    quote_expiry_date = Column(Date, nullable=True)
    base_normalized_price = Column(Float, nullable=True)     # Standardized ₹/10g
    quote_normalized_price = Column(Float, nullable=True)    # Standardized ₹/10g
    adjusted_spread = Column(Float, nullable=True)           # Carry-adjusted spread ₹/10g

    # Action & Conviction: LONG_BASE_SHORT_QUOTE, SHORT_BASE_LONG_QUOTE, CONVERGENCE, NEUTRAL
    action = Column(String(64), nullable=False)
    strength = Column(String(16), default="MEDIUM")          # LOW, MEDIUM, HIGH, EXTREME
    z_score = Column(Float, nullable=False)
    spread_value_per_10g = Column(Float, nullable=False)
    target_spread = Column(Float, nullable=False)
    stop_loss_spread = Column(Float, nullable=True)

    # Edge, Costs & 2.5x Coverage Ratio
    gross_mispricing_bps = Column(Float, nullable=False)     # Legacy/compat bps
    est_roundtrip_cost_bps = Column(Float, nullable=False)   # Legacy/compat bps
    net_edge_bps = Column(Float, nullable=False)             # Legacy/compat bps

    expected_gross_edge_bps = Column(Float, nullable=True)
    expected_gross_edge_inr = Column(Float, nullable=True)
    estimated_costs_bps = Column(Float, nullable=True)
    estimated_costs_inr = Column(Float, nullable=True)
    expected_net_edge_bps = Column(Float, nullable=True)
    expected_net_edge_inr = Column(Float, nullable=True)
    cost_coverage_ratio = Column(Float, nullable=True)       # gross_edge / estimated_costs (must >= 2.5)

    # Microstructure, Expiry & Liquidity Diagnostics
    days_to_expiry = Column(Integer, nullable=True)
    avg_volume = Column(Float, nullable=True)
    base_volume = Column(Float, nullable=True)
    quote_volume = Column(Float, nullable=True)
    base_oi = Column(Float, nullable=True)
    quote_oi = Column(Float, nullable=True)
    base_dte = Column(Integer, nullable=True)
    quote_dte = Column(Integer, nullable=True)

    liquidity_status = Column(String(32), default="ADEQUATE")  # ADEQUATE, LOW_VOLUME, LOW_OI
    expiry_status = Column(String(32), default="ACTIVE")        # ACTIVE, EXPIRY_LOCKOUT, EXPIRED

    # Qualification & Alert Statuses
    # Statuses: QUALIFIED_FOR_REVIEW, NO_SIGNAL, INSUFFICIENT_DATA, LIQUIDITY_WARNING, EXPIRY_LOCKOUT
    status = Column(String(32), default="QUALIFIED_FOR_REVIEW")
    expiry_eligible = Column(Boolean, default=True)            # False if DTE <= 5
    liquidity_qualified = Column(Boolean, default=True)        # False if volume/OI < threshold
    is_qualified = Column(Boolean, default=True)               # True only if meets all criteria

    # Audit & Rejection Tracking
    rejection_reason = Column(String(128), nullable=True)
    rejection_reasons_json = Column(Text, nullable=True)
    signal_explanation = Column(Text, nullable=True)
    rational = Column(Text, nullable=True)
    disclaimer = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        if "rejection_reasons" in kwargs:
            reasons = kwargs.pop("rejection_reasons")
            if "rejection_reasons_json" not in kwargs and isinstance(reasons, list):
                import json
                kwargs["rejection_reasons_json"] = json.dumps(reasons)
        super().__init__(**kwargs)

    @property
    def rejection_reasons(self):
        if self.rejection_reasons_json:
            try:
                import json
                return json.loads(self.rejection_reasons_json)
            except Exception:
                pass
        return [self.rejection_reason] if self.rejection_reason else []

