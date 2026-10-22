from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional
from datetime import date, datetime


class BacktestRequest(BaseModel):
    pair_name: str = "GOLDM_vs_GOLDPETAL"
    entry_z: float = Field(2.0, ge=0.5, le=5.0)
    exit_z: float = Field(0.5, ge=0.0, le=2.0)
    stop_loss_z: float = Field(3.5, ge=1.5, le=6.0)
    window_days: int = Field(20, ge=5, le=90)
    use_carry_adj: bool = True
    include_costs: bool = True
    brokerage_per_lot_inr: float = Field(20.0, ge=0.0, le=500.0)
    slippage_ticks_base: float = Field(1.0, ge=0.0, le=10.0)
    slippage_ticks_quote: float = Field(1.0, ge=0.0, le=10.0)
    expiry_lockout_days: int = Field(5, ge=1, le=20)
    min_volume_lots: int = Field(50, ge=0, le=10000)
    min_open_interest: int = Field(100, ge=0, le=50000)
    train_ratio: float = Field(0.50, ge=0.2, le=0.8)
    val_ratio: float = Field(0.25, ge=0.1, le=0.4)
    walk_forward: bool = False
    train_window_days: int = Field(40, ge=20, le=120)
    test_window_days: int = Field(15, ge=5, le=60)
    capital: float = Field(1000000.0, ge=100000.0)


class BacktestSummaryResponse(BaseModel):
    id: int
    pair_name: str
    strategy_name: str
    start_date: date
    end_date: date
    entry_z: float
    exit_z: float
    stop_loss_z: float
    gross_total_return_pct: Optional[float] = None
    total_return_pct: float  # Net return
    gross_pnl_inr: Optional[float] = None
    net_pnl_inr: Optional[float] = None
    annualized_return_pct: float
    sharpe_ratio: float
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    max_drawdown_pct: float
    win_rate_pct: float
    profit_factor: Optional[float] = None
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_fees_paid: float
    turnover_inr: Optional[float] = None
    avg_holding_days: Optional[float] = None
    benchmark_return_pct: Optional[float] = None
    gold_beta: Optional[float] = None
    walk_forward: Optional[bool] = False
    split_metrics: Optional[Dict[str, Any]] = None
    config_snapshot: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BacktestDetailResponse(BacktestSummaryResponse):
    equity_curve: Optional[List[Dict[str, Any]]] = None
    trades: Optional[List[Dict[str, Any]]] = None
    walk_forward_metrics: Optional[List[Dict[str, Any]]] = None


class SensitivityScenario(BaseModel):
    parameter_name: str
    parameter_value: Any
    net_return_pct: float
    gross_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    total_trades: int
    total_fees_inr: float


class SensitivityResponse(BaseModel):
    pair_name: str
    base_case_net_return_pct: float
    base_case_sharpe: float
    slippage_sensitivity: List[SensitivityScenario]
    cost_sensitivity: List[SensitivityScenario]
    threshold_sensitivity: List[SensitivityScenario]
    carry_rate_sensitivity: List[SensitivityScenario]
