from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import date


class NormalizedPriceResponse(BaseModel):
    trade_date: date
    symbol: str
    expiry_date: date
    raw_settle_price: float
    price_per_gram: float
    price_per_10g: float
    price_per_pure_gram_999: Optional[float] = None
    price_per_pure_10g_999: Optional[float] = None
    days_to_expiry: int
    annualized_carry_rate: Optional[float] = None
    carry_rate_source: Optional[str] = None
    carry_discount_factor: Optional[float] = None
    carry_adjusted_price_per_10g: float
    carry_adjusted_price_pure_10g: Optional[float] = None
    purity: Optional[float] = None
    quotation_base_grams: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class SpreadMetricResponse(BaseModel):
    trade_date: date
    pair_name: str
    base_symbol: str
    quote_symbol: str
    raw_spread_per_10g: float
    carry_adjusted_spread_per_10g: float
    normalized_spread_per_pure_10g_999: Optional[float] = None
    carry_adjusted_spread_pure_10g: Optional[float] = None
    spread_pct: float
    rolling_mean_20d: Optional[float] = None
    rolling_std_20d: Optional[float] = None
    z_score: Optional[float] = None
    percentile_rank: Optional[float] = None
    half_life_days: Optional[float] = None
    correlation_30d: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class CorrelationMatrixResponse(BaseModel):
    contracts: List[str]
    matrix: List[List[float]]
    start_date: date
    end_date: date


class CarryCurvePoint(BaseModel):
    symbol: str
    expiry_date: date
    days_to_expiry: int
    raw_price: float
    price_per_10g: float
    price_per_pure_gram_999: Optional[float] = None
    implied_annualized_carry_pct: float
    carry_rate_source: Optional[str] = "FIXED_ASSUMPTION_7.0PCT"


class CarryCurveResponse(BaseModel):
    as_of_date: date
    points: List[CarryCurvePoint]
    risk_free_rate_pct: float
    storage_rate_pct: float


class TermStructurePoint(BaseModel):
    symbol: str
    expiry_date: date
    days_to_expiry: int
    raw_settle_price: float
    price_per_10g: float
    price_per_pure_10g_999: float
    volume_lots: int
    open_interest: int


class TermStructureResponse(BaseModel):
    as_of_date: date
    contracts: List[TermStructurePoint]


class VolumeOIPoint(BaseModel):
    trade_date: date
    symbol: str
    settle_price: float
    volume_lots: int
    volume_value_lakhs: Optional[float] = None
    open_interest: int
    change_in_oi: Optional[int] = None


class VolumeOIResponse(BaseModel):
    symbol: str
    series: List[VolumeOIPoint]
    avg_volume_30d: float
    max_oi: int


class SpreadDetailResponse(BaseModel):
    pair_name: str
    base_symbol: str
    quote_symbol: str
    history: List[SpreadMetricResponse]
    current_z_score: Optional[float] = None
    half_life_days: Optional[float] = None
    historical_purity_note: str


class AnalyticsOverviewResponse(BaseModel):
    as_of_date: Optional[date] = None
    benchmark_goldm_price_10g: Optional[float] = None
    benchmark_pure_price_10g_999: Optional[float] = None
    contracts_count: int
    total_data_points: int
    active_pairs: List[str]
    current_spreads: List[Dict[str, Any]]
    top_divergence_pair: Optional[Dict[str, Any]] = None
    active_signals_count: int

