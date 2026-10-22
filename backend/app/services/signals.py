import json
from typing import List, Dict, Any, Optional
from datetime import date
from app.services.transaction_costs import calculate_pair_roundtrip_cost_bps
from app.services.signal_qualification import qualify_spread_opportunity, ANALYTICAL_DISCLAIMER

# Quantitative guardrails for signal generation
MIN_DAYS_TO_EXPIRY = 5        # MCX tender/delivery period protection: reject contracts with DTE < 5
MIN_AVG_VOLUME_LOTS = 50      # Reject illiquid contracts to prevent slippage/liquidity traps
MIN_NET_EDGE_BPS = 2.0        # Must yield at least +2 bps edge after ALL statutory exchange costs
COST_COVERAGE_HURDLE = 2.5    # Gross edge must exceed 2.5x estimated total costs


def evaluate_signal_for_pair(
    pair_name: str,
    base_symbol: str,
    quote_symbol: str,
    signal_date: date,
    current_spread: float,
    rolling_mean: float,
    rolling_std: float,
    z_score: float,
    base_price_10g: float,
    quote_price_10g: float,
    z_threshold: float = 2.0,
    days_to_expiry: Optional[int] = None,
    avg_volume: Optional[float] = None,
    base_expiry_date: Optional[date] = None,
    quote_expiry_date: Optional[date] = None,
    base_volume: Optional[float] = None,
    quote_volume: Optional[float] = None,
    base_oi: Optional[float] = None,
    quote_oi: Optional[float] = None,
    cost_coverage_hurdle: float = COST_COVERAGE_HURDLE,
    status_mode: str = "v1"
) -> Optional[Dict[str, Any]]:
    """
    Evaluates relative-value trading signals with strict risk qualification:
      - Statistical divergence: |Z| >= z_threshold
      - Estimated roundtrip transaction costs (Exchange, SEBI, CTT, GST, Stamp Duty, Slippage)
      - Net edge check: Gross mispricing bps must exceed roundtrip cost bps + minimum edge
      - Expiry eligibility: DTE >= 5 days (avoids MCX physical delivery tender period)
      - Liquidity limitations: avg daily volume >= 50 lots (avoids unexecutable fills)

    Does NOT generate a qualified trade signal merely because Z-score looks large.
    """
    if rolling_std is None or rolling_std <= 0:
        return None

    # Calculate transaction costs
    cost_data = calculate_pair_roundtrip_cost_bps(base_price_10g, quote_price_10g, base_symbol, quote_symbol)
    est_roundtrip_cost_bps = cost_data["roundtrip_cost_bps"]

    # Gross mispricing in basis points relative to average price
    avg_price = max(1.0, (base_price_10g + quote_price_10g) / 2.0)
    abs_mispricing_inr = abs(current_spread - rolling_mean)
    gross_mispricing_bps = (abs_mispricing_inr / avg_price) * 10000.0

    net_edge_bps = gross_mispricing_bps - est_roundtrip_cost_bps
    cost_coverage_ratio = gross_mispricing_bps / est_roundtrip_cost_bps if est_roundtrip_cost_bps > 0 else 0.0

    # 1. Statistical divergence check
    if abs(z_score) < z_threshold:
        return None

    # 2. Expiry Eligibility
    expiry_eligible = True
    expiry_reason = None
    if days_to_expiry is not None and days_to_expiry < MIN_DAYS_TO_EXPIRY:
        expiry_eligible = False
        expiry_reason = f"NEAR_EXPIRY_RISK: DTE ({days_to_expiry}d) < {MIN_DAYS_TO_EXPIRY}d minimum tender buffer"

    # 3. Liquidity Qualification
    effective_vol = avg_volume if avg_volume is not None else min(base_volume or 9999, quote_volume or 9999)
    liquidity_qualified = True
    liquidity_reason = None
    if effective_vol is not None and effective_vol < MIN_AVG_VOLUME_LOTS:
        liquidity_qualified = False
        liquidity_reason = f"LOW_LIQUIDITY: Volume ({effective_vol:.0f} lots) < {MIN_AVG_VOLUME_LOTS} lot threshold"

    # 4. Cost Hurdle Qualification
    cost_qualified = net_edge_bps >= MIN_NET_EDGE_BPS
    cost_reason = None
    if not cost_qualified:
        cost_reason = f"INSUFFICIENT_EDGE: Net edge ({net_edge_bps:.1f} bps) < {MIN_NET_EDGE_BPS:.1f} bps cost hurdle"

    # Overall qualification
    is_qualified = expiry_eligible and liquidity_qualified and cost_qualified
    rejection_reasons = [r for r in [expiry_reason, liquidity_reason, cost_reason] if r is not None]
    rejection_reason = " | ".join(rejection_reasons) if rejection_reasons else None

    # Determine action and strength
    if z_score >= z_threshold:
        action = f"SHORT_{base_symbol}__LONG_{quote_symbol}"
        stop_loss_spread = rolling_mean + (3.5 * rolling_std)
        if z_score >= 3.0:
            strength = "EXTREME"
        elif z_score >= 2.5:
            strength = "HIGH"
        else:
            strength = "MEDIUM"
        direction_text = f"{base_symbol} is trading at a {z_score:.2f}σ premium to {quote_symbol}."
    else:
        action = f"LONG_{base_symbol}__SHORT_{quote_symbol}"
        stop_loss_spread = rolling_mean - (3.5 * rolling_std)
        if z_score <= -3.0:
            strength = "EXTREME"
        elif z_score <= -2.5:
            strength = "HIGH"
        else:
            strength = "MEDIUM"
        direction_text = f"{base_symbol} is trading at a {abs(z_score):.2f}σ discount to {quote_symbol}."

    if status_mode == "v2":
        if not expiry_eligible:
            status = "EXPIRY_LOCKOUT"
        elif not liquidity_qualified:
            status = "LIQUIDITY_WARNING"
        elif not is_qualified:
            status = "NO_SIGNAL"
        else:
            status = "QUALIFIED_FOR_REVIEW"
    else:
        status = "ACTIVE" if is_qualified else "DISQUALIFIED"

    target_spread = rolling_mean

    qual_label = "QUALIFIED" if is_qualified else f"DISQUALIFIED ({rejection_reason})"
    rational = (
        f"[{qual_label}] {direction_text} "
        f"Mean reversion target is ₹{rolling_mean:.2f}/10g. "
        f"Gross mispricing: {gross_mispricing_bps:.1f} bps, Est friction: {est_roundtrip_cost_bps:.1f} bps, Net edge: {net_edge_bps:.1f} bps. "
        + (f"Rejection note: {rejection_reason}" if rejection_reason else "Meets liquidity, DTE, and cost criteria.")
    )

    return {
        "signal_date": signal_date,
        "pair_name": pair_name,
        "base_symbol": base_symbol,
        "quote_symbol": quote_symbol,
        "base_expiry_date": base_expiry_date,
        "quote_expiry_date": quote_expiry_date,
        "base_normalized_price": round(base_price_10g, 2),
        "quote_normalized_price": round(quote_price_10g, 2),
        "adjusted_spread": round(current_spread, 2),
        "action": action,
        "strength": strength,
        "z_score": round(z_score, 2),
        "spread_value_per_10g": round(current_spread, 2),
        "target_spread": round(target_spread, 2),
        "stop_loss_spread": round(stop_loss_spread, 2) if stop_loss_spread else None,
        "gross_mispricing_bps": round(gross_mispricing_bps, 2),
        "est_roundtrip_cost_bps": round(est_roundtrip_cost_bps, 2),
        "net_edge_bps": round(net_edge_bps, 2),
        "expected_gross_edge_bps": round(gross_mispricing_bps, 2),
        "expected_gross_edge_inr": round(abs_mispricing_inr, 2),
        "estimated_costs_bps": round(est_roundtrip_cost_bps, 2),
        "estimated_costs_inr": round((est_roundtrip_cost_bps / 10000.0) * avg_price, 2),
        "expected_net_edge_bps": round(net_edge_bps, 2),
        "expected_net_edge_inr": round(abs_mispricing_inr - ((est_roundtrip_cost_bps / 10000.0) * avg_price), 2),
        "cost_coverage_ratio": round(cost_coverage_ratio, 2),
        "days_to_expiry": days_to_expiry,
        "base_dte": days_to_expiry,
        "quote_dte": days_to_expiry,
        "avg_volume": round(effective_vol, 1) if effective_vol is not None else None,
        "base_volume": base_volume,
        "quote_volume": quote_volume,
        "base_oi": base_oi,
        "quote_oi": quote_oi,
        "liquidity_status": "ADEQUATE" if liquidity_qualified else "LOW_VOLUME",
        "expiry_status": "ACTIVE" if expiry_eligible else "EXPIRY_LOCKOUT",
        "expiry_eligible": expiry_eligible,
        "liquidity_qualified": liquidity_qualified,
        "is_qualified": is_qualified,
        "rejection_reason": rejection_reason,
        "rejection_reasons": rejection_reasons,
        "rejection_reasons_json": json.dumps(rejection_reasons),
        "status": status,
        "rational": rational,
        "signal_explanation": rational,
        "disclaimer": ANALYTICAL_DISCLAIMER
    }


