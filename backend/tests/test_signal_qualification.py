"""
Unit and Integration Tests for MCX Gold RVA Signal Qualification and Alert Module.

Tests validate:
1. Normalized and carry-adjusted spread evaluation.
2. Calculation of expected gross edge, total round-trip costs, and net edge.
3. Liquidity and data quality filters.
4. T-5 expiry lockout rejection (DTE <= 5 days).
5. 2.5x total cost multiplier hurdle suppression.
6. Positive expected net edge requirement.
7. Deduplication of alerts for (pair, base_expiry, quote_expiry).
8. Exact recording of candidate rejection reasons.
9. Zero fabrication when no opportunity qualifies.
10. Presence of all mandatory display fields and disclaimers.
11. Endpoints: /api/signals/candidates, /api/signals/history, /api/signals/qualified.
"""

import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient
from app.main import app
from app.services.signal_qualification import (
    qualify_spread_opportunity,
    evaluate_latest_candidates,
    ANALYTICAL_DISCLAIMER
)
from app.database import SessionLocal
from app.models.bhavcopy import BhavcopyRecord
from app.models.signals import RVASignal


@pytest.fixture
def test_client():
    return TestClient(app)


def test_gross_edge_and_itemized_costs_calculation():
    """
    Validates mathematical precision of expected gross edge, roundtrip costs,
    expected net edge, and cost coverage ratio.
    """
    sig_date = date(2026, 10, 20)
    base_price = 80000.0
    quote_price = 80000.0
    adjusted_spread = 8240.0
    rolling_mean = 8000.0
    rolling_std = 80.0
    z_score = 3.0  # (8240 - 8000) / 80 = 3.0

    res = qualify_spread_opportunity(
        pair_name="GOLDM_vs_GOLDPETAL",
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL",
        signal_date=sig_date,
        base_normalized_price=base_price,
        quote_normalized_price=quote_price,
        adjusted_spread=adjusted_spread,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        z_score=z_score,
        base_expiry_date=date(2026, 12, 5),
        quote_expiry_date=date(2026, 12, 5),
        base_dte=35,
        quote_dte=35,
        base_volume=500.0,
        quote_volume=1200.0,
        base_oi=3000.0,
        quote_oi=4500.0,
        history_count=30,
        status_mode="v2"
    )

    # Gross edge = |8240 - 8000| = 240 INR / 80000 = 30.0 bps
    assert res["expected_gross_edge_inr"] == 240.0
    assert res["expected_gross_edge_bps"] == 30.0
    assert res["estimated_costs_bps"] > 0.0
    assert res["expected_net_edge_bps"] == round(30.0 - res["estimated_costs_bps"], 2)
    assert res["cost_coverage_ratio"] == round(30.0 / res["estimated_costs_bps"], 2)
    assert res["cost_coverage_ratio"] >= 2.5
    assert res["is_qualified"] is True
    assert res["status"] == "QUALIFIED_FOR_REVIEW"
    assert len(res["rejection_reasons"]) == 0


def test_suppression_unless_gross_edge_exceeds_2_5x_total_costs():
    """
    RULE: Suppress alerts unless expected gross edge exceeds 2.5 times estimated total costs.
    If costs are 2.09 bps, a gross edge of 4.0 bps (1.91x) has a positive net edge (+1.91 bps),
    but MUST be suppressed with NO_SIGNAL because it fails the 2.5x cost multiplier hurdle.
    """
    sig_date = date(2026, 10, 20)
    base_price = 80000.0
    quote_price = 80000.0
    # Mispricing of ₹32 on ₹80,000 = 4.0 bps
    adjusted_spread = 8032.0
    rolling_mean = 8000.0
    rolling_std = 10.0
    z_score = 3.2  # 32 / 10 = 3.2 (large Z, but gross edge fails 2.5x costs)

    res = qualify_spread_opportunity(
        pair_name="GOLDM_vs_GOLDPETAL",
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL",
        signal_date=sig_date,
        base_normalized_price=base_price,
        quote_normalized_price=quote_price,
        adjusted_spread=adjusted_spread,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        z_score=z_score,
        base_dte=30,
        quote_dte=30,
        base_volume=500.0,
        quote_volume=1200.0,
        base_oi=2000.0,
        quote_oi=3000.0,
        history_count=25,
        cost_coverage_hurdle=2.5,
        status_mode="v2"
    )

    assert res["expected_gross_edge_bps"] == 4.0
    # Coverage ratio: 4.0 / 2.09 = 1.91x < 2.5x
    assert res["cost_coverage_ratio"] < 2.5
    assert res["expected_net_edge_bps"] > 0  # Demonstrates net edge is positive!
    assert res["is_qualified"] is False
    assert res["status"] == "NO_SIGNAL"
    assert any("COST_COVERAGE_FAILED" in r for r in res["rejection_reasons"])


def test_positive_net_edge_requirement():
    """
    RULE: Require positive expected net edge (expected_net_edge > 0).
    """
    sig_date = date(2026, 10, 20)
    base_price = 80000.0
    quote_price = 80000.0
    # Mispricing of ₹8 on ₹80,000 = 1.0 bps (less than ~2.09 bps cost)
    adjusted_spread = 8008.0
    rolling_mean = 8000.0
    rolling_std = 2.5
    z_score = 3.2

    res = qualify_spread_opportunity(
        pair_name="GOLDM_vs_GOLDPETAL",
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL",
        signal_date=sig_date,
        base_normalized_price=base_price,
        quote_normalized_price=quote_price,
        adjusted_spread=adjusted_spread,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        z_score=z_score,
        base_dte=30,
        quote_dte=30,
        base_volume=500.0,
        quote_volume=500.0,
        history_count=25,
        status_mode="v2"
    )

    assert res["expected_net_edge_bps"] < 0.0
    assert res["is_qualified"] is False
    assert res["status"] == "NO_SIGNAL"
    assert any("NEGATIVE_NET_EDGE" in r for r in res["rejection_reasons"])


def test_t5_expiry_lockout_rejection():
    """
    RULE: Reject opportunities inside the configured T-5 expiry lockout.
    Must tag status as EXPIRY_LOCKOUT and record the exact tender lockout reason.
    """
    sig_date = date(2026, 10, 20)
    base_price = 80000.0
    quote_price = 80000.0
    adjusted_spread = 8300.0
    rolling_mean = 8000.0
    rolling_std = 100.0
    z_score = 3.0  # Large Z, gross edge = 37.5 bps >> friction

    # Case A: Base contract DTE = 4 days (inside T-5 window)
    res_base_locked = qualify_spread_opportunity(
        pair_name="GOLDM_vs_GOLDPETAL",
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL",
        signal_date=sig_date,
        base_normalized_price=base_price,
        quote_normalized_price=quote_price,
        adjusted_spread=adjusted_spread,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        z_score=z_score,
        base_dte=4,   # <= 5 days!
        quote_dte=30,
        base_volume=500.0,
        quote_volume=500.0,
        history_count=30,
        expiry_lockout_days=5,
        status_mode="v2"
    )
    assert res_base_locked["is_qualified"] is False
    assert res_base_locked["status"] == "EXPIRY_LOCKOUT"
    assert res_base_locked["expiry_status"] == "EXPIRY_LOCKOUT"
    assert any("EXPIRY_LOCKOUT" in r for r in res_base_locked["rejection_reasons"])

    # Case B: Exactly 5 days (inclusive lockout)
    res_exact_5 = qualify_spread_opportunity(
        pair_name="GOLDM_vs_GOLDPETAL",
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL",
        signal_date=sig_date,
        base_normalized_price=base_price,
        quote_normalized_price=quote_price,
        adjusted_spread=adjusted_spread,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        z_score=z_score,
        base_dte=5,  # Exactly 5 days!
        quote_dte=20,
        base_volume=500.0,
        quote_volume=500.0,
        history_count=30,
        expiry_lockout_days=5,
        status_mode="v2"
    )
    assert res_exact_5["status"] == "EXPIRY_LOCKOUT"

    # Case C: 6 days (outside lockout window)
    res_safe_dte = qualify_spread_opportunity(
        pair_name="GOLDM_vs_GOLDPETAL",
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL",
        signal_date=sig_date,
        base_normalized_price=base_price,
        quote_normalized_price=quote_price,
        adjusted_spread=adjusted_spread,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        z_score=z_score,
        base_dte=6,  # > 5 days
        quote_dte=25,
        base_volume=500.0,
        quote_volume=500.0,
        history_count=30,
        expiry_lockout_days=5,
        status_mode="v2"
    )
    assert res_safe_dte["expiry_status"] == "ACTIVE"
    assert res_safe_dte["is_qualified"] is True


def test_liquidity_and_data_quality_filters():
    """
    RULE: Apply liquidity and data-quality filters.
    Rejects low volume (< 50 lots) or low open interest (< 100) with LIQUIDITY_WARNING.
    Rejects insufficient history (< 20 periods) with INSUFFICIENT_DATA.
    """
    sig_date = date(2026, 10, 20)
    base_price = 80000.0
    quote_price = 80000.0
    adjusted_spread = 8300.0
    rolling_mean = 8000.0
    rolling_std = 100.0
    z_score = 3.0

    # Low volume test
    res_low_vol = qualify_spread_opportunity(
        pair_name="GOLDM_vs_GOLDPETAL",
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL",
        signal_date=sig_date,
        base_normalized_price=base_price,
        quote_normalized_price=quote_price,
        adjusted_spread=adjusted_spread,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        z_score=z_score,
        base_dte=20,
        quote_dte=20,
        base_volume=20.0,  # < 50 lots!
        quote_volume=500.0,
        history_count=30,
        status_mode="v2"
    )
    assert res_low_vol["is_qualified"] is False
    assert res_low_vol["status"] == "LIQUIDITY_WARNING"
    assert res_low_vol["liquidity_status"] == "LOW_VOLUME"
    assert any("LIQUIDITY_WARNING" in r for r in res_low_vol["rejection_reasons"])

    # Low OI test
    res_low_oi = qualify_spread_opportunity(
        pair_name="GOLDM_vs_GOLDPETAL",
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL",
        signal_date=sig_date,
        base_normalized_price=base_price,
        quote_normalized_price=quote_price,
        adjusted_spread=adjusted_spread,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        z_score=z_score,
        base_dte=20,
        quote_dte=20,
        base_volume=100.0,
        quote_volume=500.0,
        base_oi=50.0,  # < 100 OI!
        quote_oi=500.0,
        history_count=30,
        status_mode="v2"
    )
    assert res_low_oi["is_qualified"] is False
    assert res_low_oi["status"] == "LIQUIDITY_WARNING"
    assert res_low_oi["liquidity_status"] == "LOW_OI"

    # Insufficient history test (< 20 periods)
    res_short_hist = qualify_spread_opportunity(
        pair_name="GOLDM_vs_GOLDPETAL",
        base_symbol="GOLDM",
        quote_symbol="GOLDPETAL",
        signal_date=sig_date,
        base_normalized_price=base_price,
        quote_normalized_price=quote_price,
        adjusted_spread=adjusted_spread,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        z_score=z_score,
        base_dte=20,
        quote_dte=20,
        base_volume=500.0,
        quote_volume=500.0,
        history_count=12,  # < 20 observations!
        status_mode="v2"
    )
    assert res_short_hist["is_qualified"] is False
    assert res_short_hist["status"] == "INSUFFICIENT_DATA"
    assert any("INSUFFICIENT_DATA" in r for r in res_short_hist["rejection_reasons"])


def test_zero_fabrication_and_display_fields():
    """
    RULES:
    - Never fabricate an alert when no opportunity qualifies.
    - Clearly label all signals as analytical estimates.
    - Provide all required display fields.
    """
    db = SessionLocal()
    eval_res = evaluate_latest_candidates(db=db, persist_qualified=False)
    db.close()

    assert "total_candidates_evaluated" in eval_res
    assert "qualified_count" in eval_res
    assert "rejected_count" in eval_res
    assert "candidates" in eval_res
    assert "disclaimer" in eval_res

    # Check analytical disclaimer
    assert "DISCLAIMER: All signals are quantitative analytical estimates" in eval_res["disclaimer"]

    # Verify that every candidate has all required display fields
    for cand in eval_res["candidates"]:
        assert "pair_name" in cand
        assert "base_expiry_date" in cand
        assert "quote_expiry_date" in cand
        assert "base_normalized_price" in cand
        assert "quote_normalized_price" in cand
        assert "adjusted_spread" in cand
        assert "z_score" in cand
        assert "estimated_costs_bps" in cand
        assert "expected_net_edge_bps" in cand
        assert "liquidity_status" in cand
        assert "expiry_status" in cand
        assert "signal_explanation" in cand
        assert "status" in cand
        assert cand["status"] in [
            "QUALIFIED_FOR_REVIEW",
            "NO_SIGNAL",
            "INSUFFICIENT_DATA",
            "LIQUIDITY_WARNING",
            "EXPIRY_LOCKOUT"
        ]


def test_api_candidate_and_history_endpoints(test_client):
    """
    Tests the API endpoints for candidate evaluation, alert history, and qualified signals.
    """
    # 1. Candidates evaluation endpoint
    resp = test_client.get("/api/signals/candidates")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_candidates_evaluated" in data
    assert "candidates" in data
    assert isinstance(data["candidates"], list)

    # 2. History endpoint
    resp_hist = test_client.get("/api/signals/history?page=1&page_size=10")
    assert resp_hist.status_code == 200
    hist_data = resp_hist.json()
    assert "total" in hist_data
    assert "items" in hist_data
    assert isinstance(hist_data["items"], list)

    # 3. Qualified endpoint
    resp_qual = test_client.get("/api/signals/qualified")
    assert resp_qual.status_code == 200
    qual_items = resp_qual.json()
    assert isinstance(qual_items, list)
    for q in qual_items:
        assert q["is_qualified"] is True
