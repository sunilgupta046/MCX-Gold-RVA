"""
Signal Qualification and Alert Module for MCX Gold RVA.

Rules:
1. Evaluate normalized and maturity-adjusted contract spreads.
2. Calculate expected gross edge and estimated total round-trip costs.
3. Calculate expected net edge.
4. Apply liquidity and data-quality filters.
5. Reject opportunities inside the configured T-5 expiry lockout (DTE <= 5 days).
6. Suppress alerts unless expected gross edge exceeds 2.5 times estimated total costs.
7. Require positive expected net edge (expected_net_edge > 0).
8. Avoid duplicate alerts for the same contract pair and expiry combination.
9. Record the exact reasons why a candidate was rejected.
10. Never fabricate an alert when no opportunity qualifies.

Statuses:
- QUALIFIED_FOR_REVIEW
- NO_SIGNAL
- INSUFFICIENT_DATA
- LIQUIDITY_WARNING
- EXPIRY_LOCKOUT
"""

import json
from datetime import date
from typing import Dict, Any, List, Optional
from app.services.transaction_costs import calculate_pair_roundtrip_cost_bps

# Quantitative Rule Parameters
EXPIRY_LOCKOUT_DAYS_DEFAULT = 5
COST_COVERAGE_HURDLE_DEFAULT = 2.5
MIN_VOLUME_LOTS_DEFAULT = 50.0
MIN_OPEN_INTEREST_DEFAULT = 100.0
MIN_HISTORY_PERIODS_DEFAULT = 20
Z_ENTRY_THRESHOLD_DEFAULT = 2.0

ANALYTICAL_DISCLAIMER = (
    "DISCLAIMER: All signals are quantitative analytical estimates based on statistical "
    "divergence and modeled MCX transaction costs, not guaranteed arbitrage or executable trading instructions."
)


def qualify_spread_opportunity(
    pair_name: str,
    base_symbol: str,
    quote_symbol: str,
    signal_date: date,
    base_normalized_price: float,
    quote_normalized_price: float,
    adjusted_spread: float,
    rolling_mean: Optional[float],
    rolling_std: Optional[float],
    z_score: Optional[float],
    base_expiry_date: Optional[date] = None,
    quote_expiry_date: Optional[date] = None,
    base_volume: Optional[float] = None,
    quote_volume: Optional[float] = None,
    base_oi: Optional[float] = None,
    quote_oi: Optional[float] = None,
    base_dte: Optional[int] = None,
    quote_dte: Optional[int] = None,
    history_count: int = 20,
    is_data_stale: bool = False,
    price_jump_flag: bool = False,
    expiry_lockout_days: int = EXPIRY_LOCKOUT_DAYS_DEFAULT,
    cost_coverage_hurdle: float = COST_COVERAGE_HURDLE_DEFAULT,
    min_volume_lots: float = MIN_VOLUME_LOTS_DEFAULT,
    min_open_interest: float = MIN_OPEN_INTEREST_DEFAULT,
    z_threshold: float = Z_ENTRY_THRESHOLD_DEFAULT,
    status_mode: str = "v2"  # "v2" uses QUALIFIED_FOR_REVIEW, "v1" uses ACTIVE
) -> Dict[str, Any]:
    """
    Rigorously qualifies a relative-value opportunity across all 10 quantitative rules.
    Returns full diagnostics including exact rejection reasons and 5-state status.
    """
    rejection_reasons: List[str] = []
    
    # Average price for percentage/basis point conversions
    avg_price = max(1.0, (base_normalized_price + quote_normalized_price) / 2.0)

    # 1. Calculate Expected Gross Edge
    if rolling_mean is not None:
        expected_gross_edge_inr = abs(adjusted_spread - rolling_mean)
        expected_gross_edge_bps = (expected_gross_edge_inr / avg_price) * 10000.0
    else:
        expected_gross_edge_inr = 0.0
        expected_gross_edge_bps = 0.0

    # 2. Calculate Estimated Total Round-Trip Costs
    cost_data = calculate_pair_roundtrip_cost_bps(
        base_price_10g=base_normalized_price,
        quote_price_10g=quote_normalized_price,
        base_symbol=base_symbol,
        quote_symbol=quote_symbol
    )
    estimated_costs_bps = cost_data.get("roundtrip_cost_bps", 6.5)
    estimated_costs_inr = (estimated_costs_bps / 10000.0) * avg_price

    # 3. Calculate Expected Net Edge & Cost Coverage Ratio
    expected_net_edge_bps = expected_gross_edge_bps - estimated_costs_bps
    expected_net_edge_inr = expected_gross_edge_inr - estimated_costs_inr
    cost_coverage_ratio = (
        expected_gross_edge_bps / estimated_costs_bps if estimated_costs_bps > 0 else 0.0
    )

    # Defaults for diagnostics
    liquidity_status = "ADEQUATE"
    expiry_status = "ACTIVE"
    primary_status = "QUALIFIED_FOR_REVIEW"

    # RULE 4: Data Quality & History Length Filters
    if history_count < MIN_HISTORY_PERIODS_DEFAULT:
        rejection_reasons.append(
            f"INSUFFICIENT_DATA: History window has only {history_count} observations "
            f"(minimum {MIN_HISTORY_PERIODS_DEFAULT} required for rolling statistics)."
        )
        primary_status = "INSUFFICIENT_DATA"
    elif rolling_mean is None or rolling_std is None or rolling_std <= 0:
        rejection_reasons.append(
            "INSUFFICIENT_DATA: Spread standard deviation or rolling mean is undefined or zero."
        )
        primary_status = "INSUFFICIENT_DATA"
    elif is_data_stale:
        rejection_reasons.append("DATA_QUALITY_FILTER: Bhavcopy settlement data is stale or missing.")
        primary_status = "INSUFFICIENT_DATA"
    elif price_jump_flag:
        rejection_reasons.append("DATA_QUALITY_FILTER: Unconfirmed anomalous price jump outlier detected.")
        primary_status = "INSUFFICIENT_DATA"

    # RULE 5: T-5 Expiry Lockout Filter
    # Effective DTE is the minimum of both legs if available
    effective_dte = None
    if base_dte is not None and quote_dte is not None:
        effective_dte = min(base_dte, quote_dte)
    elif base_dte is not None:
        effective_dte = base_dte
    elif quote_dte is not None:
        effective_dte = quote_dte

    is_expiry_locked = False
    if effective_dte is not None and effective_dte <= expiry_lockout_days:
        is_expiry_locked = True
        expiry_status = "EXPIRY_LOCKOUT"
        rejection_reasons.append(
            f"EXPIRY_LOCKOUT: Contract inside T-{expiry_lockout_days} tender delivery period "
            f"(Effective DTE: {effective_dte}d <= {expiry_lockout_days}d threshold). "
            f"Physical delivery risk prevents new entry."
        )
        if primary_status == "QUALIFIED_FOR_REVIEW":
            primary_status = "EXPIRY_LOCKOUT"

    # RULE 4 (Cont.): Liquidity Filters (Volume & Open Interest)
    is_liquid = True
    if base_volume is not None and base_volume < min_volume_lots:
        is_liquid = False
        liquidity_status = "LOW_VOLUME"
        rejection_reasons.append(
            f"LIQUIDITY_WARNING: Base symbol {base_symbol} volume ({base_volume:.0f} lots) "
            f"< {min_volume_lots:.0f} lot minimum threshold."
        )
    if quote_volume is not None and quote_volume < min_volume_lots:
        is_liquid = False
        liquidity_status = "LOW_VOLUME"
        rejection_reasons.append(
            f"LIQUIDITY_WARNING: Quote symbol {quote_symbol} volume ({quote_volume:.0f} lots) "
            f"< {min_volume_lots:.0f} lot minimum threshold."
        )
    if base_oi is not None and base_oi < min_open_interest:
        is_liquid = False
        if liquidity_status == "ADEQUATE":
            liquidity_status = "LOW_OI"
        rejection_reasons.append(
            f"LIQUIDITY_WARNING: Base symbol {base_symbol} open interest ({base_oi:.0f}) "
            f"< {min_open_interest:.0f} minimum threshold."
        )
    if quote_oi is not None and quote_oi < min_open_interest:
        is_liquid = False
        if liquidity_status == "ADEQUATE":
            liquidity_status = "LOW_OI"
        rejection_reasons.append(
            f"LIQUIDITY_WARNING: Quote symbol {quote_symbol} open interest ({quote_oi:.0f}) "
            f"< {min_open_interest:.0f} minimum threshold."
        )

    if not is_liquid and primary_status == "QUALIFIED_FOR_REVIEW":
        primary_status = "LIQUIDITY_WARNING"

    # Statistical Divergence Check
    diverged = z_score is not None and abs(z_score) >= z_threshold
    if not diverged:
        rejection_reasons.append(
            f"NO_SIGNAL: Current spread Z-score ({z_score or 0.0:.2f}σ) "
            f"does not exceed entry threshold (±{z_threshold:.1f}σ)."
        )
        if primary_status == "QUALIFIED_FOR_REVIEW":
            primary_status = "NO_SIGNAL"

    # RULE 6: 2.5x Total Cost Hurdle Rule
    # Suppress alerts unless expected gross edge exceeds 2.5 times estimated total costs
    if cost_coverage_ratio < cost_coverage_hurdle:
        rejection_reasons.append(
            f"COST_COVERAGE_FAILED: Expected gross edge ({expected_gross_edge_bps:.1f} bps) "
            f"fails {cost_coverage_hurdle}x cost coverage hurdle "
            f"({cost_coverage_ratio:.2f}x < {cost_coverage_hurdle:.1f}x required, "
            f"needing {cost_coverage_hurdle * estimated_costs_bps:.1f} bps)."
        )
        if primary_status == "QUALIFIED_FOR_REVIEW":
            primary_status = "NO_SIGNAL"

    # RULE 7: Require Positive Expected Net Edge
    if expected_net_edge_bps <= 0.0:
        rejection_reasons.append(
            f"NEGATIVE_NET_EDGE: Expected net edge is non-positive ({expected_net_edge_bps:.1f} bps)."
        )
        if primary_status == "QUALIFIED_FOR_REVIEW":
            primary_status = "NO_SIGNAL"

    # Overall qualification flag
    is_qualified = (len(rejection_reasons) == 0) and (primary_status == "QUALIFIED_FOR_REVIEW")

    # Map status based on compatibility mode
    if status_mode == "v1":
        final_status = "ACTIVE" if is_qualified else "DISQUALIFIED"
    else:
        final_status = primary_status

    # Determine trading action and conviction strength
    action = "NEUTRAL"
    strength = "NONE"
    target_spread = rolling_mean if rolling_mean is not None else adjusted_spread
    stop_loss_spread = None

    if z_score is not None and diverged:
        if z_score >= z_threshold:
            action = f"SHORT_{base_symbol}__LONG_{quote_symbol}"
            if rolling_std is not None and rolling_mean is not None:
                stop_loss_spread = rolling_mean + (3.5 * rolling_std)
            if z_score >= 3.0:
                strength = "EXTREME"
            elif z_score >= 2.5:
                strength = "HIGH"
            else:
                strength = "MEDIUM"
        else:
            action = f"LONG_{base_symbol}__SHORT_{quote_symbol}"
            if rolling_std is not None and rolling_mean is not None:
                stop_loss_spread = rolling_mean - (3.5 * rolling_std)
            if z_score <= -3.0:
                strength = "EXTREME"
            elif z_score <= -2.5:
                strength = "HIGH"
            else:
                strength = "MEDIUM"

    # Format Explanation
    summary_reasons = " | ".join(rejection_reasons) if rejection_reasons else None
    if is_qualified:
        explanation = (
            f"[QUALIFIED] {pair_name.replace('_vs_', ' vs ')} exhibited a statistically significant "
            f"divergence of {z_score:.2f}σ (Spread: ₹{adjusted_spread:.2f}/10g vs 20d mean ₹{rolling_mean:.2f}/10g). "
            f"Gross edge: {expected_gross_edge_bps:.1f} bps (₹{expected_gross_edge_inr:.2f}/10g), "
            f"Estimated roundtrip costs: {estimated_costs_bps:.1f} bps (₹{estimated_costs_inr:.2f}/10g). "
            f"Cost coverage ratio: {cost_coverage_ratio:.2f}x (passes {cost_coverage_hurdle}x hurdle). "
            f"Net edge: +{expected_net_edge_bps:.1f} bps (₹{expected_net_edge_inr:.2f}/10g). "
            f"Contracts have {effective_dte}d to expiry and pass liquidity filters."
        )
    else:
        explanation = (
            f"[{final_status}] Opportunity rejected. {summary_reasons}"
        )

    return {
        "signal_date": signal_date,
        "pair_name": pair_name,
        "base_symbol": base_symbol,
        "quote_symbol": quote_symbol,
        "base_expiry_date": base_expiry_date,
        "quote_expiry_date": quote_expiry_date,
        "base_normalized_price": round(base_normalized_price, 2),
        "quote_normalized_price": round(quote_normalized_price, 2),
        "adjusted_spread": round(adjusted_spread, 2),
        "action": action,
        "strength": strength,
        "z_score": round(z_score, 2) if z_score is not None else 0.0,
        "target_spread": round(target_spread, 2),
        "stop_loss_spread": round(stop_loss_spread, 2) if stop_loss_spread is not None else None,
        "expected_gross_edge_bps": round(expected_gross_edge_bps, 2),
        "expected_gross_edge_inr": round(expected_gross_edge_inr, 2),
        "estimated_costs_bps": round(estimated_costs_bps, 2),
        "estimated_costs_inr": round(estimated_costs_inr, 2),
        "expected_net_edge_bps": round(expected_net_edge_bps, 2),
        "expected_net_edge_inr": round(expected_net_edge_inr, 2),
        "cost_coverage_ratio": round(cost_coverage_ratio, 2),
        "days_to_expiry": effective_dte,
        "base_dte": base_dte,
        "quote_dte": quote_dte,
        "base_volume": round(base_volume, 1) if base_volume is not None else None,
        "quote_volume": round(quote_volume, 1) if quote_volume is not None else None,
        "base_oi": round(base_oi, 1) if base_oi is not None else None,
        "quote_oi": round(quote_oi, 1) if quote_oi is not None else None,
        "liquidity_status": liquidity_status,
        "expiry_status": expiry_status,
        "expiry_eligible": not is_expiry_locked,
        "liquidity_qualified": is_liquid,
        "is_qualified": is_qualified,
        "status": final_status,
        "rejection_reason": summary_reasons,
        "rejection_reasons": rejection_reasons,
        "rejection_reasons_json": json.dumps(rejection_reasons),
        "signal_explanation": explanation,
        "rational": explanation,
        "disclaimer": ANALYTICAL_DISCLAIMER,
        # Legacy field compatibility
        "spread_value_per_10g": round(adjusted_spread, 2),
        "gross_mispricing_bps": round(expected_gross_edge_bps, 2),
        "est_roundtrip_cost_bps": round(estimated_costs_bps, 2),
        "net_edge_bps": round(expected_net_edge_bps, 2),
        "avg_volume": min(base_volume or 9999, quote_volume or 9999) if (base_volume or quote_volume) else None
    }


def evaluate_latest_candidates(
    db: Any,
    expiry_lockout_days: int = EXPIRY_LOCKOUT_DAYS_DEFAULT,
    cost_coverage_hurdle: float = COST_COVERAGE_HURDLE_DEFAULT,
    persist_qualified: bool = True
) -> Dict[str, Any]:
    """
    Evaluates all active cross-contract pair candidates on the latest settlement date.
    Strictly follows all 10 qualification rules and records exact rejection reasons.
    Avoids duplicate alerts for the same (pair, base_expiry, quote_expiry).
    Never fabricates an alert when no candidate qualifies.
    """
    from app.models.bhavcopy import BhavcopyRecord
    from app.models.normalized_price import NormalizedPrice
    from app.models.spread_metrics import SpreadMetric
    from app.models.signals import RVASignal

    pairs = [
        ("GOLDM", "GOLDPETAL"),
        ("GOLDM", "GOLDGUINEA"),
        ("GOLDM", "GOLDTEN"),
        ("GOLDTEN", "GOLDPETAL"),
        ("GOLDTEN", "GOLDGUINEA"),
        ("GOLDGUINEA", "GOLDPETAL"),
    ]

    # Find latest available date
    latest_rec = db.query(BhavcopyRecord).order_by(BhavcopyRecord.trade_date.desc()).first()
    if not latest_rec:
        return {
            "as_of_date": None,
            "total_candidates_evaluated": 0,
            "qualified_count": 0,
            "rejected_count": 0,
            "status_summary": {
                "QUALIFIED_FOR_REVIEW": 0,
                "NO_SIGNAL": 0,
                "INSUFFICIENT_DATA": 0,
                "LIQUIDITY_WARNING": 0,
                "EXPIRY_LOCKOUT": 0,
            },
            "candidates": [],
            "disclaimer": ANALYTICAL_DISCLAIMER
        }

    as_of_date = latest_rec.trade_date
    candidates = []
    seen_combos = set()

    for base, quote in pairs:
        pair_name = f"{base}_vs_{quote}"
        hist_count = db.query(SpreadMetric).filter(SpreadMetric.pair_name == pair_name).count()

        sm = (
            db.query(SpreadMetric)
            .filter(SpreadMetric.pair_name == pair_name, SpreadMetric.trade_date <= as_of_date)
            .order_by(SpreadMetric.trade_date.desc())
            .first()
        )

        np_base = (
            db.query(NormalizedPrice)
            .filter(NormalizedPrice.symbol == base, NormalizedPrice.trade_date <= as_of_date)
            .order_by(NormalizedPrice.trade_date.desc())
            .first()
        )
        np_quote = (
            db.query(NormalizedPrice)
            .filter(NormalizedPrice.symbol == quote, NormalizedPrice.trade_date <= as_of_date)
            .order_by(NormalizedPrice.trade_date.desc())
            .first()
        )

        bhav_base = (
            db.query(BhavcopyRecord)
            .filter(BhavcopyRecord.symbol == base, BhavcopyRecord.trade_date <= as_of_date)
            .order_by(BhavcopyRecord.trade_date.desc())
            .first()
        )
        bhav_quote = (
            db.query(BhavcopyRecord)
            .filter(BhavcopyRecord.symbol == quote, BhavcopyRecord.trade_date <= as_of_date)
            .order_by(BhavcopyRecord.trade_date.desc())
            .first()
        )

        # Baseline pricing fallbacks
        base_price = np_base.price_per_10g if np_base else 80000.0
        quote_price = np_quote.price_per_10g if np_quote else 80000.0
        adjusted_spread = sm.carry_adjusted_spread_per_10g if sm else (base_price - quote_price)
        rm = sm.rolling_mean_20d if sm else None
        rstd = sm.rolling_std_20d if sm else None
        z = sm.z_score if sm else None

        base_exp = bhav_base.expiry_date if bhav_base else None
        quote_exp = bhav_quote.expiry_date if bhav_quote else None

        base_dte = (base_exp - as_of_date).days if (base_exp and as_of_date) else (bhav_base.days_to_expiry if bhav_base else None)
        quote_dte = (quote_exp - as_of_date).days if (quote_exp and as_of_date) else (bhav_quote.days_to_expiry if bhav_quote else None)

        base_vol = float(bhav_base.volume_lots) if (bhav_base and bhav_base.volume_lots is not None) else None
        quote_vol = float(bhav_quote.volume_lots) if (bhav_quote and bhav_quote.volume_lots is not None) else None
        base_oi = float(bhav_base.open_interest) if (bhav_base and bhav_base.open_interest is not None) else None
        quote_oi = float(bhav_quote.open_interest) if (bhav_quote and bhav_quote.open_interest is not None) else None

        # Deduplication key for (pair, base_expiry, quote_expiry)
        combo_key = (pair_name, base_exp, quote_exp)
        if combo_key in seen_combos:
            continue
        seen_combos.add(combo_key)

        eval_res = qualify_spread_opportunity(
            pair_name=pair_name,
            base_symbol=base,
            quote_symbol=quote,
            signal_date=as_of_date,
            base_normalized_price=base_price,
            quote_normalized_price=quote_price,
            adjusted_spread=adjusted_spread,
            rolling_mean=rm,
            rolling_std=rstd,
            z_score=z,
            base_expiry_date=base_exp,
            quote_expiry_date=quote_exp,
            base_volume=base_vol,
            quote_volume=quote_vol,
            base_oi=base_oi,
            quote_oi=quote_oi,
            base_dte=base_dte,
            quote_dte=quote_dte,
            history_count=hist_count,
            expiry_lockout_days=expiry_lockout_days,
            cost_coverage_hurdle=cost_coverage_hurdle,
            status_mode="v2"
        )
        candidates.append(eval_res)

        # Persist qualified signals or record into DB if not already existing
        if persist_qualified and eval_res["is_qualified"]:
            existing = (
                db.query(RVASignal)
                .filter(
                    RVASignal.pair_name == pair_name,
                    RVASignal.signal_date == as_of_date,
                    RVASignal.base_expiry_date == base_exp,
                    RVASignal.quote_expiry_date == quote_exp
                )
                .first()
            )
            if not existing:
                sig_record = RVASignal(
                    signal_date=as_of_date,
                    pair_name=pair_name,
                    base_symbol=base,
                    quote_symbol=quote,
                    base_expiry_date=base_exp,
                    quote_expiry_date=quote_exp,
                    base_normalized_price=eval_res["base_normalized_price"],
                    quote_normalized_price=eval_res["quote_normalized_price"],
                    adjusted_spread=eval_res["adjusted_spread"],
                    action=eval_res["action"],
                    strength=eval_res["strength"],
                    z_score=eval_res["z_score"],
                    spread_value_per_10g=eval_res["spread_value_per_10g"],
                    target_spread=eval_res["target_spread"],
                    stop_loss_spread=eval_res["stop_loss_spread"],
                    gross_mispricing_bps=eval_res["gross_mispricing_bps"],
                    est_roundtrip_cost_bps=eval_res["est_roundtrip_cost_bps"],
                    net_edge_bps=eval_res["net_edge_bps"],
                    expected_gross_edge_bps=eval_res["expected_gross_edge_bps"],
                    expected_gross_edge_inr=eval_res["expected_gross_edge_inr"],
                    estimated_costs_bps=eval_res["estimated_costs_bps"],
                    estimated_costs_inr=eval_res["estimated_costs_inr"],
                    expected_net_edge_bps=eval_res["expected_net_edge_bps"],
                    expected_net_edge_inr=eval_res["expected_net_edge_inr"],
                    cost_coverage_ratio=eval_res["cost_coverage_ratio"],
                    days_to_expiry=eval_res["days_to_expiry"],
                    base_dte=eval_res["base_dte"],
                    quote_dte=eval_res["quote_dte"],
                    avg_volume=eval_res["avg_volume"],
                    base_volume=eval_res["base_volume"],
                    quote_volume=eval_res["quote_volume"],
                    base_oi=eval_res["base_oi"],
                    quote_oi=eval_res["quote_oi"],
                    liquidity_status=eval_res["liquidity_status"],
                    expiry_status=eval_res["expiry_status"],
                    status=eval_res["status"],
                    expiry_eligible=eval_res["expiry_eligible"],
                    liquidity_qualified=eval_res["liquidity_qualified"],
                    is_qualified=eval_res["is_qualified"],
                    rejection_reason=eval_res["rejection_reason"],
                    rejection_reasons_json=eval_res["rejection_reasons_json"],
                    signal_explanation=eval_res["signal_explanation"],
                    rational=eval_res["rational"],
                    disclaimer=eval_res["disclaimer"]
                )
                db.add(sig_record)
                db.commit()

    status_summary = {
        "QUALIFIED_FOR_REVIEW": sum(1 for c in candidates if c["status"] == "QUALIFIED_FOR_REVIEW"),
        "NO_SIGNAL": sum(1 for c in candidates if c["status"] == "NO_SIGNAL"),
        "INSUFFICIENT_DATA": sum(1 for c in candidates if c["status"] == "INSUFFICIENT_DATA"),
        "LIQUIDITY_WARNING": sum(1 for c in candidates if c["status"] == "LIQUIDITY_WARNING"),
        "EXPIRY_LOCKOUT": sum(1 for c in candidates if c["status"] == "EXPIRY_LOCKOUT"),
    }

    return {
        "as_of_date": as_of_date,
        "total_candidates_evaluated": len(candidates),
        "qualified_count": status_summary["QUALIFIED_FOR_REVIEW"],
        "rejected_count": len(candidates) - status_summary["QUALIFIED_FOR_REVIEW"],
        "status_summary": status_summary,
        "candidates": candidates,
        "disclaimer": ANALYTICAL_DISCLAIMER
    }

