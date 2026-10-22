from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import pandas as pd
from app.database import get_db
from app.models.normalized_price import NormalizedPrice
from app.models.spread_metrics import SpreadMetric
from app.models.signals import RVASignal
from app.models.bhavcopy import BhavcopyRecord
from app.config import settings
from app.schemas.analytics import (
    NormalizedPriceResponse,
    SpreadMetricResponse,
    CorrelationMatrixResponse,
    CarryCurveResponse,
    CarryCurvePoint,
    AnalyticsOverviewResponse,
    TermStructureResponse,
    TermStructurePoint,
    VolumeOIResponse,
    VolumeOIPoint,
    SpreadDetailResponse
)
from app.services.spread_analytics import compute_correlation_matrix

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/normalized-prices", response_model=List[NormalizedPriceResponse])
def get_normalized_prices(
    symbol: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    expiry_date: Optional[date] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db)
):
    """Retrieves standardized prices (₹/gram, ₹/10g, and 999-purity basis) across contracts."""
    query = db.query(NormalizedPrice)
    if symbol:
        query = query.filter(NormalizedPrice.symbol == symbol.upper())
    if start_date:
        query = query.filter(NormalizedPrice.trade_date >= start_date)
    if end_date:
        query = query.filter(NormalizedPrice.trade_date <= end_date)
    if expiry_date:
        query = query.filter(NormalizedPrice.expiry_date == expiry_date)
    return query.order_by(NormalizedPrice.trade_date.asc(), NormalizedPrice.symbol.asc()).limit(limit).all()


@router.get("/spreads", response_model=List[SpreadMetricResponse])
def get_spread_metrics(
    pair_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db)
):
    """Retrieves pair spreads, rolling statistics, and Z-scores on 999-purity basis."""
    query = db.query(SpreadMetric)
    if pair_name:
        query = query.filter(SpreadMetric.pair_name == pair_name)
    if start_date:
        query = query.filter(SpreadMetric.trade_date >= start_date)
    if end_date:
        query = query.filter(SpreadMetric.trade_date <= end_date)
    return query.order_by(SpreadMetric.trade_date.asc()).limit(limit).all()


@router.get("/correlation-matrix", response_model=CorrelationMatrixResponse)
def get_correlation_matrix_endpoint(db: Session = Depends(get_db)):
    """Computes rolling correlation matrix of 999-purity normalized prices."""
    records = db.query(NormalizedPrice).all()
    if not records:
        return CorrelationMatrixResponse(
            contracts=[],
            matrix=[],
            start_date=date.today(),
            end_date=date.today()
        )

    df = pd.DataFrame([{
        "trade_date": r.trade_date,
        "symbol": r.symbol,
        "price": r.price_per_pure_10g_999 or r.price_per_10g
    } for r in records])

    pivoted = df.pivot_table(index="trade_date", columns="symbol", values="price")
    result = compute_correlation_matrix(pivoted)

    return CorrelationMatrixResponse(
        contracts=result["contracts"],
        matrix=result["matrix"],
        start_date=min(df["trade_date"]),
        end_date=max(df["trade_date"])
    )


@router.get("/carry-curve", response_model=CarryCurveResponse)
def get_carry_curve(db: Session = Depends(get_db)):
    """Computes the term-structure carry curve across maturities with explicit assumption labeling."""
    latest_date = db.query(NormalizedPrice.trade_date).order_by(NormalizedPrice.trade_date.desc()).first()
    if not latest_date:
        today = date.today()
        return CarryCurveResponse(
            as_of_date=today,
            points=[],
            risk_free_rate_pct=settings.ANNUAL_RISK_FREE_RATE * 100.0,
            storage_rate_pct=settings.GOLD_STORAGE_INSURANCE_RATE * 100.0
        )

    as_of = latest_date[0]
    records = db.query(NormalizedPrice).filter(NormalizedPrice.trade_date == as_of).all()

    points = []
    for r in records:
        t_years = r.days_to_expiry / 365.0
        carry_adj_price = r.carry_adjusted_price_pure_10g or r.carry_adjusted_price_per_10g
        norm_price = r.price_per_pure_10g_999 or r.price_per_10g
        implied_carry = ((norm_price / carry_adj_price - 1.0) / t_years * 100.0) if t_years > 0 and carry_adj_price > 0 else (r.annualized_carry_rate * 100.0)
        
        points.append(CarryCurvePoint(
            symbol=r.symbol,
            expiry_date=r.expiry_date,
            days_to_expiry=r.days_to_expiry,
            raw_price=r.raw_settle_price,
            price_per_10g=r.price_per_10g,
            price_per_pure_gram_999=r.price_per_pure_gram_999,
            implied_annualized_carry_pct=round(implied_carry, 2),
            carry_rate_source=r.carry_rate_source or "FIXED_ASSUMPTION_7.0PCT"
        ))

    return CarryCurveResponse(
        as_of_date=as_of,
        points=points,
        risk_free_rate_pct=round(settings.ANNUAL_RISK_FREE_RATE * 100.0, 2),
        storage_rate_pct=round(settings.GOLD_STORAGE_INSURANCE_RATE * 100.0, 2)
    )


@router.get("/term-structure", response_model=TermStructureResponse)
def get_term_structure(
    as_of: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns the futures term structure across all active gold contracts and maturities for a given date.
    Displays both unadjusted and 999-purity normalized prices alongside Volume & Open Interest.
    """
    if not as_of:
        latest_date_row = db.query(NormalizedPrice.trade_date).order_by(NormalizedPrice.trade_date.desc()).first()
        if not latest_date_row:
            return TermStructureResponse(as_of_date=date.today(), contracts=[])
        as_of = latest_date_row[0]

    norm_records = db.query(NormalizedPrice).filter(NormalizedPrice.trade_date == as_of).all()
    bhav_records = db.query(BhavcopyRecord).filter(BhavcopyRecord.trade_date == as_of).all()
    bhav_map = {r.symbol: r for r in bhav_records}

    points = []
    for n in norm_records:
        b = bhav_map.get(n.symbol)
        points.append(TermStructurePoint(
            symbol=n.symbol,
            expiry_date=n.expiry_date,
            days_to_expiry=n.days_to_expiry,
            raw_settle_price=n.raw_settle_price,
            price_per_10g=n.price_per_10g,
            price_per_pure_10g_999=n.price_per_pure_10g_999 or n.price_per_10g,
            volume_lots=b.volume_lots if b else 0,
            open_interest=b.open_interest if b else 0
        ))

    points.sort(key=lambda p: (p.days_to_expiry, p.symbol))
    return TermStructureResponse(as_of_date=as_of, contracts=points)


@router.get("/volume-oi", response_model=VolumeOIResponse)
def get_volume_oi(
    symbol: str = Query("GOLDM"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns daily volume and open interest time series for a contract to inspect liquidity trends.
    """
    query = db.query(BhavcopyRecord).filter(BhavcopyRecord.symbol == symbol.upper())
    if start_date:
        query = query.filter(BhavcopyRecord.trade_date >= start_date)
    if end_date:
        query = query.filter(BhavcopyRecord.trade_date <= end_date)

    records = query.order_by(BhavcopyRecord.trade_date.asc()).all()
    if not records:
        return VolumeOIResponse(symbol=symbol.upper(), series=[], avg_volume_30d=0.0, max_oi=0)

    series = [
        VolumeOIPoint(
            trade_date=r.trade_date,
            symbol=r.symbol,
            settle_price=r.settle_price,
            volume_lots=r.volume_lots,
            volume_value_lakhs=r.volume_value_lakhs,
            open_interest=r.open_interest,
            change_in_oi=r.change_in_oi
        )
        for r in records
    ]

    recent_30 = series[-30:] if len(series) >= 30 else series
    avg_vol = sum(p.volume_lots for p in recent_30) / float(len(recent_30)) if recent_30 else 0.0
    max_oi = max((p.open_interest for p in series), default=0)

    return VolumeOIResponse(
        symbol=symbol.upper(),
        series=series,
        avg_volume_30d=round(avg_vol, 1),
        max_oi=max_oi
    )


@router.get("/spread-details", response_model=SpreadDetailResponse)
def get_spread_details(
    pair_name: str = Query("GOLDM_vs_GOLDPETAL"),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db)
):
    """
    Returns full spread series and statistical context for a specific pair, including 999 purity basis.
    """
    metrics = (
        db.query(SpreadMetric)
        .filter(SpreadMetric.pair_name == pair_name)
        .order_by(SpreadMetric.trade_date.asc())
        .limit(limit)
        .all()
    )
    if not metrics:
        raise HTTPException(status_code=404, detail=f"No spread data found for pair {pair_name}")

    latest = metrics[-1]
    tokens = pair_name.split("_vs_")
    base = tokens[0] if len(tokens) > 0 else "UNKNOWN"
    quote = tokens[1] if len(tokens) > 1 else "UNKNOWN"

    purity_note = (
        f"Spread metrics are calculated on a standardized 999-fineness pure gold basis. "
        f"GOLDM (995 fineness) prices are scaled by (999/995 = 1.00402) to adjust for 0.4% purity difference "
        f"relative to {quote} (999 fineness)."
    )

    return SpreadDetailResponse(
        pair_name=pair_name,
        base_symbol=base,
        quote_symbol=quote,
        history=metrics,
        current_z_score=latest.z_score,
        half_life_days=latest.half_life_days,
        historical_purity_note=purity_note
    )


@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_overview_metrics(db: Session = Depends(get_db)):
    """Provides high-level dashboard metrics, live spreads, and divergence pairs."""
    latest_date_row = db.query(NormalizedPrice.trade_date).order_by(NormalizedPrice.trade_date.desc()).first()
    as_of = latest_date_row[0] if latest_date_row else None

    # Benchmark GOLDM price
    benchmark_row = None
    if as_of:
        benchmark_row = (
            db.query(NormalizedPrice)
            .filter(NormalizedPrice.trade_date == as_of, NormalizedPrice.symbol == "GOLDM")
            .first()
        )

    # Active pairs current spread
    spreads = []
    top_divergence = None
    max_abs_z = -1.0

    if as_of:
        latest_spreads = db.query(SpreadMetric).filter(SpreadMetric.trade_date == as_of).all()
        for s in latest_spreads:
            s_dict = {
                "pair_name": s.pair_name,
                "base_symbol": s.base_symbol,
                "quote_symbol": s.quote_symbol,
                "raw_spread_per_10g": s.raw_spread_per_10g,
                "carry_adjusted_spread_per_10g": s.carry_adjusted_spread_per_10g,
                "normalized_spread_per_pure_10g_999": s.normalized_spread_per_pure_10g_999,
                "carry_adjusted_spread_pure_10g": s.carry_adjusted_spread_pure_10g,
                "spread_pct": s.spread_pct,
                "rolling_mean_20d": s.rolling_mean_20d,
                "z_score": s.z_score,
                "half_life_days": s.half_life_days
            }
            spreads.append(s_dict)
            if s.z_score is not None and abs(s.z_score) > max_abs_z:
                max_abs_z = abs(s.z_score)
                top_divergence = s_dict

    signals_count = db.query(RVASignal).filter(RVASignal.status == "ACTIVE").count()
    total_data_points = db.query(BhavcopyRecord).count()

    return AnalyticsOverviewResponse(
        as_of_date=as_of,
        benchmark_goldm_price_10g=benchmark_row.price_per_10g if benchmark_row else None,
        benchmark_pure_price_10g_999=benchmark_row.price_per_pure_10g_999 if benchmark_row else None,
        contracts_count=4,
        total_data_points=total_data_points,
        active_pairs=["GOLDM_vs_GOLDPETAL", "GOLDM_vs_GOLDGUINEA", "GOLDM_vs_GOLDTEN", "GOLDGUINEA_vs_GOLDPETAL"],
        current_spreads=spreads,
        top_divergence_pair=top_divergence,
        active_signals_count=signals_count
    )
