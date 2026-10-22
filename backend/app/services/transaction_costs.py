from typing import Dict, Any
from app.config import settings


def calculate_transaction_costs(
    turnover_inr: float,
    is_buy: bool,
    slippage_ticks: int = 1,
    tick_value_inr: float = 1.0
) -> Dict[str, float]:
    """
    Computes statutory and market transaction costs for MCX Commodity Derivatives trading.
    
    Components:
      - Exchange Turnover Fee: 0.0021% (₹2.10 per Lakh)
      - SEBI Turnover Fee: 0.0001% (₹10 per Crore)
      - GST: 18% on (Exchange + SEBI charges)
      - CTT (Commodities Transaction Tax): 0.01% on Sell leg only
      - Stamp Duty: 0.002% on Buy leg only
      - Slippage: tick_size * slippage_ticks
    """
    exchange_fee = turnover_inr * settings.EXCHANGE_TURNOVER_FEE_PCT
    sebi_fee = turnover_inr * settings.SEBI_TURNOVER_FEE_PCT
    gst = (exchange_fee + sebi_fee) * settings.GST_PCT

    ctt = (turnover_inr * settings.CTT_SELL_PCT) if not is_buy else 0.0
    stamp_duty = (turnover_inr * settings.STAMP_DUTY_BUY_PCT) if is_buy else 0.0

    slippage_cost = slippage_ticks * tick_value_inr

    total_statutory = exchange_fee + sebi_fee + gst + ctt + stamp_duty
    total_cost = total_statutory + slippage_cost
    cost_in_bps = (total_cost / turnover_inr * 10000.0) if turnover_inr > 0 else 0.0

    return {
        "turnover_inr": round(turnover_inr, 2),
        "exchange_fee": round(exchange_fee, 4),
        "sebi_fee": round(sebi_fee, 4),
        "gst": round(gst, 4),
        "ctt": round(ctt, 4),
        "stamp_duty": round(stamp_duty, 4),
        "slippage_cost": round(slippage_cost, 2),
        "total_statutory": round(total_statutory, 2),
        "total_cost": round(total_cost, 2),
        "cost_in_bps": round(cost_in_bps, 2)
    }


def calculate_pair_roundtrip_cost_bps(
    base_price_10g: float,
    quote_price_10g: float,
    base_symbol: str = "GOLDM",
    quote_symbol: str = "GOLDPETAL"
) -> Dict[str, float]:
    """
    Calculates round-trip trading friction (entry + exit across two legs) in basis points.
    Pair trade involves:
      - Leg 1 (e.g. Buy Base): Buy cost on entry, Sell cost on exit
      - Leg 2 (e.g. Sell Quote): Sell cost on entry, Buy cost on exit
    """
    # 1 lot normalized to ₹ per 10g
    # Base leg roundtrip: 1 Buy + 1 Sell
    base_buy = calculate_transaction_costs(base_price_10g, is_buy=True, slippage_ticks=1)
    base_sell = calculate_transaction_costs(base_price_10g, is_buy=False, slippage_ticks=1)
    base_rt_cost = base_buy["total_cost"] + base_sell["total_cost"]

    # Quote leg roundtrip: 1 Sell + 1 Buy (micro contracts like Petal typically have 2 ticks slippage)
    slippage_ticks_quote = 2 if quote_symbol in ["GOLDPETAL", "GOLDGUINEA"] else 1
    quote_sell = calculate_transaction_costs(quote_price_10g, is_buy=False, slippage_ticks=slippage_ticks_quote)
    quote_buy = calculate_transaction_costs(quote_price_10g, is_buy=True, slippage_ticks=slippage_ticks_quote)
    quote_rt_cost = quote_sell["total_cost"] + quote_buy["total_cost"]

    total_rt_cost = base_rt_cost + quote_rt_cost
    total_capital_involved = base_price_10g + quote_price_10g
    roundtrip_bps = (total_rt_cost / total_capital_involved) * 10000.0

    return {
        "base_rt_cost_inr": round(base_rt_cost, 2),
        "quote_rt_cost_inr": round(quote_rt_cost, 2),
        "total_rt_cost_inr": round(total_rt_cost, 2),
        "roundtrip_cost_bps": round(roundtrip_bps, 2)
    }
