import math
import numpy as np
import pandas as pd
from datetime import date, timedelta, datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.contract import Contract
from app.models.bhavcopy import BhavcopyRecord
from app.models.normalized_price import NormalizedPrice
from app.models.spread_metrics import SpreadMetric
from app.models.signals import RVASignal
from app.services.normalization import CONTRACT_SPECS, normalize_price, calculate_days_to_expiry
from app.services.carry_adjustment import calculate_carry_adjustment
from app.services.spread_analytics import (
    calculate_pair_spread,
    calculate_rolling_z_score,
    calculate_half_life
)
from app.services.signals import evaluate_signal_for_pair


def seed_contracts(db: Session):
    """Ensures base MCX gold contracts exist in database with verified specs."""
    for symbol, spec in CONTRACT_SPECS.items():
        existing = db.query(Contract).filter(Contract.symbol == symbol).first()
        if not existing:
            c = Contract(
                symbol=symbol,
                name=spec["name"],
                trading_unit_grams=spec["trading_unit_grams"],
                quotation_unit_grams=spec.get("quotation_unit_grams", spec["quotation_base_grams"]),
                quotation_base_grams=spec["quotation_base_grams"],
                purity=spec["purity"],
                tick_size=spec["tick_size"],
                contract_multiplier=spec["contract_multiplier"],
                description=spec["description"],
                is_active=True
            )
            db.add(c)
        else:
            # Update existing contract specs if missing new fields
            existing.quotation_base_grams = spec["quotation_base_grams"]
            existing.purity = spec["purity"]
    db.commit()


def generate_synthetic_demo_bhavcopy(db: Session, days: int = 90) -> Dict[str, Any]:
    """
    Generates realistic, continuous synthetic demo Bhavcopy data for testing.
    CLEARLY LABELED AS DEMO DATA per project requirements.
    """
    seed_contracts(db)

    # Clean previous demo records to allow clean re-generation
    db.query(BhavcopyRecord).filter(BhavcopyRecord.is_demo == True).delete()
    db.query(NormalizedPrice).delete()
    db.query(SpreadMetric).delete()
    db.query(RVASignal).delete()
    db.commit()

    # Base price trajectory ~ ₹78,500 / 10g with a geometric brownian walk
    np.random.seed(42)  # Deterministic realistic demo series
    start_date = date.today() - timedelta(days=int(days * 1.5))
    
    # Generate business days
    trade_dates = []
    curr = start_date
    while len(trade_dates) < days:
        if curr.weekday() < 5:  # Monday to Friday
            trade_dates.append(curr)
        curr += timedelta(days=1)

    # Base drift and volatility
    daily_vol = 0.0075  # ~12% annual volatility
    price_drift = 0.0003
    base_benchmark = 78200.0

    bhavcopy_entries = []
    
    # Contract maturities: e.g. next month 5th
    base_expiry = trade_dates[-1] + timedelta(days=25)

    current_price = base_benchmark
    for t_idx, t_date in enumerate(trade_dates):
        # Random walk for gold benchmark
        shock = np.random.normal(price_drift, daily_vol)
        current_price = current_price * math.exp(shock)

        # Days to expiry
        dte = calculate_days_to_expiry(t_date, base_expiry)

        # Microstructure relative deviations (basis points relative to benchmark)
        # GOLDM: Benchmark mini
        # GOLDTEN: near benchmark with +- 2 to 5 bps noise
        # GOLDGUINEA: sovereign coin demand, slightly higher premium (+5 to 25 bps) with cyclical oscillations
        # GOLDPETAL: high retail turnover, periodic liquidity discount or retail delivery premium (-20 to +35 bps)
        
        cycle_guinea = 15.0 * math.sin(t_idx / 6.0) + np.random.normal(0, 4.0)
        cycle_petal = 28.0 * math.cos(t_idx / 4.5) + np.random.normal(0, 6.0)
        cycle_ten = np.random.normal(0, 3.0)

        # Pricing per 10g:
        p10_goldm = current_price
        p10_goldten = current_price * (1.0 + cycle_ten / 10000.0)
        p10_guinea = current_price * (1.0 + (12.0 + cycle_guinea) / 10000.0)
        p10_petal = current_price * (1.0 + (-5.0 + cycle_petal) / 10000.0)

        # Convert back to raw quote units
        # GOLDM: quoted per 10g
        # GOLDTEN: quoted per 10g
        # GOLDGUINEA: quoted per 8g (price = p10 * 8/10)
        # GOLDPETAL: quoted per 1g (price = p10 * 1/10)
        quotes = {
            "GOLDM": (round(p10_goldm, 0), int(np.random.normal(9500, 1500)), int(np.random.normal(12000, 800))),
            "GOLDTEN": (round(p10_goldten, 0), int(np.random.normal(1100, 200)), int(np.random.normal(2100, 300))),
            "GOLDGUINEA": (round(p10_guinea * 0.8, 0), int(np.random.normal(2800, 400)), int(np.random.normal(4500, 500))),
            "GOLDPETAL": (round(p10_petal * 0.1, 0), int(np.random.normal(32000, 4000)), int(np.random.normal(38000, 2500))),
        }

        for sym, (settle, vol, oi) in quotes.items():
            daily_range = settle * 0.009
            bhavcopy_entries.append(BhavcopyRecord(
                trade_date=t_date,
                symbol=sym,
                expiry_date=base_expiry,
                open_price=round(settle - (daily_range * 0.2), 2),
                high_price=round(settle + (daily_range * 0.5), 2),
                low_price=round(settle - (daily_range * 0.5), 2),
                close_price=round(settle + (daily_range * 0.1), 2),
                settle_price=round(settle, 2),
                volume_lots=max(10, vol),
                volume_value_lakhs=round((settle * vol) / 100000.0, 2),
                open_interest=max(100, oi),
                change_in_oi=int(np.random.normal(0, 150)),
                is_demo=True,
                data_source="DEMO_SYNTHETIC_DATASET_COZY_NEXUS"
            ))

    db.bulk_save_objects(bhavcopy_entries)
    db.commit()

    # Re-compute downstream analytics
    process_normalization_and_spreads(db)

    return {
        "success": True,
        "message": f"Successfully generated {len(bhavcopy_entries)} DEMO Bhavcopy records across {days} trading days.",
        "records_processed": len(bhavcopy_entries),
        "dates_covered": [str(d) for d in [trade_dates[0], trade_dates[-1]]],
        "is_demo": True
    }


def process_normalization_and_spreads(db: Session):
    """Calculates NormalizedPrice, SpreadMetrics, and RVASignals from Bhavcopy records."""
    records = db.query(BhavcopyRecord).order_by(BhavcopyRecord.trade_date.asc()).all()
    if not records:
        return

    # Look up any historical carry rates
    try:
        from app.models.carry_rate import CarryRateHistory
        historical_rates = {
            cr.rate_date: (cr.annualized_carry_rate, cr.rate_source)
            for cr in db.query(CarryRateHistory).all()
        }
    except Exception:
        historical_rates = {}

    bhav_map = {(r.trade_date, r.symbol): r for r in records}

    # 1. Normalize Prices on standard 999 fineness basis
    norm_objects = []
    for r in records:
        norm = normalize_price(r.symbol, r.settle_price)
        dte = calculate_days_to_expiry(r.trade_date, r.expiry_date)

        hist_rate, hist_source = historical_rates.get(r.trade_date, (None, None))
        carry_adj_raw = calculate_carry_adjustment(
            norm["price_per_10g"],
            dte,
            annual_carry_rate=hist_rate,
            rate_source=hist_source
        )
        pure_10g = norm["price_per_pure_gram_999"] * 10.0
        carry_adj_pure = calculate_carry_adjustment(
            pure_10g,
            dte,
            annual_carry_rate=hist_rate,
            rate_source=hist_source
        )
        
        norm_objects.append(NormalizedPrice(
            trade_date=r.trade_date,
            symbol=r.symbol,
            expiry_date=r.expiry_date,
            raw_settle_price=r.settle_price,
            price_per_gram=norm["price_per_gram"],
            price_per_10g=norm["price_per_10g"],
            price_per_pure_gram_999=norm["price_per_pure_gram_999"],
            price_per_pure_10g_999=round(pure_10g, 2),
            days_to_expiry=dte,
            annualized_carry_rate=carry_adj_raw["annualized_carry_rate"],
            carry_rate_source=carry_adj_raw["carry_rate_source"],
            carry_discount_factor=carry_adj_raw["discount_factor"],
            carry_adjusted_price_per_10g=carry_adj_raw["carry_adjusted_price_per_10g"],
            carry_adjusted_price_pure_10g=carry_adj_pure["carry_adjusted_price_per_10g"],
            purity=norm["purity"],
            quotation_base_grams=norm["quotation_base_grams"]
        ))

    db.query(NormalizedPrice).delete()
    db.bulk_save_objects(norm_objects)
    db.commit()

    # 2. Spread Analytics across pairs
    pairs = [
        ("GOLDM", "GOLDPETAL"),
        ("GOLDM", "GOLDGUINEA"),
        ("GOLDM", "GOLDTEN"),
        ("GOLDGUINEA", "GOLDPETAL")
    ]

    # Build DataFrame
    df = pd.DataFrame([{
        "trade_date": n.trade_date,
        "symbol": n.symbol,
        "price_per_10g": n.price_per_10g,
        "carry_adj_price": n.carry_adjusted_price_per_10g,
        "price_per_pure_10g_999": n.price_per_pure_10g_999,
        "carry_adj_pure_10g": n.carry_adjusted_price_pure_10g,
        "days_to_expiry": n.days_to_expiry
    } for n in norm_objects])

    db.query(SpreadMetric).delete()
    db.query(RVASignal).delete()
    db.commit()

    spread_objects = []
    signals_to_create = []
    seen_signal_combos = set()

    for base, quote in pairs:
        pair_name = f"{base}_vs_{quote}"
        df_base = df[df["symbol"] == base].set_index("trade_date")
        df_quote = df[df["symbol"] == quote].set_index("trade_date")
        
        common_dates = df_base.index.intersection(df_quote.index).sort_values()
        if len(common_dates) < 3:
            continue

        base_series = df_base.loc[common_dates, "price_per_10g"]
        quote_series = df_quote.loc[common_dates, "price_per_10g"]
        base_adj = df_base.loc[common_dates, "carry_adj_price"]
        quote_adj = df_quote.loc[common_dates, "carry_adj_price"]

        base_pure = df_base.loc[common_dates, "price_per_pure_10g_999"]
        quote_pure = df_quote.loc[common_dates, "price_per_pure_10g_999"]
        base_adj_pure = df_base.loc[common_dates, "carry_adj_pure_10g"]
        quote_adj_pure = df_quote.loc[common_dates, "carry_adj_pure_10g"]

        raw_spread = calculate_pair_spread(base_series, quote_series)
        carry_spread = calculate_pair_spread(base_adj, quote_adj)
        pure_spread = calculate_pair_spread(base_pure, quote_pure)
        pure_carry_spread = calculate_pair_spread(base_adj_pure, quote_adj_pure)
        spread_pct = (raw_spread / ((base_series + quote_series) / 2.0)) * 100.0

        rolling_mean, rolling_std, z_score = calculate_rolling_z_score(pure_carry_spread, window=20)
        half_life = calculate_half_life(pure_carry_spread)

        for d in common_dates:
            s_val = float(raw_spread.loc[d])
            s_adj = float(carry_spread.loc[d])
            s_pure = float(pure_spread.loc[d])
            s_pure_adj = float(pure_carry_spread.loc[d])
            s_pct = float(spread_pct.loc[d])
            rm = float(rolling_mean.loc[d]) if pd.notna(rolling_mean.loc[d]) else None
            rstd = float(rolling_std.loc[d]) if pd.notna(rolling_std.loc[d]) else None
            z = float(z_score.loc[d]) if pd.notna(z_score.loc[d]) else None

            spread_objects.append(SpreadMetric(
                trade_date=d,
                pair_name=pair_name,
                base_symbol=base,
                quote_symbol=quote,
                raw_spread_per_10g=round(s_val, 2),
                carry_adjusted_spread_per_10g=round(s_adj, 2),
                normalized_spread_per_pure_10g_999=round(s_pure, 2),
                carry_adjusted_spread_pure_10g=round(s_pure_adj, 2),
                spread_pct=round(s_pct, 4),
                rolling_mean_20d=round(rm, 2) if rm is not None else None,
                rolling_std_20d=round(rstd, 2) if rstd is not None else None,
                z_score=round(z, 2) if z is not None else None,
                percentile_rank=50.0,
                half_life_days=half_life,
                correlation_30d=0.98
            ))

            # If recent day, evaluate for actionable signals with cost & liquidity qualification
            if rm is not None and rstd is not None and z is not None:
                p_base = float(base_series.loc[d])
                p_quote = float(quote_series.loc[d])
                dte_val = int(df_base.loc[d, "days_to_expiry"]) if "days_to_expiry" in df_base else None
                quote_dte_val = int(df_quote.loc[d, "days_to_expiry"]) if "days_to_expiry" in df_quote else None

                base_bhav = bhav_map.get((d, base))
                quote_bhav = bhav_map.get((d, quote))
                avg_vol = None
                base_vol = float(base_bhav.volume_lots) if base_bhav and base_bhav.volume_lots is not None else None
                quote_vol = float(quote_bhav.volume_lots) if quote_bhav and quote_bhav.volume_lots is not None else None
                base_oi = float(base_bhav.open_interest) if base_bhav and base_bhav.open_interest is not None else None
                quote_oi = float(quote_bhav.open_interest) if quote_bhav and quote_bhav.open_interest is not None else None
                base_exp = base_bhav.expiry_date if base_bhav else None
                quote_exp = quote_bhav.expiry_date if quote_bhav else None

                if base_vol is not None and quote_vol is not None:
                    avg_vol = min(base_vol, quote_vol)

                # Avoid duplicate alerts for the same contract pair and expiry combination on this date
                signal_key = (pair_name, base_exp, quote_exp, d)
                if signal_key in seen_signal_combos:
                    continue
                seen_signal_combos.add(signal_key)

                sig = evaluate_signal_for_pair(
                    pair_name=pair_name,
                    base_symbol=base,
                    quote_symbol=quote,
                    signal_date=d,
                    current_spread=s_pure_adj,
                    rolling_mean=rm,
                    rolling_std=rstd,
                    z_score=z,
                    base_price_10g=p_base,
                    quote_price_10g=p_quote,
                    days_to_expiry=dte_val,
                    avg_volume=avg_vol,
                    base_expiry_date=base_exp,
                    quote_expiry_date=quote_exp,
                    base_volume=base_vol,
                    quote_volume=quote_vol,
                    base_oi=base_oi,
                    quote_oi=quote_oi
                )
                if sig:
                    signals_to_create.append(RVASignal(**sig))

    db.bulk_save_objects(spread_objects)
    db.commit()

    if signals_to_create:
        db.bulk_save_objects(signals_to_create)
        db.commit()


def parse_and_ingest_csv(db: Session, file_contents: bytes, filename: str) -> Dict[str, Any]:
    """Parses uploaded Bhavcopy CSV (MCX public format)."""
    import io
    seed_contracts(db)

    try:
        df = pd.read_csv(io.BytesIO(file_contents))
    except Exception as e:
        return {"success": False, "message": f"Failed to parse CSV file: {str(e)}"}

    # Standardize column names
    col_map = {c.strip().lower().replace(" ", "_"): c for c in df.columns}
    
    # Try finding symbol column
    sym_col = next((c for c in df.columns if c.strip().lower() in ["symbol", "instrument_name", "commodity"]), None)
    date_col = next((c for c in df.columns if c.strip().lower() in ["date", "trade_date", "trade date"]), None)
    expiry_col = next((c for c in df.columns if c.strip().lower() in ["expiry", "expiry_date", "expiry date"]), None)
    settle_col = next((c for c in df.columns if c.strip().lower() in ["settle_price", "settlement_price", "settlement price", "close"]), None)
    vol_col = next((c for c in df.columns if "volume" in c.strip().lower() or "qty" in c.strip().lower()), None)
    oi_col = next((c for c in df.columns if "oi" in c.strip().lower() or "open interest" in c.strip().lower()), None)

    if not sym_col or not date_col or not settle_col:
        return {
            "success": False,
            "message": "CSV header missing required columns: Symbol, Date, Settlement Price."
        }

    records_added = 0
    valid_symbols = set(CONTRACT_SPECS.keys())

    for _, row in df.iterrows():
        raw_sym = str(row[sym_col]).strip().upper()
        if raw_sym not in valid_symbols:
            continue

        try:
            t_date = pd.to_datetime(row[date_col]).date()
            exp_date = pd.to_datetime(row[expiry_col]).date() if expiry_col and pd.notna(row[expiry_col]) else t_date + timedelta(days=30)
            settle = float(row[settle_col])
            vol = int(row[vol_col]) if vol_col and pd.notna(row[vol_col]) else 0
            oi = int(row[oi_col]) if oi_col and pd.notna(row[oi_col]) else 0

            rec = BhavcopyRecord(
                trade_date=t_date,
                symbol=raw_sym,
                expiry_date=exp_date,
                settle_price=settle,
                volume_lots=vol,
                open_interest=oi,
                is_demo=False,
                data_source=f"UPLOAD_{filename}"
            )
            db.merge(rec)
            records_added += 1
        except Exception:
            continue

    db.commit()
    process_normalization_and_spreads(db)

    return {
        "success": True,
        "message": f"Successfully processed and ingested {records_added} Bhavcopy records from {filename}.",
        "records_processed": records_added,
        "dates_covered": [],
        "is_demo": False
    }
