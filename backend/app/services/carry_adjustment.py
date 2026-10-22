import math
from datetime import date
from typing import Dict, Any, Optional
from app.config import settings


def get_annualized_carry_rate(
    custom_risk_free: Optional[float] = None,
    custom_storage: Optional[float] = None
) -> float:
    """Returns combined annualized cost-of-carry rate (financing interest + physical storage/insurance)."""
    rf = custom_risk_free if custom_risk_free is not None else settings.ANNUAL_RISK_FREE_RATE
    storage = custom_storage if custom_storage is not None else settings.GOLD_STORAGE_INSURANCE_RATE
    return rf + storage


def calculate_carry_adjustment(
    price_per_10g: float,
    days_to_expiry: int,
    benchmark_dte: int = 0,
    annual_carry_rate: Optional[float] = None,
    rate_source: Optional[str] = None,
    method: str = "exponential"
) -> Dict[str, Any]:
    """
    Adjusts futures settlement price for the time-value-of-carry relative to a benchmark DTE (e.g. spot / 0 DTE).

    Supports:
      1. Configurable exponential cost-of-carry (continuous compounding):
         F_adj = F(T) * exp(-C * (T - T_b) / 365.0)
         Discount Factor = exp(-C * (T - T_b) / 365.0)
      2. Linear cost-of-carry (discrete convention):
         Discount Factor = (1 + C * (T_b / 365)) / (1 + C * (T / 365))
      3. Historical carry rate inputs when available, with explicit labeling
         when fixed rate assumptions are used.

    Returns:
      annualized_carry_rate: Combined financing + storage rate (e.g. 0.070)
      carry_rate_source: Explicit label (e.g. "HISTORICAL" or "FIXED_ASSUMPTION_7.0PCT")
      discount_factor: Multiplier applied to futures price
      carry_adjusted_price_per_10g: Resulting carry-neutral price
      carry_drag_rupees: Amount of carry component removed
      method: "exponential" or "linear"
    """
    if annual_carry_rate is None:
        annual_carry_rate = get_annualized_carry_rate()
        effective_source = rate_source or f"FIXED_ASSUMPTION_{annual_carry_rate * 100:.1f}PCT"
    else:
        effective_source = rate_source or "HISTORICAL"

    if days_to_expiry <= benchmark_dte:
        # Zero or negative carry horizon
        discount_factor = 1.0
        carry_adjusted_price = price_per_10g
        carry_drag_rupees = 0.0
    else:
        t_years = days_to_expiry / 365.0
        tb_years = benchmark_dte / 365.0
        dt_years = (days_to_expiry - benchmark_dte) / 365.0

        if method == "exponential":
            discount_factor = math.exp(-annual_carry_rate * dt_years)
        else:
            forward_factor_contract = 1.0 + (annual_carry_rate * t_years)
            forward_factor_benchmark = 1.0 + (annual_carry_rate * tb_years)
            discount_factor = forward_factor_benchmark / forward_factor_contract

        carry_adjusted_price = price_per_10g * discount_factor
        carry_drag_rupees = price_per_10g - carry_adjusted_price

    return {
        "annualized_carry_rate": round(annual_carry_rate, 4),
        "carry_rate_source": effective_source,
        "discount_factor": round(discount_factor, 6),
        "carry_adjusted_price_per_10g": round(carry_adjusted_price, 2),
        "carry_drag_rupees": round(carry_drag_rupees, 2),
        "method": method
    }

