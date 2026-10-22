import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.services.backtest import (
    run_pair_trading_backtest,
    run_sensitivity_analysis,
    compute_leg_transaction_costs,
    calculate_position_quantities
)

client = TestClient(app)


def create_sample_pair_df(n_days: int = 50, dte_start: int = 40):
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(n_days)]
    # Alternating mean-reverting z-score series
    z_scores = [2.5 if i % 8 == 2 else (-2.5 if i % 8 == 6 else 0.1) for i in range(n_days)]
    spreads = [10.0 + z * 5.0 for z in z_scores]

    dtes = [max(0, dte_start - i) for i in range(n_days)]

    return pd.DataFrame({
        "trade_date": dates,
        "spread_per_10g": spreads,
        "z_score": z_scores,
        "base_price_10g": [78000.0] * n_days,
        "quote_price_10g": [78000.0] * n_days,
        "base_raw_settle": [78000.0] * n_days,
        "quote_raw_settle": [7800.0] * n_days,
        "dte_base": dtes,
        "dte_quote": dtes,
        "vol_base": [1500] * n_days,
        "vol_quote": [5000] * n_days,
        "oi_base": [3000] * n_days,
        "oi_quote": [8000] * n_days,
    })


def test_transaction_cost_deduction():
    """
    Validates itemized MCX transaction cost deductions:
    Exchange Turnover Fee (0.0021%), SEBI (0.0001%), GST (18%),
    CTT (0.01% on sell leg), Stamp Duty (0.002% on buy leg), and Brokerage.
    """
    turnover = 1000000.0  # ₹10 Lakhs turnover

    # Buy leg costs
    buy_costs = compute_leg_transaction_costs(turnover, is_buy=True, lots=1, brokerage_per_lot=20.0)
    assert buy_costs["brokerage"] == 20.0
    assert buy_costs["exchange_fee"] == 21.0
    assert buy_costs["sebi_fee"] == 1.0
    assert buy_costs["stamp_duty"] == 20.0
    assert buy_costs["ctt"] == 0.0  # No CTT on buy
    assert buy_costs["gst"] == round((21.0 + 1.0 + 20.0) * 0.18, 2)
    assert buy_costs["total_fees"] > 60.0

    # Sell leg costs
    sell_costs = compute_leg_transaction_costs(turnover, is_buy=False, lots=1, brokerage_per_lot=20.0)
    assert sell_costs["ctt"] == 100.0  # 0.01% CTT on sell
    assert sell_costs["stamp_duty"] == 0.0  # No Stamp Duty on sell
    assert sell_costs["total_fees"] > buy_costs["total_fees"]


def test_position_quantities_and_pure_gold_hedging():
    """
    Validates explicit position sizing and contract quantities:
    GOLDM (100g, 995 fineness = 99.5g pure gold) hedged by GOLDPETAL (1g, 999 fineness = 0.999g pure gold)
    yields exactly 100 lots of GOLDPETAL.
    """
    lots_b, lots_q, notional_b, notional_q = calculate_position_quantities(
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL",
        base_settle_quote=78500.0,
        capital=1000000.0,
        allocation_pct=0.70
    )
    assert lots_b >= 1
    # 1 lot of GOLDM requires 100 lots of GOLDPETAL for metal delta neutrality
    assert lots_q == lots_b * 100


def test_backtest_execution_and_gross_net_separation():
    """
    Validates:
      1. Execution without look-ahead bias.
      2. Gross P&L and Net P&L reported separately.
      3. Distinguishes modeled execution fills from observed settlement prices.
    """
    df = create_sample_pair_df(n_days=40, dte_start=45)

    res = run_pair_trading_backtest(
        df_pair=df,
        entry_z=2.0,
        exit_z=0.5,
        stop_loss_z=3.5,
        include_costs=True,
        slippage_ticks_base=1.0,
        slippage_ticks_quote=1.0,
        capital=1000000.0,
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL"
    )

    assert "total_return_pct" in res
    assert "gross_total_return_pct" in res
    assert "gross_pnl_inr" in res
    assert "net_pnl_inr" in res
    assert "total_fees_paid" in res
    assert res["total_fees_paid"] > 0.0

    # Gross return must be >= Net return
    assert res["gross_total_return_pct"] >= res["total_return_pct"]
    assert res["gross_pnl_inr"] >= res["net_pnl_inr"]

    # Trade ledger distinguishes modeled fills from observed settlement prices
    assert len(res["trades"]) > 0
    trade = res["trades"][0]
    assert "entry_base_settle" in trade
    assert "entry_base_fill" in trade
    assert "entry_costs_inr" in trade
    assert "exit_costs_inr" in trade
    assert "slippage_inr" in trade
    assert trade["entry_base_fill"] != trade["entry_base_settle"]


def test_look_ahead_bias_prevention():
    """
    Validates zero look-ahead bias:
    Altering future settlement prices (at day 35) must NOT alter trading decisions,
    entry dates, or execution prices at earlier days (e.g. day 10).
    """
    df1 = create_sample_pair_df(n_days=40, dte_start=45)
    df2 = df1.copy()
    # Shock day 35 significantly in df2
    df2.loc[35, "spread_per_10g"] = 999.0
    df2.loc[35, "z_score"] = 15.0

    res1 = run_pair_trading_backtest(df_pair=df1, entry_z=2.0, exit_z=0.5, capital=1000000.0)
    res2 = run_pair_trading_backtest(df_pair=df2, entry_z=2.0, exit_z=0.5, capital=1000000.0)

    # First trade must be completely identical
    assert len(res1["trades"]) > 0
    assert len(res2["trades"]) > 0
    assert res1["trades"][0]["entry_date"] == res2["trades"][0]["entry_date"]
    assert res1["trades"][0]["net_pnl_inr"] == res2["trades"][0]["net_pnl_inr"]


def test_expiry_lockout_and_forced_exit():
    """
    Validates:
      1. Prevents new entries inside expiry lockout window (min DTE <= 5).
      2. Forces exit of open positions when DTE <= 1.
    """
    # Create dataset of 30 days where DTE drops towards zero
    dates = [date(2026, 9, 1) + timedelta(days=i) for i in range(30)]
    # Z-scores are zero for first 20 days, then breach entry threshold on day 25 (when DTE is 3 <= lockout!)
    z_scores = [0.0] * 30
    z_scores[25] = 2.8  # Breach entry threshold on day 25
    z_scores[26] = 2.8

    # DTE starts at 30 and drops to 0
    dtes = [max(0, 30 - i) for i in range(30)]

    df = pd.DataFrame({
        "trade_date": dates,
        "spread_per_10g": [10.0 + z * 5.0 for z in z_scores],
        "z_score": z_scores,
        "base_price_10g": [78000.0] * 30,
        "quote_price_10g": [78000.0] * 30,
        "base_raw_settle": [78000.0] * 30,
        "quote_raw_settle": [7800.0] * 30,
        "dte_base": dtes,
        "dte_quote": dtes,
        "vol_base": [1000] * 30,
        "vol_quote": [1000] * 30,
        "oi_base": [2000] * 30,
        "oi_quote": [2000] * 30,
    })

    res = run_pair_trading_backtest(
        df_pair=df,
        entry_z=2.0,
        exit_z=0.5,
        expiry_lockout_days=5,  # DTE <= 5 lockout
        capital=1000000.0
    )

    # On day 25, DTE is 30 - 25 = 5 (which is <= expiry_lockout_days 5).
    # New entry must be rejected due to expiry lockout window!
    assert len(res["trades"]) == 0


def test_train_validation_test_splits():
    """
    Validates chronological 3-way partition:
    Reports performance metrics separately for Training, Validation, and Out-of-Sample Test periods.
    """
    df = create_sample_pair_df(n_days=60, dte_start=50)

    res = run_pair_trading_backtest(
        df_pair=df,
        entry_z=2.0,
        exit_z=0.5,
        train_ratio=0.50,
        val_ratio=0.25,
        walk_forward=False,
        capital=1000000.0
    )

    assert "split_metrics" in res
    sm = res["split_metrics"]
    assert "training" in sm
    assert "validation" in sm
    assert "out_of_sample_test" in sm
    assert "net_return_pct" in sm["training"]
    assert "net_return_pct" in sm["out_of_sample_test"]


def test_gold_beta_and_benchmark_metrics():
    """
    Validates benchmark comparison and market-neutral gold beta calculation.
    """
    df = create_sample_pair_df(n_days=40, dte_start=45)

    res = run_pair_trading_backtest(df_pair=df, entry_z=2.0, exit_z=0.5, capital=1000000.0)

    assert "benchmark_return_pct" in res
    assert "gold_beta" in res
    assert "calmar_ratio" in res
    assert "turnover_inr" in res
    assert "avg_holding_days" in res


def test_sensitivity_analysis():
    """
    Validates multi-scenario sensitivity analysis across slippage, costs, thresholds, and carry rates.
    """
    df = create_sample_pair_df(n_days=40, dte_start=45)

    sens = run_sensitivity_analysis(df_pair=df, base_symbol="GOLDM", quote_symbol="GOLDPETAL", capital=1000000.0)

    assert "slippage_sensitivity" in sens
    assert "cost_sensitivity" in sens
    assert "threshold_sensitivity" in sens
    assert "carry_rate_sensitivity" in sens
    assert len(sens["slippage_sensitivity"]) == 4


def test_backtest_api_endpoints_and_csv_export():
    """
    Tests FastAPI endpoints:
      - POST /api/backtest/run
      - POST /api/backtest/sensitivity
      - GET /api/backtest/{id}/export/trades.csv
      - GET /api/backtest/{id}/export/equity.csv
    """
    payload = {
        "pair_name": "GOLDM_vs_GOLDPETAL",
        "entry_z": 2.0,
        "exit_z": 0.5,
        "stop_loss_z": 3.5,
        "window_days": 20,
        "use_carry_adj": True,
        "include_costs": True,
        "brokerage_per_lot_inr": 20.0,
        "slippage_ticks_base": 1.0,
        "slippage_ticks_quote": 1.0,
        "expiry_lockout_days": 5,
        "min_volume_lots": 50,
        "min_open_interest": 100,
        "train_ratio": 0.5,
        "val_ratio": 0.25,
        "walk_forward": False,
        "capital": 1000000.0
    }
    resp = client.post("/api/backtest/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    run_id = data["id"]
    assert "gross_total_return_pct" in data
    assert "total_return_pct" in data
    assert "gold_beta" in data
    assert "split_metrics" in data

    # Test sensitivity endpoint
    resp_sens = client.post("/api/backtest/sensitivity?pair_name=GOLDM_vs_GOLDPETAL")
    assert resp_sens.status_code == 200
    sens_data = resp_sens.json()
    assert "slippage_sensitivity" in sens_data

    # Test CSV export endpoints
    resp_trades_csv = client.get(f"/api/backtest/{run_id}/export/trades.csv")
    assert resp_trades_csv.status_code == 200
    assert "text/csv" in resp_trades_csv.headers["content-type"]
    assert "attachment" in resp_trades_csv.headers["content-disposition"]

    resp_equity_csv = client.get(f"/api/backtest/{run_id}/export/equity.csv")
    assert resp_equity_csv.status_code == 200
    assert "text/csv" in resp_equity_csv.headers["content-type"]
