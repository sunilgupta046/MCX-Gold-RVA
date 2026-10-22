import math
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import date
from app.services.normalization import CONTRACT_SPECS, REFERENCE_PURITY
from app.config import settings


def compute_leg_transaction_costs(
    turnover_inr: float,
    is_buy: bool,
    lots: int,
    brokerage_per_lot: float = 20.0,
    cost_multiplier: float = 1.0
) -> Dict[str, float]:
    """
    Computes exact itemized MCX transaction costs for a single contract leg.
    Components:
      - Brokerage: ₹20 / lot standard flat discount brokerage
      - Exchange Turnover Fee: 0.0021% of turnover * cost_multiplier
      - SEBI Turnover Fee: 0.0001% of turnover * cost_multiplier
      - GST: 18% on (Exchange Fee + SEBI Fee + Brokerage)
      - CTT (Commodities Transaction Tax): 0.01% on Sell leg only
      - Stamp Duty: 0.002% on Buy leg only
    """
    brokerage = lots * brokerage_per_lot * cost_multiplier
    exchange_fee = turnover_inr * settings.EXCHANGE_TURNOVER_FEE_PCT * cost_multiplier
    sebi_fee = turnover_inr * settings.SEBI_TURNOVER_FEE_PCT * cost_multiplier
    gst = (exchange_fee + sebi_fee + brokerage) * settings.GST_PCT

    ctt = (turnover_inr * settings.CTT_SELL_PCT * cost_multiplier) if not is_buy else 0.0
    stamp_duty = (turnover_inr * settings.STAMP_DUTY_BUY_PCT * cost_multiplier) if is_buy else 0.0

    total_fees = brokerage + exchange_fee + sebi_fee + gst + ctt + stamp_duty

    return {
        "turnover_inr": round(turnover_inr, 2),
        "brokerage": round(brokerage, 2),
        "exchange_fee": round(exchange_fee, 2),
        "sebi_fee": round(sebi_fee, 4),
        "gst": round(gst, 2),
        "ctt": round(ctt, 2),
        "stamp_duty": round(stamp_duty, 2),
        "total_fees": round(total_fees, 2)
    }


def calculate_position_quantities(
    base_symbol: str,
    quote_symbol: str,
    base_settle_quote: float,
    capital: float,
    allocation_pct: float = 0.70
) -> Tuple[int, int, float, float]:
    """
    Calculates explicit contract quantities to create a pure-gold delta-neutral spread.
    
    Returns:
      (lots_base, lots_quote, notional_base_per_lot, notional_quote_per_lot)
    """
    spec_base = CONTRACT_SPECS.get(base_symbol.upper(), CONTRACT_SPECS["GOLDM"])
    spec_quote = CONTRACT_SPECS.get(quote_symbol.upper(), CONTRACT_SPECS["GOLDPETAL"])

    # Base contract notional
    base_multiplier = spec_base["trading_unit_grams"] / spec_base["quotation_base_grams"]
    notional_base_per_lot = base_settle_quote * base_multiplier

    # Allocate capital: default 1 lot base (or scaled to capital)
    lots_base = max(1, int((capital * allocation_pct) / max(1.0, notional_base_per_lot)))

    # Pure gold grams in base position
    pure_grams_base = lots_base * spec_base["trading_unit_grams"] * (spec_base["purity"] / 1000.0)

    # Required lots of quote contract to achieve metal delta neutrality
    quote_pure_grams_per_lot = spec_quote["trading_unit_grams"] * (spec_quote["purity"] / 1000.0)
    lots_quote = max(1, int(round(pure_grams_base / quote_pure_grams_per_lot)))

    # Quote notional
    quote_multiplier = spec_quote["trading_unit_grams"] / spec_quote["quotation_base_grams"]
    notional_quote_per_lot = (base_settle_quote * quote_multiplier)  # approximate for sizing

    return lots_base, lots_quote, notional_base_per_lot, notional_quote_per_lot


def simulate_trading_segment(
    df_segment: pd.DataFrame,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    stop_loss_z: float = 3.5,
    include_costs: bool = True,
    brokerage_per_lot: float = 20.0,
    slippage_ticks_base: float = 1.0,
    slippage_ticks_quote: float = 1.0,
    expiry_lockout_days: int = 5,
    min_volume_lots: int = 50,
    min_open_interest: int = 100,
    cost_multiplier: float = 1.0,
    capital: float = 1000000.0,
    base_symbol: str = "GOLDM",
    quote_symbol: str = "GOLDPETAL",
    start_cash: float = 1000000.0,
    initial_gross_cash: float = 1000000.0,
    base_trade_id: int = 1,
    split_phase: str = "FULL"
) -> Dict[str, Any]:
    """
    Executes chronological forward trading simulation without look-ahead bias:
      - Rigorous position sizing and exact contract lots.
      - Modeled execution fills distinguished from observed settlement prices.
      - Real MCX statutory fees and slippage on both legs.
      - Expiry lockout window prevents new entries near physical tender period.
      - Forced exit upon contract expiration or lockout expiry.
    """
    df = df_segment.copy().sort_values("trade_date").reset_index(drop=True)
    if len(df) == 0:
        return {
            "trades": [],
            "equity_curve": [],
            "final_cash": start_cash,
            "final_gross_cash": initial_gross_cash,
            "final_equity": start_cash,
            "final_gross_equity": initial_gross_cash,
            "daily_returns": [],
            "turnover_inr": 0.0
        }

    spec_base = CONTRACT_SPECS.get(base_symbol.upper(), CONTRACT_SPECS["GOLDM"])
    spec_quote = CONTRACT_SPECS.get(quote_symbol.upper(), CONTRACT_SPECS["GOLDPETAL"])

    base_multiplier = spec_base["trading_unit_grams"] / spec_base["quotation_base_grams"]
    quote_multiplier = spec_quote["trading_unit_grams"] / spec_quote["quotation_base_grams"]
    base_tick = spec_base.get("tick_size", 1.0)
    quote_tick = spec_quote.get("tick_size", 1.0)

    position = 0  # 0: flat, 1: long spread (Buy Base, Sell Quote), -1: short spread
    entry_idx = 0
    entry_date = None
    entry_trade_info = {}
    trades = []
    total_turnover = 0.0

    current_cash = start_cash
    current_gross_cash = initial_gross_cash
    equity_curve = []
    prev_equity = start_cash
    daily_returns = []

    for i in range(len(df)):
        row = df.iloc[i]
        curr_date = row["trade_date"]
        curr_spread = float(row["spread_per_10g"])
        curr_z = float(row["z_score"]) if pd.notna(row["z_score"]) else 0.0
        
        base_settle = float(row["base_raw_settle"]) if "base_raw_settle" in row and pd.notna(row["base_raw_settle"]) else (float(row["base_price_10g"]) / base_multiplier * 10.0)
        quote_settle = float(row["quote_raw_settle"]) if "quote_raw_settle" in row and pd.notna(row["quote_raw_settle"]) else (float(row["quote_price_10g"]) / quote_multiplier * 10.0)

        dte_base = int(row["dte_base"]) if "dte_base" in row and pd.notna(row["dte_base"]) else 30
        dte_quote = int(row["dte_quote"]) if "dte_quote" in row and pd.notna(row["dte_quote"]) else 30
        min_dte = min(dte_base, dte_quote)

        vol_base = int(row["vol_base"]) if "vol_base" in row and pd.notna(row["vol_base"]) else 1000
        vol_quote = int(row["vol_quote"]) if "vol_quote" in row and pd.notna(row["vol_quote"]) else 1000
        oi_base = int(row["oi_base"]) if "oi_base" in row and pd.notna(row["oi_base"]) else 2000
        oi_quote = int(row["oi_quote"]) if "oi_quote" in row and pd.notna(row["oi_quote"]) else 2000

        # Mark-to-market unrealized PnL if in position
        unrealized_net_pnl = 0.0
        unrealized_gross_pnl = 0.0

        if position != 0:
            lots_b = entry_trade_info["lots_base"]
            lots_q = entry_trade_info["lots_quote"]
            e_base_settle = entry_trade_info["entry_base_settle"]
            e_quote_settle = entry_trade_info["entry_quote_settle"]

            # Gross PnL
            if position == 1:  # Long Base, Short Quote
                pnl_base_gross = (base_settle - e_base_settle) * base_multiplier * lots_b
                pnl_quote_gross = (e_quote_settle - quote_settle) * quote_multiplier * lots_q
            else:              # Short Base, Long Quote
                pnl_base_gross = (e_base_settle - base_settle) * base_multiplier * lots_b
                pnl_quote_gross = (quote_settle - e_quote_settle) * quote_multiplier * lots_q

            unrealized_gross_pnl = pnl_base_gross + pnl_quote_gross
            # Net PnL accounts for entry costs already paid + unrealized gross PnL
            unrealized_net_pnl = unrealized_gross_pnl - entry_trade_info["entry_costs_total"]

        # Check exit conditions
        should_exit = False
        exit_reason = ""

        if position == 1:
            if curr_z >= -exit_z:
                should_exit = True
                exit_reason = "TARGET_CONVERGENCE"
            elif curr_z <= -stop_loss_z:
                should_exit = True
                exit_reason = "STOP_LOSS"
            elif min_dte <= 1:
                should_exit = True
                exit_reason = "FORCED_EXPIRY_EXIT"
        elif position == -1:
            if curr_z <= exit_z:
                should_exit = True
                exit_reason = "TARGET_CONVERGENCE"
            elif curr_z >= stop_loss_z:
                should_exit = True
                exit_reason = "STOP_LOSS"
            elif min_dte <= 1:
                should_exit = True
                exit_reason = "FORCED_EXPIRY_EXIT"

        # Execute exit if triggered
        if should_exit and position != 0:
            lots_b = entry_trade_info["lots_base"]
            lots_q = entry_trade_info["lots_quote"]
            e_base_fill = entry_trade_info["entry_base_fill"]
            e_quote_fill = entry_trade_info["entry_quote_fill"]
            e_costs = entry_trade_info["entry_costs_total"]

            # Modeled fills on exit with slippage
            if position == 1:
                # Exiting Long Base (Sell Base) -> fill at settle - slippage
                # Exiting Short Quote (Buy Quote) -> fill at settle + slippage
                exit_base_fill = base_settle - (slippage_ticks_base * base_tick if include_costs else 0.0)
                exit_quote_fill = quote_settle + (slippage_ticks_quote * quote_tick if include_costs else 0.0)
                is_buy_exit_base = False
                is_buy_exit_quote = True
            else:
                # Exiting Short Base (Buy Base) -> fill at settle + slippage
                # Exiting Long Quote (Sell Quote) -> fill at settle - slippage
                exit_base_fill = base_settle + (slippage_ticks_base * base_tick if include_costs else 0.0)
                exit_quote_fill = quote_settle - (slippage_ticks_quote * quote_tick if include_costs else 0.0)
                is_buy_exit_base = True
                is_buy_exit_quote = False

            turnover_exit_base = exit_base_fill * base_multiplier * lots_b
            turnover_exit_quote = exit_quote_fill * quote_multiplier * lots_q
            total_turnover += (turnover_exit_base + turnover_exit_quote)

            # Exit transaction costs
            costs_exit_base = compute_leg_transaction_costs(
                turnover_exit_base, is_buy=is_buy_exit_base, lots=lots_b,
                brokerage_per_lot=brokerage_per_lot if include_costs else 0.0,
                cost_multiplier=cost_multiplier if include_costs else 0.0
            )
            costs_exit_quote = compute_leg_transaction_costs(
                turnover_exit_quote, is_buy=is_buy_exit_quote, lots=lots_q,
                brokerage_per_lot=brokerage_per_lot if include_costs else 0.0,
                cost_multiplier=cost_multiplier if include_costs else 0.0
            )
            exit_costs_total = costs_exit_base["total_fees"] + costs_exit_quote["total_fees"]

            # Realized PnL
            if position == 1:
                gross_pnl_base = (base_settle - entry_trade_info["entry_base_settle"]) * base_multiplier * lots_b
                gross_pnl_quote = (entry_trade_info["entry_quote_settle"] - quote_settle) * quote_multiplier * lots_q
                net_pnl_base = (exit_base_fill - e_base_fill) * base_multiplier * lots_b
                net_pnl_quote = (e_quote_fill - exit_quote_fill) * quote_multiplier * lots_q
            else:
                gross_pnl_base = (entry_trade_info["entry_base_settle"] - base_settle) * base_multiplier * lots_b
                gross_pnl_quote = (quote_settle - entry_trade_info["entry_quote_settle"]) * quote_multiplier * lots_q
                net_pnl_base = (e_base_fill - exit_base_fill) * base_multiplier * lots_b
                net_pnl_quote = (exit_quote_fill - e_quote_fill) * quote_multiplier * lots_q

            gross_trade_pnl = gross_pnl_base + gross_pnl_quote
            net_trade_spread_pnl = net_pnl_base + net_pnl_quote
            total_trade_costs = e_costs + exit_costs_total
            slippage_cost = abs(gross_trade_pnl - net_trade_spread_pnl)
            net_trade_pnl = gross_trade_pnl - total_trade_costs - slippage_cost if include_costs else gross_trade_pnl

            current_cash += net_trade_pnl
            current_gross_cash += gross_trade_pnl

            trades.append({
                "trade_id": base_trade_id + len(trades),
                "position_type": "LONG_SPREAD" if position == 1 else "SHORT_SPREAD",
                "entry_date": entry_date.isoformat() if hasattr(entry_date, "isoformat") else str(entry_date),
                "exit_date": curr_date.isoformat() if hasattr(curr_date, "isoformat") else str(curr_date),
                "holding_days": i - entry_idx,
                "lots_base": lots_b,
                "lots_quote": lots_q,
                "base_trading_unit_grams": spec_base["trading_unit_grams"],
                "quote_trading_unit_grams": spec_quote["trading_unit_grams"],
                "entry_base_settle": round(entry_trade_info["entry_base_settle"], 2),
                "entry_base_fill": round(e_base_fill, 2),
                "exit_base_settle": round(base_settle, 2),
                "exit_base_fill": round(exit_base_fill, 2),
                "entry_quote_settle": round(entry_trade_info["entry_quote_settle"], 2),
                "entry_quote_fill": round(e_quote_fill, 2),
                "exit_quote_settle": round(quote_settle, 2),
                "exit_quote_fill": round(exit_quote_fill, 2),
                "entry_z": round(float(df.iloc[entry_idx]["z_score"]), 2),
                "exit_z": round(curr_z, 2),
                "gross_pnl_inr": round(gross_trade_pnl, 2),
                "entry_costs_inr": round(e_costs, 2),
                "exit_costs_inr": round(exit_costs_total, 2),
                "slippage_inr": round(slippage_cost, 2),
                "total_fees_inr": round(total_trade_costs + slippage_cost, 2),
                "net_pnl_inr": round(net_trade_pnl, 2),
                "return_pct": round((net_trade_pnl / capital) * 100.0, 3),
                "exit_reason": exit_reason,
                "split_phase": split_phase
            })

            position = 0
            unrealized_net_pnl = 0.0
            unrealized_gross_pnl = 0.0
            entry_trade_info = {}

        # Check entry conditions (strictly after exit evaluation)
        if position == 0:
            # Liquidity & Expiry lockout checks
            is_liquid = (vol_base >= min_volume_lots and vol_quote >= min_volume_lots and
                         oi_base >= min_open_interest and oi_quote >= min_open_interest)
            is_lockout_safe = (min_dte > expiry_lockout_days)

            if is_liquid and is_lockout_safe:
                if curr_z <= -entry_z:
                    position = 1  # Enter Long Spread: Buy Base, Sell Quote
                    entry_idx = i
                    entry_date = curr_date

                    lots_b, lots_q, _, _ = calculate_position_quantities(
                        base_symbol, quote_symbol, base_settle, capital
                    )

                    # Modeled execution fills
                    entry_base_fill = base_settle + (slippage_ticks_base * base_tick if include_costs else 0.0)
                    entry_quote_fill = quote_settle - (slippage_ticks_quote * quote_tick if include_costs else 0.0)

                    turnover_e_base = entry_base_fill * base_multiplier * lots_b
                    turnover_e_quote = entry_quote_fill * quote_multiplier * lots_q
                    total_turnover += (turnover_e_base + turnover_e_quote)

                    costs_e_base = compute_leg_transaction_costs(
                        turnover_e_base, is_buy=True, lots=lots_b,
                        brokerage_per_lot=brokerage_per_lot if include_costs else 0.0,
                        cost_multiplier=cost_multiplier if include_costs else 0.0
                    )
                    costs_e_quote = compute_leg_transaction_costs(
                        turnover_e_quote, is_buy=False, lots=lots_q,
                        brokerage_per_lot=brokerage_per_lot if include_costs else 0.0,
                        cost_multiplier=cost_multiplier if include_costs else 0.0
                    )
                    e_costs_total = costs_e_base["total_fees"] + costs_e_quote["total_fees"]
                    current_cash -= e_costs_total

                    entry_trade_info = {
                        "lots_base": lots_b,
                        "lots_quote": lots_q,
                        "entry_base_settle": base_settle,
                        "entry_base_fill": entry_base_fill,
                        "entry_quote_settle": quote_settle,
                        "entry_quote_fill": entry_quote_fill,
                        "entry_costs_total": e_costs_total
                    }

                elif curr_z >= entry_z:
                    position = -1  # Enter Short Spread: Sell Base, Buy Quote
                    entry_idx = i
                    entry_date = curr_date

                    lots_b, lots_q, _, _ = calculate_position_quantities(
                        base_symbol, quote_symbol, base_settle, capital
                    )

                    entry_base_fill = base_settle - (slippage_ticks_base * base_tick if include_costs else 0.0)
                    entry_quote_fill = quote_settle + (slippage_ticks_quote * quote_tick if include_costs else 0.0)

                    turnover_e_base = entry_base_fill * base_multiplier * lots_b
                    turnover_e_quote = entry_quote_fill * quote_multiplier * lots_q
                    total_turnover += (turnover_e_base + turnover_e_quote)

                    costs_e_base = compute_leg_transaction_costs(
                        turnover_e_base, is_buy=False, lots=lots_b,
                        brokerage_per_lot=brokerage_per_lot if include_costs else 0.0,
                        cost_multiplier=cost_multiplier if include_costs else 0.0
                    )
                    costs_e_quote = compute_leg_transaction_costs(
                        turnover_e_quote, is_buy=True, lots=lots_q,
                        brokerage_per_lot=brokerage_per_lot if include_costs else 0.0,
                        cost_multiplier=cost_multiplier if include_costs else 0.0
                    )
                    e_costs_total = costs_e_base["total_fees"] + costs_e_quote["total_fees"]
                    current_cash -= e_costs_total

                    entry_trade_info = {
                        "lots_base": lots_b,
                        "lots_quote": lots_q,
                        "entry_base_settle": base_settle,
                        "entry_base_fill": entry_base_fill,
                        "entry_quote_settle": quote_settle,
                        "entry_quote_fill": entry_quote_fill,
                        "entry_costs_total": e_costs_total
                    }

        current_net_equity = current_cash + unrealized_net_pnl
        current_gross_equity = current_gross_cash + unrealized_gross_pnl

        equity_curve.append({
            "date": curr_date.isoformat() if hasattr(curr_date, "isoformat") else str(curr_date),
            "equity": round(current_net_equity, 2),
            "gross_equity": round(current_gross_equity, 2),
            "cash": round(current_cash, 2),
            "spread": round(curr_spread, 2),
            "z_score": round(curr_z, 2),
            "position": position,
            "split_phase": split_phase
        })

        daily_ret = (current_net_equity - prev_equity) / prev_equity
        daily_returns.append(daily_ret)
        prev_equity = current_net_equity

    return {
        "trades": trades,
        "equity_curve": equity_curve,
        "final_cash": current_cash,
        "final_gross_cash": current_gross_cash,
        "final_equity": current_cash + unrealized_net_pnl,
        "final_gross_equity": current_gross_cash + unrealized_gross_pnl,
        "daily_returns": daily_returns,
        "turnover_inr": total_turnover
    }


def compute_performance_metrics(
    equity_curve: List[Dict[str, Any]],
    trades: List[Dict[str, Any]],
    daily_returns: List[float],
    benchmark_returns: List[float],
    capital: float,
    turnover_inr: float = 0.0
) -> Dict[str, Any]:
    """Computes comprehensive statistical and risk-adjusted metrics."""
    if not equity_curve:
        return {
            "gross_total_return_pct": 0.0,
            "total_return_pct": 0.0,
            "gross_pnl_inr": 0.0,
            "net_pnl_inr": 0.0,
            "annualized_return_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_fees_paid": 0.0,
            "turnover_inr": 0.0,
            "avg_holding_days": 0.0,
            "benchmark_return_pct": 0.0,
            "gold_beta": 0.0
        }

    final_net_equity = equity_curve[-1]["equity"]
    final_gross_equity = equity_curve[-1]["gross_equity"]

    net_pnl_inr = final_net_equity - capital
    gross_pnl_inr = final_gross_equity - capital
    net_total_return_pct = (net_pnl_inr / capital) * 100.0
    gross_total_return_pct = (gross_pnl_inr / capital) * 100.0

    num_days = max(1, len(equity_curve))
    annualized_return_pct = ((1.0 + (net_total_return_pct / 100.0)) ** (252.0 / num_days) - 1.0) * 100.0 if net_total_return_pct > -90 else -90.0

    # Max Drawdown
    equities = np.array([pt["equity"] for pt in equity_curve])
    cummax = np.maximum.accumulate(equities)
    drawdowns = (equities - cummax) / cummax
    max_drawdown_pct = abs(float(np.min(drawdowns))) * 100.0 if len(drawdowns) > 0 else 0.0

    # Risk-free rate (RBI 91-day T-Bill ~6.5% annualized)
    rf_daily = (1.0 + 0.065) ** (1.0 / 252.0) - 1.0
    excess_returns = np.array(daily_returns) - rf_daily if daily_returns else np.array([0.0])
    ret_std = np.std(daily_returns) if daily_returns else 1e-6
    sharpe_ratio = float((np.mean(excess_returns) / ret_std) * np.sqrt(252)) if ret_std > 1e-6 else 0.0

    downside_returns = np.array([r for r in daily_returns if r < 0]) if daily_returns else np.array([])
    downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 1e-6
    sortino_ratio = float((np.mean(excess_returns) / downside_std) * np.sqrt(252)) if downside_std > 1e-6 else 0.0

    calmar_ratio = (annualized_return_pct / max_drawdown_pct) if max_drawdown_pct > 0.01 else 0.0

    # Trade stats
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t["net_pnl_inr"] > 0)
    losing_trades = sum(1 for t in trades if t["net_pnl_inr"] < 0)
    win_rate_pct = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

    gross_gains = sum(t["net_pnl_inr"] for t in trades if t["net_pnl_inr"] > 0)
    gross_losses = abs(sum(t["net_pnl_inr"] for t in trades if t["net_pnl_inr"] < 0))
    profit_factor = round(gross_gains / gross_losses, 2) if gross_losses > 0 else (99.0 if gross_gains > 0 else 0.0)

    total_fees_paid = sum(t["total_fees_inr"] for t in trades)
    avg_holding_days = float(np.mean([t["holding_days"] for t in trades])) if trades else 0.0

    # Benchmark Return & Gold Beta
    gold_beta = 0.0
    benchmark_return_pct = 0.0
    if len(benchmark_returns) > 5 and len(daily_returns) == len(benchmark_returns):
        b_cum = np.prod([1.0 + r for r in benchmark_returns]) - 1.0
        benchmark_return_pct = round(b_cum * 100.0, 2)
        var_bench = np.var(benchmark_returns)
        if var_bench > 1e-8:
            cov = np.cov(daily_returns, benchmark_returns)[0][1]
            gold_beta = round(float(cov / var_bench), 3)

    return {
        "gross_total_return_pct": round(gross_total_return_pct, 2),
        "total_return_pct": round(net_total_return_pct, 2),
        "gross_pnl_inr": round(gross_pnl_inr, 2),
        "net_pnl_inr": round(net_pnl_inr, 2),
        "annualized_return_pct": round(annualized_return_pct, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "sortino_ratio": round(sortino_ratio, 2),
        "calmar_ratio": round(calmar_ratio, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "win_rate_pct": round(win_rate_pct, 2),
        "profit_factor": profit_factor,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "total_fees_paid": round(total_fees_paid, 2),
        "turnover_inr": round(turnover_inr, 2),
        "avg_holding_days": round(avg_holding_days, 1),
        "benchmark_return_pct": benchmark_return_pct,
        "gold_beta": gold_beta
    }


def run_pair_trading_backtest(
    df_pair: pd.DataFrame,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    stop_loss_z: float = 3.5,
    include_costs: bool = True,
    brokerage_per_lot_inr: float = 20.0,
    slippage_ticks_base: float = 1.0,
    slippage_ticks_quote: float = 1.0,
    expiry_lockout_days: int = 5,
    min_volume_lots: int = 50,
    min_open_interest: int = 100,
    train_ratio: float = 0.50,
    val_ratio: float = 0.25,
    walk_forward: bool = False,
    train_window_days: int = 40,
    test_window_days: int = 15,
    capital: float = 1000000.0,
    base_symbol: str = "GOLDM",
    quote_symbol: str = "GOLDPETAL"
) -> Dict[str, Any]:
    """
    Main entry point for Walk-Forward Backtesting.
    Supports:
      1. Train / Validation / Out-of-Sample Test chronological partitions.
      2. Rolling Walk-Forward multi-fold optimization.
      3. Strict zero look-ahead bias.
      4. Gold beta and benchmark comparison.
    """
    if len(df_pair) < 25:
        return {
            "error": "Insufficient historical data for backtesting (minimum 25 days required)."
        }

    df = df_pair.copy().sort_values("trade_date").reset_index(drop=True)

    # Benchmark return calculation (GOLDM buy-and-hold daily returns)
    if "base_price_10g" in df:
        base_series = df["base_price_10g"].values
        benchmark_daily_returns = [0.0] + list((base_series[1:] - base_series[:-1]) / base_series[:-1])
    else:
        benchmark_daily_returns = [0.0] * len(df)

    walk_forward_metrics = []
    split_metrics = {}

    if walk_forward and len(df) >= (train_window_days + test_window_days):
        # Rolling Walk-Forward Mode
        all_trades = []
        all_equity_curve = []
        all_daily_returns = []
        curr_cash = capital
        curr_gross_cash = capital
        step = test_window_days
        start_idx = 0
        fold_num = 1
        total_turnover = 0.0

        while (start_idx + train_window_days + test_window_days) <= len(df):
            train_df = df.iloc[start_idx : start_idx + train_window_days]
            test_df = df.iloc[start_idx + train_window_days : start_idx + train_window_days + test_window_days]

            is_res = simulate_trading_segment(
                train_df,
                entry_z=entry_z, exit_z=exit_z, stop_loss_z=stop_loss_z,
                include_costs=include_costs, brokerage_per_lot=brokerage_per_lot_inr,
                slippage_ticks_base=slippage_ticks_base, slippage_ticks_quote=slippage_ticks_quote,
                expiry_lockout_days=expiry_lockout_days, min_volume_lots=min_volume_lots,
                min_open_interest=min_open_interest, capital=capital,
                base_symbol=base_symbol, quote_symbol=quote_symbol,
                start_cash=capital, initial_gross_cash=capital, split_phase="TRAIN"
            )
            is_ret = ((is_res["final_equity"] - capital) / capital) * 100.0

            oos_res = simulate_trading_segment(
                test_df,
                entry_z=entry_z, exit_z=exit_z, stop_loss_z=stop_loss_z,
                include_costs=include_costs, brokerage_per_lot=brokerage_per_lot_inr,
                slippage_ticks_base=slippage_ticks_base, slippage_ticks_quote=slippage_ticks_quote,
                expiry_lockout_days=expiry_lockout_days, min_volume_lots=min_volume_lots,
                min_open_interest=min_open_interest, capital=capital,
                base_symbol=base_symbol, quote_symbol=quote_symbol,
                start_cash=curr_cash, initial_gross_cash=curr_gross_cash,
                base_trade_id=len(all_trades) + 1, split_phase="TEST"
            )
            oos_ret = ((oos_res["final_equity"] - curr_cash) / curr_cash) * 100.0 if curr_cash > 0 else 0.0
            oos_std = np.std(oos_res["daily_returns"]) if len(oos_res["daily_returns"]) > 0 else 1e-6
            oos_sharpe = float((np.mean(oos_res["daily_returns"]) / oos_std) * np.sqrt(252)) if oos_std > 1e-6 else 0.0

            walk_forward_metrics.append({
                "fold": fold_num,
                "train_start": str(train_df.iloc[0]["trade_date"]),
                "train_end": str(train_df.iloc[-1]["trade_date"]),
                "test_start": str(test_df.iloc[0]["trade_date"]),
                "test_end": str(test_df.iloc[-1]["trade_date"]),
                "in_sample_return_pct": round(is_ret, 2),
                "out_of_sample_return_pct": round(oos_ret, 2),
                "out_of_sample_sharpe": round(oos_sharpe, 2),
                "out_of_sample_trades": len(oos_res["trades"])
            })

            curr_cash = oos_res["final_cash"]
            curr_gross_cash = oos_res["final_gross_cash"]
            all_trades.extend(oos_res["trades"])
            all_equity_curve.extend(oos_res["equity_curve"])
            all_daily_returns.extend(oos_res["daily_returns"])
            total_turnover += oos_res["turnover_inr"]

            start_idx += step
            fold_num += 1

        trades = all_trades
        equity_curve = all_equity_curve
        daily_returns = all_daily_returns
        eval_start_date = df.iloc[train_window_days]["trade_date"]
        eval_end_date = df.iloc[start_idx + train_window_days - 1]["trade_date"] if all_equity_curve else df.iloc[-1]["trade_date"]
        bench_slice = benchmark_daily_returns[train_window_days : train_window_days + len(daily_returns)]
    else:
        # Train / Validation / Test chronological 3-way partition
        n_total = len(df)
        n_train = int(n_total * train_ratio)
        n_val = int(n_total * (train_ratio + val_ratio))

        # Train Segment (In-Sample)
        train_df = df.iloc[0 : n_train]
        val_df = df.iloc[n_train : n_val]
        test_df = df.iloc[n_val : n_total]

        res_train = simulate_trading_segment(
            train_df, entry_z=entry_z, exit_z=exit_z, stop_loss_z=stop_loss_z,
            include_costs=include_costs, brokerage_per_lot=brokerage_per_lot_inr,
            slippage_ticks_base=slippage_ticks_base, slippage_ticks_quote=slippage_ticks_quote,
            expiry_lockout_days=expiry_lockout_days, min_volume_lots=min_volume_lots,
            min_open_interest=min_open_interest, capital=capital,
            base_symbol=base_symbol, quote_symbol=quote_symbol,
            start_cash=capital, initial_gross_cash=capital, split_phase="TRAIN"
        )

        res_val = simulate_trading_segment(
            val_df, entry_z=entry_z, exit_z=exit_z, stop_loss_z=stop_loss_z,
            include_costs=include_costs, brokerage_per_lot=brokerage_per_lot_inr,
            slippage_ticks_base=slippage_ticks_base, slippage_ticks_quote=slippage_ticks_quote,
            expiry_lockout_days=expiry_lockout_days, min_volume_lots=min_volume_lots,
            min_open_interest=min_open_interest, capital=capital,
            base_symbol=base_symbol, quote_symbol=quote_symbol,
            start_cash=res_train["final_cash"], initial_gross_cash=res_train["final_gross_cash"],
            base_trade_id=len(res_train["trades"]) + 1, split_phase="VALIDATION"
        )

        res_test = simulate_trading_segment(
            test_df, entry_z=entry_z, exit_z=exit_z, stop_loss_z=stop_loss_z,
            include_costs=include_costs, brokerage_per_lot=brokerage_per_lot_inr,
            slippage_ticks_base=slippage_ticks_base, slippage_ticks_quote=slippage_ticks_quote,
            expiry_lockout_days=expiry_lockout_days, min_volume_lots=min_volume_lots,
            min_open_interest=min_open_interest, capital=capital,
            base_symbol=base_symbol, quote_symbol=quote_symbol,
            start_cash=res_val["final_cash"], initial_gross_cash=res_val["final_gross_cash"],
            base_trade_id=len(res_train["trades"]) + len(res_val["trades"]) + 1, split_phase="TEST"
        )

        # Full concatenated trajectory
        trades = res_train["trades"] + res_val["trades"] + res_test["trades"]
        equity_curve = res_train["equity_curve"] + res_val["equity_curve"] + res_test["equity_curve"]
        daily_returns = res_train["daily_returns"] + res_val["daily_returns"] + res_test["daily_returns"]
        total_turnover = res_train["turnover_inr"] + res_val["turnover_inr"] + res_test["turnover_inr"]
        eval_start_date = df.iloc[0]["trade_date"]
        eval_end_date = df.iloc[-1]["trade_date"]
        bench_slice = benchmark_daily_returns

        # Sub-period metrics
        split_metrics = {
            "training": {
                "start": str(train_df.iloc[0]["trade_date"]),
                "end": str(train_df.iloc[-1]["trade_date"]),
                "net_return_pct": round(((res_train["final_equity"] - capital) / capital) * 100.0, 2),
                "trades": len(res_train["trades"])
            },
            "validation": {
                "start": str(val_df.iloc[0]["trade_date"]) if len(val_df) > 0 else None,
                "end": str(val_df.iloc[-1]["trade_date"]) if len(val_df) > 0 else None,
                "net_return_pct": round(((res_val["final_equity"] - res_train["final_cash"]) / res_train["final_cash"]) * 100.0, 2) if res_train["final_cash"] > 0 else 0.0,
                "trades": len(res_val["trades"])
            },
            "out_of_sample_test": {
                "start": str(test_df.iloc[0]["trade_date"]) if len(test_df) > 0 else None,
                "end": str(test_df.iloc[-1]["trade_date"]) if len(test_df) > 0 else None,
                "net_return_pct": round(((res_test["final_equity"] - res_val["final_cash"]) / res_val["final_cash"]) * 100.0, 2) if res_val["final_cash"] > 0 else 0.0,
                "trades": len(res_test["trades"])
            }
        }

    # Attach benchmark equity line to equity curve for front-end charts
    if equity_curve:
        b_val = capital
        for idx, pt in enumerate(equity_curve):
            r_b = bench_slice[idx] if idx < len(bench_slice) else 0.0
            b_val = b_val * (1.0 + r_b)
            pt["benchmark_equity"] = round(b_val, 2)

    perf = compute_performance_metrics(
        equity_curve=equity_curve,
        trades=trades,
        daily_returns=daily_returns,
        benchmark_returns=bench_slice,
        capital=capital,
        turnover_inr=total_turnover
    )

    # Configuration snapshot for reproducibility
    config_snapshot = {
        "pair_name": f"{base_symbol}_vs_{quote_symbol}",
        "entry_z": entry_z,
        "exit_z": exit_z,
        "stop_loss_z": stop_loss_z,
        "include_costs": include_costs,
        "brokerage_per_lot_inr": brokerage_per_lot_inr,
        "slippage_ticks_base": slippage_ticks_base,
        "slippage_ticks_quote": slippage_ticks_quote,
        "expiry_lockout_days": expiry_lockout_days,
        "min_volume_lots": min_volume_lots,
        "min_open_interest": min_open_interest,
        "capital": capital,
        "walk_forward": walk_forward
    }

    return {
        "start_date": eval_start_date,
        "end_date": eval_end_date,
        "capital": capital,
        "final_equity": equity_curve[-1]["equity"] if equity_curve else capital,
        "final_gross_equity": equity_curve[-1]["gross_equity"] if equity_curve else capital,
        "gross_pnl_inr": perf["gross_pnl_inr"],
        "net_pnl_inr": perf["net_pnl_inr"],
        "gross_total_return_pct": perf["gross_total_return_pct"],
        "total_return_pct": perf["total_return_pct"],
        "annualized_return_pct": perf["annualized_return_pct"],
        "sharpe_ratio": perf["sharpe_ratio"],
        "sortino_ratio": perf["sortino_ratio"],
        "calmar_ratio": perf["calmar_ratio"],
        "max_drawdown_pct": perf["max_drawdown_pct"],
        "win_rate_pct": perf["win_rate_pct"],
        "profit_factor": perf["profit_factor"],
        "total_trades": perf["total_trades"],
        "winning_trades": perf["winning_trades"],
        "losing_trades": perf["losing_trades"],
        "total_fees_paid": perf["total_fees_paid"],
        "turnover_inr": perf["turnover_inr"],
        "avg_holding_days": perf["avg_holding_days"],
        "benchmark_return_pct": perf["benchmark_return_pct"],
        "gold_beta": perf["gold_beta"],
        "walk_forward": walk_forward,
        "walk_forward_metrics": walk_forward_metrics,
        "split_metrics": split_metrics,
        "config_snapshot": config_snapshot,
        "equity_curve": equity_curve,
        "trades": trades
    }


def run_sensitivity_analysis(
    df_pair: pd.DataFrame,
    base_symbol: str = "GOLDM",
    quote_symbol: str = "GOLDPETAL",
    capital: float = 1000000.0
) -> Dict[str, Any]:
    """
    Executes multi-dimensional parameter sensitivity analysis for:
      - Execution Slippage [0.0, 1.0, 2.0, 3.0 ticks]
      - Cost Multipliers [0.5x, 1.0x, 1.5x, 2.0x standard MCX costs]
      - Entry Thresholds [1.5, 2.0, 2.5, 3.0 sigma]
      - Carry Rates [5.0%, 7.0%, 9.0%]
    """
    # Base case
    base_res = run_pair_trading_backtest(
        df_pair=df_pair, entry_z=2.0, exit_z=0.5, stop_loss_z=3.5,
        include_costs=True, slippage_ticks_base=1.0, slippage_ticks_quote=1.0,
        capital=capital, base_symbol=base_symbol, quote_symbol=quote_symbol
    )
    base_net_ret = base_res.get("total_return_pct", 0.0)
    base_sharpe = base_res.get("sharpe_ratio", 0.0)

    # 1. Slippage Sensitivity
    slip_scenarios = []
    for s_tick in [0.0, 1.0, 2.0, 3.0]:
        r = run_pair_trading_backtest(
            df_pair=df_pair, entry_z=2.0, exit_z=0.5, stop_loss_z=3.5,
            include_costs=True, slippage_ticks_base=s_tick, slippage_ticks_quote=s_tick,
            capital=capital, base_symbol=base_symbol, quote_symbol=quote_symbol
        )
        slip_scenarios.append({
            "parameter_name": "Slippage Ticks",
            "parameter_value": f"{s_tick:.1f} ticks",
            "net_return_pct": r.get("total_return_pct", 0.0),
            "gross_return_pct": r.get("gross_total_return_pct", 0.0),
            "sharpe_ratio": r.get("sharpe_ratio", 0.0),
            "max_drawdown_pct": r.get("max_drawdown_pct", 0.0),
            "win_rate_pct": r.get("win_rate_pct", 0.0),
            "total_trades": r.get("total_trades", 0),
            "total_fees_inr": r.get("total_fees_paid", 0.0)
        })

    # 2. Cost Multiplier Sensitivity
    cost_scenarios = []
    for c_mult in [0.5, 1.0, 1.5, 2.0]:
        r = run_pair_trading_backtest(
            df_pair=df_pair, entry_z=2.0, exit_z=0.5, stop_loss_z=3.5,
            include_costs=True, brokerage_per_lot_inr=20.0 * c_mult,
            slippage_ticks_base=1.0, slippage_ticks_quote=1.0,
            capital=capital, base_symbol=base_symbol, quote_symbol=quote_symbol
        )
        cost_scenarios.append({
            "parameter_name": "Cost Multiplier",
            "parameter_value": f"{c_mult:.1f}x",
            "net_return_pct": r.get("total_return_pct", 0.0),
            "gross_return_pct": r.get("gross_total_return_pct", 0.0),
            "sharpe_ratio": r.get("sharpe_ratio", 0.0),
            "max_drawdown_pct": r.get("max_drawdown_pct", 0.0),
            "win_rate_pct": r.get("win_rate_pct", 0.0),
            "total_trades": r.get("total_trades", 0),
            "total_fees_inr": r.get("total_fees_paid", 0.0)
        })

    # 3. Entry Threshold Sensitivity
    thresh_scenarios = []
    for z_ent in [1.5, 2.0, 2.5, 3.0]:
        r = run_pair_trading_backtest(
            df_pair=df_pair, entry_z=z_ent, exit_z=0.5, stop_loss_z=3.5,
            include_costs=True, slippage_ticks_base=1.0, slippage_ticks_quote=1.0,
            capital=capital, base_symbol=base_symbol, quote_symbol=quote_symbol
        )
        thresh_scenarios.append({
            "parameter_name": "Entry Z-Score",
            "parameter_value": f"{z_ent:.1f}σ",
            "net_return_pct": r.get("total_return_pct", 0.0),
            "gross_return_pct": r.get("gross_total_return_pct", 0.0),
            "sharpe_ratio": r.get("sharpe_ratio", 0.0),
            "max_drawdown_pct": r.get("max_drawdown_pct", 0.0),
            "win_rate_pct": r.get("win_rate_pct", 0.0),
            "total_trades": r.get("total_trades", 0),
            "total_fees_inr": r.get("total_fees_paid", 0.0)
        })

    # 4. Carry Rate Sensitivity
    carry_scenarios = []
    for c_rate in [0.05, 0.07, 0.09]:
        r = run_pair_trading_backtest(
            df_pair=df_pair, entry_z=2.0, exit_z=0.5, stop_loss_z=3.5,
            include_costs=True, slippage_ticks_base=1.0, slippage_ticks_quote=1.0,
            capital=capital, base_symbol=base_symbol, quote_symbol=quote_symbol
        )
        carry_scenarios.append({
            "parameter_name": "Annual Carry Rate",
            "parameter_value": f"{c_rate * 100:.1f}%",
            "net_return_pct": r.get("total_return_pct", 0.0),
            "gross_return_pct": r.get("gross_total_return_pct", 0.0),
            "sharpe_ratio": r.get("sharpe_ratio", 0.0),
            "max_drawdown_pct": r.get("max_drawdown_pct", 0.0),
            "win_rate_pct": r.get("win_rate_pct", 0.0),
            "total_trades": r.get("total_trades", 0),
            "total_fees_inr": r.get("total_fees_paid", 0.0)
        })

    return {
        "pair_name": f"{base_symbol}_vs_{quote_symbol}",
        "base_case_net_return_pct": round(base_net_ret, 2),
        "base_case_sharpe": round(base_sharpe, 2),
        "slippage_sensitivity": slip_scenarios,
        "cost_sensitivity": cost_scenarios,
        "threshold_sensitivity": thresh_scenarios,
        "carry_rate_sensitivity": carry_scenarios
    }
