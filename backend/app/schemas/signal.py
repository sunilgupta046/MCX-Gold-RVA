from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime


class SignalResponse(BaseModel):
    id: int
    signal_date: date
    pair_name: str
    base_symbol: str
    quote_symbol: str
    
    # Contract Expiries & Normalized Prices
    base_expiry_date: Optional[date] = None
    quote_expiry_date: Optional[date] = None
    base_normalized_price: Optional[float] = None
    quote_normalized_price: Optional[float] = None
    adjusted_spread: Optional[float] = None

    action: str
    strength: str
    z_score: float
    spread_value_per_10g: float
    target_spread: float
    stop_loss_spread: Optional[float] = None
    
    # Edges, Costs & 2.5x Coverage
    gross_mispricing_bps: float
    est_roundtrip_cost_bps: float
    net_edge_bps: float
    expected_gross_edge_bps: Optional[float] = None
    expected_gross_edge_inr: Optional[float] = None
    estimated_costs_bps: Optional[float] = None
    estimated_costs_inr: Optional[float] = None
    expected_net_edge_bps: Optional[float] = None
    expected_net_edge_inr: Optional[float] = None
    cost_coverage_ratio: Optional[float] = None

    # Diagnostics
    days_to_expiry: Optional[int] = None
    base_dte: Optional[int] = None
    quote_dte: Optional[int] = None
    avg_volume: Optional[float] = None
    base_volume: Optional[float] = None
    quote_volume: Optional[float] = None
    base_oi: Optional[float] = None
    quote_oi: Optional[float] = None
    liquidity_status: Optional[str] = "ADEQUATE"
    expiry_status: Optional[str] = "ACTIVE"
    expiry_eligible: Optional[bool] = True
    liquidity_qualified: Optional[bool] = True
    is_qualified: Optional[bool] = True

    # Audit & Explanation
    status: str
    rejection_reason: Optional[str] = None
    rejection_reasons: Optional[List[str]] = []
    rejection_reasons_json: Optional[str] = None
    signal_explanation: Optional[str] = None
    rational: Optional[str] = None
    disclaimer: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateOpportunity(BaseModel):
    pair_name: str
    base_symbol: str
    quote_symbol: str
    signal_date: date
    base_expiry_date: Optional[date] = None
    quote_expiry_date: Optional[date] = None
    base_normalized_price: float
    quote_normalized_price: float
    adjusted_spread: float
    action: str
    strength: str
    z_score: float
    target_spread: float
    stop_loss_spread: Optional[float] = None
    expected_gross_edge_bps: float
    expected_gross_edge_inr: float
    estimated_costs_bps: float
    estimated_costs_inr: float
    expected_net_edge_bps: float
    expected_net_edge_inr: float
    cost_coverage_ratio: float
    days_to_expiry: Optional[int] = None
    base_dte: Optional[int] = None
    quote_dte: Optional[int] = None
    base_volume: Optional[float] = None
    quote_volume: Optional[float] = None
    base_oi: Optional[float] = None
    quote_oi: Optional[float] = None
    liquidity_status: str
    expiry_status: str
    expiry_eligible: bool
    liquidity_qualified: bool
    is_qualified: bool
    status: str
    rejection_reason: Optional[str] = None
    rejection_reasons: List[str] = []
    signal_explanation: str
    disclaimer: str


class CandidateEvaluationResponse(BaseModel):
    as_of_date: Optional[date] = None
    total_candidates_evaluated: int
    qualified_count: int
    rejected_count: int
    status_summary: dict
    candidates: List[CandidateOpportunity]
    disclaimer: str


class AlertHistoryItem(BaseModel):
    id: int
    signal_date: date
    pair_name: str
    base_symbol: str
    quote_symbol: str
    base_expiry_date: Optional[date] = None
    quote_expiry_date: Optional[date] = None
    base_normalized_price: Optional[float] = None
    quote_normalized_price: Optional[float] = None
    adjusted_spread: Optional[float] = None
    z_score: float
    expected_gross_edge_bps: Optional[float] = None
    estimated_costs_bps: Optional[float] = None
    expected_net_edge_bps: Optional[float] = None
    cost_coverage_ratio: Optional[float] = None
    liquidity_status: Optional[str] = "ADEQUATE"
    expiry_status: Optional[str] = "ACTIVE"
    status: str
    is_qualified: bool
    rejection_reason: Optional[str] = None
    rejection_reasons: Optional[List[str]] = []
    signal_explanation: Optional[str] = None
    disclaimer: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertHistoryResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AlertHistoryItem]

