import io
import csv
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
from app.database import get_db
from app.models.spread_metrics import SpreadMetric
from app.models.normalized_price import NormalizedPrice
from app.models.bhavcopy import BhavcopyRecord
from app.models.backtest import BacktestRun
from app.schemas.backtest import (
    BacktestRequest,
    BacktestSummaryResponse,
    BacktestDetailResponse,
    SensitivityResponse
)
from app.services.backtest import run_pair_trading_backtest, run_sensitivity_analysis

router = APIRouter(prefix="/backtest", tags=["Backtesting"])


def build_pair_dataframe(db: Session, pair_name: str, use_carry_adj: bool = True):
    """Builds a complete historical DataFrame containing both legs, expiries, volume, and OI."""
    metrics = (
        db.query(SpreadMetric)
        .filter(SpreadMetric.pair_name == pair_name)
        .order_by(SpreadMetric.trade_date.asc())
        .all()
    )
    if not metrics:
        return None, None, None

    parts = pair_name.split("_vs_")
    base_sym = parts[0]
    quote_sym = parts[1] if len(parts) > 1 else "GOLDPETAL"

    norm_base = {
        n.trade_date: n
        for n in db.query(NormalizedPrice).filter(NormalizedPrice.symbol == base_sym).all()
    }
    norm_quote = {
        n.trade_date: n
        for n in db.query(NormalizedPrice).filter(NormalizedPrice.symbol == quote_sym).all()
    }
    bhav_base = {
        (b.trade_date, b.symbol): b
        for b in db.query(BhavcopyRecord).filter(BhavcopyRecord.symbol == base_sym).all()
    }
    bhav_quote = {
        (b.trade_date, b.symbol): b
        for b in db.query(BhavcopyRecord).filter(BhavcopyRecord.symbol == quote_sym).all()
    }

    data = []
    for m in metrics:
        d = m.trade_date
        if d in norm_base and d in norm_quote:
            nb = norm_base[d]
            nq = norm_quote[d]
            bb = bhav_base.get((d, base_sym))
            bq = bhav_quote.get((d, quote_sym))

            spread_val = (
                m.carry_adjusted_spread_pure_10g
                if (use_carry_adj and m.carry_adjusted_spread_pure_10g is not None)
                else (m.carry_adjusted_spread_per_10g if use_carry_adj else m.raw_spread_per_10g)
            )

            data.append({
                "trade_date": d,
                "spread_per_10g": spread_val,
                "z_score": m.z_score if m.z_score is not None else 0.0,
                "base_price_10g": nb.price_per_pure_10g_999 or nb.price_per_10g,
                "quote_price_10g": nq.price_per_pure_10g_999 or nq.price_per_10g,
                "base_raw_settle": nb.raw_settle_price,
                "quote_raw_settle": nq.raw_settle_price,
                "dte_base": nb.days_to_expiry,
                "dte_quote": nq.days_to_expiry,
                "vol_base": bb.volume_lots if bb else 1000,
                "vol_quote": bq.volume_lots if bq else 1000,
                "oi_base": bb.open_interest if bb else 2000,
                "oi_quote": bq.open_interest if bq else 2000,
            })

    return pd.DataFrame(data), base_sym, quote_sym


@router.post("/run", response_model=BacktestDetailResponse)
def run_backtest_endpoint(req: BacktestRequest, db: Session = Depends(get_db)):
    """Executes a full walk-forward backtest simulation on historical settlement records."""
    df, base_sym, quote_sym = build_pair_dataframe(db, req.pair_name, req.use_carry_adj)
    if df is None or len(df) == 0:
        raise HTTPException(
            status_code=400,
            detail=f"No spread data found for pair '{req.pair_name}'. Seed or upload bhavcopy data first."
        )

    result = run_pair_trading_backtest(
        df_pair=df,
        entry_z=req.entry_z,
        exit_z=req.exit_z,
        stop_loss_z=req.stop_loss_z,
        include_costs=req.include_costs,
        brokerage_per_lot_inr=req.brokerage_per_lot_inr,
        slippage_ticks_base=req.slippage_ticks_base,
        slippage_ticks_quote=req.slippage_ticks_quote,
        expiry_lockout_days=req.expiry_lockout_days,
        min_volume_lots=req.min_volume_lots,
        min_open_interest=req.min_open_interest,
        train_ratio=req.train_ratio,
        val_ratio=req.val_ratio,
        walk_forward=req.walk_forward,
        train_window_days=req.train_window_days,
        test_window_days=req.test_window_days,
        capital=req.capital,
        base_symbol=base_sym,
        quote_symbol=quote_sym
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Persist backtest run
    run = BacktestRun(
        pair_name=req.pair_name,
        strategy_name="Z_SCORE_MEAN_REVERSION",
        start_date=result["start_date"],
        end_date=result["end_date"],
        entry_z=req.entry_z,
        exit_z=req.exit_z,
        stop_loss_z=req.stop_loss_z,
        window_days=req.window_days,
        use_carry_adj=req.use_carry_adj,
        include_costs=req.include_costs,
        slippage_ticks=req.slippage_ticks_base,
        walk_forward=req.walk_forward,
        capital=req.capital,
        gross_total_return_pct=result["gross_total_return_pct"],
        total_return_pct=result["total_return_pct"],
        gross_pnl_inr=result["gross_pnl_inr"],
        net_pnl_inr=result["net_pnl_inr"],
        annualized_return_pct=result["annualized_return_pct"],
        sharpe_ratio=result["sharpe_ratio"],
        sortino_ratio=result["sortino_ratio"],
        calmar_ratio=result["calmar_ratio"],
        max_drawdown_pct=result["max_drawdown_pct"],
        win_rate_pct=result["win_rate_pct"],
        profit_factor=result["profit_factor"],
        total_trades=result["total_trades"],
        winning_trades=result["winning_trades"],
        losing_trades=result["losing_trades"],
        total_fees_paid=result["total_fees_paid"],
        turnover_inr=result["turnover_inr"],
        avg_holding_days=result["avg_holding_days"],
        benchmark_return_pct=result["benchmark_return_pct"],
        gold_beta=result["gold_beta"],
        equity_curve=result["equity_curve"],
        trades_json=result["trades"],
        walk_forward_metrics=result.get("walk_forward_metrics"),
        split_metrics=result.get("split_metrics"),
        config_snapshot=result.get("config_snapshot")
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return BacktestDetailResponse(
        id=run.id,
        pair_name=run.pair_name,
        strategy_name=run.strategy_name,
        start_date=run.start_date,
        end_date=run.end_date,
        entry_z=run.entry_z,
        exit_z=run.exit_z,
        stop_loss_z=run.stop_loss_z,
        gross_total_return_pct=run.gross_total_return_pct,
        total_return_pct=run.total_return_pct,
        gross_pnl_inr=run.gross_pnl_inr,
        net_pnl_inr=run.net_pnl_inr,
        annualized_return_pct=run.annualized_return_pct,
        sharpe_ratio=run.sharpe_ratio,
        sortino_ratio=run.sortino_ratio,
        calmar_ratio=run.calmar_ratio,
        max_drawdown_pct=run.max_drawdown_pct,
        win_rate_pct=run.win_rate_pct,
        profit_factor=run.profit_factor,
        total_trades=run.total_trades,
        winning_trades=run.winning_trades,
        losing_trades=run.losing_trades,
        total_fees_paid=run.total_fees_paid,
        turnover_inr=run.turnover_inr,
        avg_holding_days=run.avg_holding_days,
        benchmark_return_pct=run.benchmark_return_pct,
        gold_beta=run.gold_beta,
        walk_forward=run.walk_forward,
        walk_forward_metrics=run.walk_forward_metrics,
        split_metrics=run.split_metrics,
        config_snapshot=run.config_snapshot,
        created_at=run.created_at,
        equity_curve=run.equity_curve,
        trades=run.trades_json
    )


@router.post("/sensitivity", response_model=SensitivityResponse)
def run_sensitivity_endpoint(
    pair_name: str = Query("GOLDM_vs_GOLDPETAL"),
    capital: float = Query(1000000.0),
    db: Session = Depends(get_db)
):
    """Executes multi-scenario parameter grid sensitivity analysis."""
    df, base_sym, quote_sym = build_pair_dataframe(db, pair_name, use_carry_adj=True)
    if df is None or len(df) == 0:
        raise HTTPException(status_code=400, detail="Insufficient data for sensitivity analysis.")

    return run_sensitivity_analysis(df, base_symbol=base_sym, quote_symbol=quote_sym, capital=capital)


@router.get("/history", response_model=List[BacktestSummaryResponse])
def get_backtest_history(db: Session = Depends(get_db)):
    """Fetches previously executed backtests."""
    return db.query(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(20).all()


@router.get("/{run_id}", response_model=BacktestDetailResponse)
def get_backtest_detail(run_id: int, db: Session = Depends(get_db)):
    """Fetches single backtest run with complete equity curve and trades."""
    run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found.")

    return BacktestDetailResponse(
        id=run.id,
        pair_name=run.pair_name,
        strategy_name=run.strategy_name,
        start_date=run.start_date,
        end_date=run.end_date,
        entry_z=run.entry_z,
        exit_z=run.exit_z,
        stop_loss_z=run.stop_loss_z,
        gross_total_return_pct=run.gross_total_return_pct,
        total_return_pct=run.total_return_pct,
        gross_pnl_inr=run.gross_pnl_inr,
        net_pnl_inr=run.net_pnl_inr,
        annualized_return_pct=run.annualized_return_pct,
        sharpe_ratio=run.sharpe_ratio,
        sortino_ratio=run.sortino_ratio,
        calmar_ratio=run.calmar_ratio,
        max_drawdown_pct=run.max_drawdown_pct,
        win_rate_pct=run.win_rate_pct,
        profit_factor=run.profit_factor,
        total_trades=run.total_trades,
        winning_trades=run.winning_trades,
        losing_trades=run.losing_trades,
        total_fees_paid=run.total_fees_paid,
        turnover_inr=run.turnover_inr,
        avg_holding_days=run.avg_holding_days,
        benchmark_return_pct=run.benchmark_return_pct,
        gold_beta=run.gold_beta,
        walk_forward=run.walk_forward,
        walk_forward_metrics=run.walk_forward_metrics,
        split_metrics=run.split_metrics,
        config_snapshot=run.config_snapshot,
        created_at=run.created_at,
        equity_curve=run.equity_curve,
        trades=run.trades_json
    )


@router.get("/{run_id}/export/trades.csv")
def export_trades_csv(run_id: int, db: Session = Depends(get_db)):
    """Exports executed trade ledger for a backtest run in CSV format."""
    run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
    if not run or run.trades_json is None:
        raise HTTPException(status_code=404, detail="Backtest run not found.")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "trade_id", "position_type", "entry_date", "exit_date", "holding_days",
        "lots_base", "lots_quote", "entry_base_settle", "entry_base_fill",
        "exit_base_settle", "exit_base_fill", "entry_quote_settle", "entry_quote_fill",
        "exit_quote_settle", "exit_quote_fill", "entry_z", "exit_z",
        "gross_pnl_inr", "entry_costs_inr", "exit_costs_inr", "slippage_inr",
        "total_fees_inr", "net_pnl_inr", "return_pct", "exit_reason", "split_phase"
    ])
    writer.writeheader()
    for t in (run.trades_json or []):
        writer.writerow({k: t.get(k, "") for k in writer.fieldnames})

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=trades_run_{run_id}_{run.pair_name}.csv"}
    )


@router.get("/{run_id}/export/equity.csv")
def export_equity_csv(run_id: int, db: Session = Depends(get_db)):
    """Exports daily portfolio equity progression and drawdown in CSV format."""
    run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
    if not run or run.equity_curve is None:
        raise HTTPException(status_code=404, detail="Backtest run not found.")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "date", "equity", "gross_equity", "benchmark_equity", "cash", "spread", "z_score", "position", "split_phase"
    ])
    writer.writeheader()
    for pt in run.equity_curve:
        writer.writerow({k: pt.get(k, "") for k in writer.fieldnames})

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=equity_curve_run_{run_id}_{run.pair_name}.csv"}
    )
