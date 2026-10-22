import pytest
import math
import numpy as np
import pandas as pd
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.services.normalization import normalize_price, CONTRACT_SPECS, REFERENCE_PURITY
from app.services.carry_adjustment import calculate_carry_adjustment
from app.services.spread_analytics import (
    calculate_pair_spread,
    calculate_rolling_z_score,
    calculate_half_life,
    compute_correlation_matrix
)
from app.services.signals import evaluate_signal_for_pair, MIN_DAYS_TO_EXPIRY, MIN_AVG_VOLUME_LOTS
from app.services.transaction_costs import calculate_pair_roundtrip_cost_bps

client = TestClient(app)


def test_purity_normalization_formula_and_contract_specs():
    """
    Validates:
    1. normalized_price = settlement_price / quotation_base_grams * 999 / purity
    2. quotation_base_grams, trading_unit_grams, and purity are stored separately.
    3. GOLDM purity is 995, others are 999.
    4. Quotation base is NOT inferred solely from trading unit (GOLDM: trading=100g, quote=10g).
    """
    assert CONTRACT_SPECS["GOLDM"]["purity"] == 995.0
    assert CONTRACT_SPECS["GOLDM"]["trading_unit_grams"] == 100.0
    assert CONTRACT_SPECS["GOLDM"]["quotation_base_grams"] == 10.0
    assert CONTRACT_SPECS["GOLDM"]["trading_unit_grams"] != CONTRACT_SPECS["GOLDM"]["quotation_base_grams"]

    assert CONTRACT_SPECS["GOLDTEN"]["purity"] == 999.0
    assert CONTRACT_SPECS["GOLDTEN"]["quotation_base_grams"] == 10.0

    assert CONTRACT_SPECS["GOLDGUINEA"]["purity"] == 999.0
    assert CONTRACT_SPECS["GOLDGUINEA"]["quotation_base_grams"] == 8.0

    assert CONTRACT_SPECS["GOLDPETAL"]["purity"] == 999.0
    assert CONTRACT_SPECS["GOLDPETAL"]["quotation_base_grams"] == 1.0

    # Test GOLDM normalization with 995 fineness:
    # settlement = ₹79,600 / 10g
    # price_per_gram = 7960.0
    # price_per_pure_gram_999 = 7960.0 * (999.0 / 995.0) = 7992.0
    norm_goldm = normalize_price("GOLDM", 79600.0)
    assert norm_goldm["price_per_gram"] == 7960.0
    assert norm_goldm["price_per_10g"] == 79600.0
    assert norm_goldm["purity"] == 995.0
    assert norm_goldm["quotation_base_grams"] == 10.0
    expected_pure_1g = round(7960.0 * (999.0 / 995.0), 4)
    assert norm_goldm["price_per_pure_gram_999"] == expected_pure_1g
    assert norm_goldm["purity_adjustment_factor"] == round(999.0 / 995.0, 6)

    # Test GOLDGUINEA normalization:
    # 8g quotation unit, 999 purity
    # settlement = ₹64,000 / 8g => ₹8,000/g
    norm_guinea = normalize_price("GOLDGUINEA", 64000.0)
    assert norm_guinea["price_per_gram"] == 8000.0
    assert norm_guinea["price_per_pure_gram_999"] == 8000.0
    assert norm_guinea["purity_adjustment_factor"] == 1.0


def test_exponential_cost_of_carry_and_labeling():
    """
    Validates exponential cost-of-carry discount factor:
      D = exp(-C * (T - T_b) / 365)
    and validates explicit label when using fixed-rate assumption vs historical rate.
    """
    # 1. Zero DTE: factor = 1.0
    res_zero = calculate_carry_adjustment(price_per_10g=80000.0, days_to_expiry=0)
    assert res_zero["discount_factor"] == 1.0
    assert res_zero["carry_adjusted_price_per_10g"] == 80000.0
    assert res_zero["carry_drag_rupees"] == 0.0

    # 2. 73 days to expiry with fixed rate assumption (7.0%)
    res_fixed = calculate_carry_adjustment(
        price_per_10g=80000.0,
        days_to_expiry=73,
        benchmark_dte=0,
        annual_carry_rate=None  # will use default
    )
    # 73 / 365 = 0.2 years. rate = 0.07. exp(-0.07 * 0.2) = exp(-0.014) = 0.986098
    expected_df = math.exp(-0.07 * (73 / 365.0))
    assert abs(res_fixed["discount_factor"] - round(expected_df, 6)) < 1e-4
    assert res_fixed["carry_adjusted_price_per_10g"] < 80000.0
    assert "FIXED_ASSUMPTION" in res_fixed["carry_rate_source"]
    assert res_fixed["method"] == "exponential"

    # 3. Explicit historical rate input
    res_hist = calculate_carry_adjustment(
        price_per_10g=80000.0,
        days_to_expiry=73,
        benchmark_dte=0,
        annual_carry_rate=0.065,
        rate_source="HISTORICAL_RBI_REPO"
    )
    assert res_hist["carry_rate_source"] == "HISTORICAL_RBI_REPO"
    assert res_hist["annualized_carry_rate"] == 0.065


def test_z_score_calculation_no_look_ahead_bias():
    """
    Validates rolling Z-score calculation:
    1. Uses rolling window without look-ahead bias (only past observations).
    2. Handles min_periods gracefully without leaking future data.
    """
    dates = pd.date_range("2026-01-01", periods=30, freq="B")
    # Synthetic spread series
    spreads = pd.Series([10.0 + i * 0.5 for i in range(30)], index=dates)

    rolling_mean, rolling_std, z_score = calculate_rolling_z_score(spreads, window=10)

    # For any index t, rolling mean at t must equal mean of spreads[t-9 : t+1]
    for idx in range(10, 30):
        past_slice = spreads.iloc[max(0, idx - 10 + 1) : idx + 1]
        assert round(rolling_mean.iloc[idx], 4) == round(past_slice.mean(), 4)
        assert round(rolling_std.iloc[idx], 4) == round(past_slice.std(), 4)


def test_handling_missing_values_and_shorter_history():
    """
    Validates handling of contracts with shorter historical availability (like GOLDTEN)
    or missing observations: does not crash, aligns on common dates.
    """
    dates_long = pd.date_range("2026-01-01", periods=20, freq="B")
    dates_short = dates_long[10:]  # GOLDTEN listed 10 days later

    s_base = pd.Series(np.random.normal(80000, 200, len(dates_long)), index=dates_long)
    s_quote = pd.Series(np.random.normal(80000, 200, len(dates_short)), index=dates_short)

    common = s_base.index.intersection(s_quote.index)
    assert len(common) == 10

    spread = calculate_pair_spread(s_base.loc[common], s_quote.loc[common])
    assert len(spread) == 10
    assert not spread.isna().any()

    # Z-score on short history
    rm, rstd, z = calculate_rolling_z_score(spread, window=10)
    assert len(z) == 10


def test_signal_qualification_cost_and_liquidity_guardrails():
    """
    Validates that a trading signal is NOT generated merely because Z-score looks large.
    Must pass:
      1. Net edge > transaction cost hurdle
      2. Expiry eligibility: DTE >= 5 days (avoids MCX delivery/tender risks)
      3. Liquidity limitation: avg volume >= 50 lots
    """
    sig_date = date(2026, 10, 20)

    # Scenario A: Large Z-score (+2.8), but Gross Edge is small (3 bps) vs 6.2 bps friction -> DISQUALIFIED
    # Spread = 8010, mean = 8000 => mispricing = ₹10 / 80000 = 1.25 bps
    sig_cost_blocked = evaluate_signal_for_pair(
        pair_name="GOLDM_vs_GOLDPETAL",
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL",
        signal_date=sig_date,
        current_spread=8010.0,
        rolling_mean=8000.0,
        rolling_std=3.5,  # Z = (8010 - 8000)/3.5 = 2.85 (large Z!)
        z_score=2.85,
        base_price_10g=80000.0,
        quote_price_10g=80000.0,
        days_to_expiry=25,
        avg_volume=500
    )
    assert sig_cost_blocked is not None
    assert sig_cost_blocked["is_qualified"] is False
    assert sig_cost_blocked["status"] == "DISQUALIFIED"
    assert "INSUFFICIENT_EDGE" in sig_cost_blocked["rejection_reason"]

    # Scenario B: Large Z-score, sufficient gross edge, but DTE = 3 days (< 5 days tender buffer) -> DISQUALIFIED
    sig_dte_blocked = evaluate_signal_for_pair(
        pair_name="GOLDM_vs_GOLDPETAL",
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL",
        signal_date=sig_date,
        current_spread=8300.0,
        rolling_mean=8000.0,
        rolling_std=100.0,  # Z = 3.0, mispricing = ₹300 / 80000 = 37.5 bps >> friction
        z_score=3.0,
        base_price_10g=80000.0,
        quote_price_10g=80000.0,
        days_to_expiry=3,  # < 5 days!
        avg_volume=500
    )
    assert sig_dte_blocked is not None
    assert sig_dte_blocked["expiry_eligible"] is False
    assert sig_dte_blocked["is_qualified"] is False
    assert "NEAR_EXPIRY_RISK" in sig_dte_blocked["rejection_reason"]

    # Scenario C: Large Z-score, sufficient gross edge, DTE = 20, but volume = 15 lots (< 50 lots) -> DISQUALIFIED
    sig_vol_blocked = evaluate_signal_for_pair(
        pair_name="GOLDM_vs_GOLDPETAL",
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL",
        signal_date=sig_date,
        current_spread=8300.0,
        rolling_mean=8000.0,
        rolling_std=100.0,
        z_score=3.0,
        base_price_10g=80000.0,
        quote_price_10g=80000.0,
        days_to_expiry=20,
        avg_volume=15  # < 50 lots!
    )
    assert sig_vol_blocked is not None
    assert sig_vol_blocked["liquidity_qualified"] is False
    assert sig_vol_blocked["is_qualified"] is False
    assert "LOW_LIQUIDITY" in sig_vol_blocked["rejection_reason"]

    # Scenario D: Large Z-score, high edge, DTE = 20, volume = 500 -> QUALIFIED & ACTIVE
    sig_qualified = evaluate_signal_for_pair(
        pair_name="GOLDM_vs_GOLDPETAL",
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL",
        signal_date=sig_date,
        current_spread=8300.0,
        rolling_mean=8000.0,
        rolling_std=100.0,
        z_score=3.0,
        base_price_10g=80000.0,
        quote_price_10g=80000.0,
        days_to_expiry=20,
        avg_volume=500
    )
    assert sig_qualified is not None
    assert sig_qualified["is_qualified"] is True
    assert sig_qualified["expiry_eligible"] is True
    assert sig_qualified["liquidity_qualified"] is True
    assert sig_qualified["status"] == "ACTIVE"
    assert sig_qualified["rejection_reason"] is None


def test_analytics_api_endpoints():
    """
    Tests that FastAPI analytics endpoints respond with valid schemas.
    """
    # 1. Term structure
    resp_ts = client.get("/api/analytics/term-structure")
    assert resp_ts.status_code == 200
    data_ts = resp_ts.json()
    assert "as_of_date" in data_ts
    assert "contracts" in data_ts

    # 2. Volume & OI
    resp_vol = client.get("/api/analytics/volume-oi?symbol=GOLDM")
    assert resp_vol.status_code == 200
    data_vol = resp_vol.json()
    assert data_vol["symbol"] == "GOLDM"
    assert "series" in data_vol
    assert "avg_volume_30d" in data_vol

    # 3. Carry Curve
    resp_carry = client.get("/api/analytics/carry-curve")
    assert resp_carry.status_code == 200
    data_carry = resp_carry.json()
    assert "points" in data_carry

    # 4. Overview
    resp_ov = client.get("/api/analytics/overview")
    assert resp_ov.status_code == 200
    data_ov = resp_ov.json()
    assert "benchmark_goldm_price_10g" in data_ov
    assert "active_pairs" in data_ov
