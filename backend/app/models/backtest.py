from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, Text, JSON
from datetime import datetime
from app.database import Base


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, index=True)
    pair_name = Column(String(64), nullable=False)
    strategy_name = Column(String(64), default="Z_SCORE_MEAN_REVERSION")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Parameters
    entry_z = Column(Float, default=2.0)
    exit_z = Column(Float, default=0.5)
    stop_loss_z = Column(Float, default=3.5)
    window_days = Column(Integer, default=20)
    use_carry_adj = Column(Boolean, default=True)
    include_costs = Column(Boolean, default=True)
    slippage_ticks = Column(Float, default=1.0)
    walk_forward = Column(Boolean, default=False)
    capital = Column(Float, default=1000000.0)  # INR 10 Lakhs standard
    
    # Performance Metrics - Gross & Net PnL Reported Separately
    gross_total_return_pct = Column(Float, nullable=True)
    total_return_pct = Column(Float, nullable=False)  # Net return
    gross_pnl_inr = Column(Float, nullable=True)
    net_pnl_inr = Column(Float, nullable=True)
    annualized_return_pct = Column(Float, nullable=False)
    sharpe_ratio = Column(Float, nullable=False)
    sortino_ratio = Column(Float, nullable=True)
    calmar_ratio = Column(Float, nullable=True)
    max_drawdown_pct = Column(Float, nullable=False)
    win_rate_pct = Column(Float, nullable=False)
    profit_factor = Column(Float, nullable=True)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_fees_paid = Column(Float, default=0.0)
    turnover_inr = Column(Float, default=0.0)
    avg_holding_days = Column(Float, default=0.0)

    # Benchmark & Market Neutrality
    benchmark_return_pct = Column(Float, nullable=True)
    gold_beta = Column(Float, nullable=True)
    
    # Detailed series JSON for charts, trade log, train/val/test splits & config snapshot
    equity_curve = Column(JSON, nullable=True)
    trades_json = Column(JSON, nullable=True)
    walk_forward_metrics = Column(JSON, nullable=True)
    split_metrics = Column(JSON, nullable=True)  # Train, Validation, Test performance breakdown
    config_snapshot = Column(JSON, nullable=True) # Full reproducible backtest configuration
    
    created_at = Column(DateTime, default=datetime.utcnow)
