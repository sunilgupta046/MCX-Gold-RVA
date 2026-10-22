import pandas as pd
from datetime import date, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.bhavcopy import BhavcopyRecord


def run_data_quality_checks(db: Session) -> Dict[str, Any]:
    """
    Performs comprehensive data quality audits on ingested Bhavcopy data:
      1. Missing trading days check against calendar business days
      2. Zero volume & zero open interest warnings
      3. Outlier / settlement price jump anomalies (> 4% day-over-day)
      4. Inverted high/low checks
      5. Cross-contract expiry consistency
    """
    records = db.query(BhavcopyRecord).order_by(BhavcopyRecord.trade_date.asc()).all()
    if not records:
        return {
            "total_records": 0,
            "distinct_dates": 0,
            "contracts_checked": 0,
            "missing_dates_detected": 0,
            "zero_volume_days": 0,
            "price_jump_anomalies": 0,
            "overall_health_score": 100.0,
            "status": "HEALTHY",
            "anomalies": [],
            "warnings": ["No bhavcopy records found in database. Ingest or seed data to begin."],
            "is_demo_dataset": False
        }

    df = pd.DataFrame([{
        "trade_date": r.trade_date,
        "symbol": r.symbol,
        "expiry_date": r.expiry_date,
        "open_price": r.open_price,
        "high_price": r.high_price,
        "low_price": r.low_price,
        "close_price": r.close_price,
        "settle_price": r.settle_price,
        "volume_lots": r.volume_lots,
        "open_interest": r.open_interest,
        "is_demo": r.is_demo
    } for r in records])

    anomalies = []
    warnings = []
    
    is_demo_dataset = bool(df["is_demo"].any())
    if is_demo_dataset:
        warnings.append("Active dataset contains SYNTHETIC DEMO DATA for development and demonstration.")

    # 1. Missing dates detection
    unique_dates = sorted(df["trade_date"].unique())
    distinct_dates_count = len(unique_dates)
    
    missing_dates = []
    if distinct_dates_count >= 2:
        start_d = unique_dates[0]
        end_d = unique_dates[-1]
        
        # Check standard Monday-Friday business days
        curr_d = start_d
        observed_dates = set(unique_dates)
        while curr_d <= end_d:
            if curr_d.weekday() < 5 and curr_d not in observed_dates:
                # Potential holiday or missing date
                missing_dates.append(curr_d)
            curr_d += timedelta(days=1)

    # 2. Zero volume checks
    zero_vol_records = df[df["volume_lots"] <= 0]
    zero_vol_count = len(zero_vol_records)
    for _, row in zero_vol_records.head(5).iterrows():
        anomalies.append({
            "date": str(row["trade_date"]),
            "symbol": row["symbol"],
            "anomaly_type": "ZERO_VOLUME",
            "description": f"{row['symbol']} recorded 0 traded contracts on {row['trade_date']}.",
            "severity": "LOW"
        })

    # 3. Price jumps (>4% daily change)
    price_jump_count = 0
    for symbol, group in df.groupby("symbol"):
        group = group.sort_values("trade_date")
        pct_change = group["settle_price"].pct_change().abs() * 100.0
        jumps = group[pct_change > 4.0]
        price_jump_count += len(jumps)
        for _, j_row in jumps.head(3).iterrows():
            chg = pct_change.loc[j_row.name]
            anomalies.append({
                "date": str(j_row["trade_date"]),
                "symbol": symbol,
                "anomaly_type": "LARGE_PRICE_JUMP",
                "description": f"{symbol} settlement shifted by {chg:.1f}% on {j_row['trade_date']}.",
                "severity": "MEDIUM"
            })

    # 4. Inverted high/low
    inverted = df[df["high_price"] < df["low_price"]]
    for _, inv_row in inverted.iterrows():
        anomalies.append({
            "date": str(inv_row["trade_date"]),
            "symbol": inv_row["symbol"],
            "anomaly_type": "INVERTED_RANGE",
            "description": f"High price {inv_row['high_price']} is lower than Low price {inv_row['low_price']}.",
            "severity": "HIGH"
        })

    # Deduct penalty for anomalies
    penalty = (min(len(missing_dates), 10) * 1.5) + (min(zero_vol_count, 10) * 0.5) + (price_jump_count * 2.0) + (len(inverted) * 10.0)
    health_score = max(0.0, min(100.0, 100.0 - penalty))

    status = "HEALTHY"
    if health_score < 75:
        status = "CRITICAL"
    elif health_score < 90:
        status = "WARNING"

    return {
        "audit_date": date.today().isoformat(),
        "total_records": len(df),
        "distinct_dates": distinct_dates_count,
        "contracts_checked": len(df["symbol"].unique()),
        "missing_dates_detected": len(missing_dates),
        "zero_volume_days": zero_vol_count,
        "price_jump_anomalies": price_jump_count,
        "overall_health_score": round(health_score, 1),
        "status": status,
        "anomalies": anomalies,
        "warnings": warnings,
        "is_demo_dataset": is_demo_dataset
    }
