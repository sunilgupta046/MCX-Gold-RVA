from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.database import get_db
from app.models.signals import RVASignal
from app.schemas.signal import (
    SignalResponse,
    CandidateEvaluationResponse,
    AlertHistoryResponse,
    AlertHistoryItem
)
from app.services.ingestion import process_normalization_and_spreads
from app.services.signal_qualification import evaluate_latest_candidates, ANALYTICAL_DISCLAIMER

router = APIRouter(prefix="/signals", tags=["Signals"])


@router.get("", response_model=List[SignalResponse])
def get_all_signals(
    pair_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    strength: Optional[str] = Query(None),
    is_qualified: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieves all relative value signals with filtering options including qualification check."""
    query = db.query(RVASignal)
    if pair_name:
        query = query.filter(RVASignal.pair_name == pair_name)
    if status:
        query = query.filter(RVASignal.status == status.upper())
    if strength:
        query = query.filter(RVASignal.strength == strength.upper())
    if is_qualified is not None:
        query = query.filter(RVASignal.is_qualified == is_qualified)
    return query.order_by(RVASignal.signal_date.desc(), RVASignal.id.desc()).offset(offset).limit(limit).all()


@router.get("/candidates", response_model=CandidateEvaluationResponse)
def get_latest_candidate_opportunities(
    expiry_lockout_days: int = Query(5, ge=1, le=30),
    cost_coverage_hurdle: float = Query(2.5, ge=1.0, le=10.0),
    db: Session = Depends(get_db)
):
    """
    Evaluates real-time cross-contract pair opportunities against all 10 qualification rules:
      - Normalized & carry-adjusted spreads
      - Expected gross edge vs estimated round-trip costs
      - Expected net edge
      - Liquidity (volume & open interest) filters
      - T-5 expiry delivery lockout
      - 2.5x total cost multiplier hurdle
      - Positive net edge
      - Rejection reasons recorded for every candidate
      - Never fabricates alerts when no candidate qualifies
    """
    return evaluate_latest_candidates(
        db=db,
        expiry_lockout_days=expiry_lockout_days,
        cost_coverage_hurdle=cost_coverage_hurdle,
        persist_qualified=True
    )


@router.get("/qualified", response_model=List[SignalResponse])
def get_qualified_signals(db: Session = Depends(get_db)):
    """Retrieves only fully qualified alerts (QUALIFIED_FOR_REVIEW / ACTIVE)."""
    return (
        db.query(RVASignal)
        .filter(RVASignal.status.in_(["QUALIFIED_FOR_REVIEW", "ACTIVE"]), RVASignal.is_qualified == True)
        .order_by(RVASignal.signal_date.desc(), RVASignal.id.desc())
        .all()
    )


@router.get("/active", response_model=List[SignalResponse])
def get_active_signals(db: Session = Depends(get_db)):
    """Retrieves current open/active signals (QUALIFIED_FOR_REVIEW or ACTIVE)."""
    return (
        db.query(RVASignal)
        .filter(RVASignal.status.in_(["QUALIFIED_FOR_REVIEW", "ACTIVE"]))
        .order_by(RVASignal.signal_date.desc(), RVASignal.id.desc())
        .all()
    )


@router.get("/history", response_model=AlertHistoryResponse)
def get_alert_history(
    pair_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_qualified: Optional[bool] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieves paginated history of all signal candidates and alerts with audit trails."""
    query = db.query(RVASignal)
    if pair_name:
        query = query.filter(RVASignal.pair_name == pair_name)
    if status:
        query = query.filter(RVASignal.status == status.upper())
    if is_qualified is not None:
        query = query.filter(RVASignal.is_qualified == is_qualified)
    if start_date:
        query = query.filter(RVASignal.signal_date >= start_date)
    if end_date:
        query = query.filter(RVASignal.signal_date <= end_date)

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(RVASignal.signal_date.desc(), RVASignal.id.desc()).offset(offset).limit(page_size).all()

    return AlertHistoryResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items
    )


@router.get("/quiet-alerts", response_model=List[SignalResponse])
def get_quiet_alerts(
    min_net_edge_bps: float = Query(5.0, ge=0.0, le=100.0),
    min_strength: Optional[str] = Query(None),
    qualified_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    Returns curated quiet alerts with noise suppression and threshold filtering:
      - Only qualified actionable signals (no illiquid or tender-period contracts).
      - Net edge >= min_net_edge_bps hurdle (filters out marginal edge signals).
      - Optional strength filter (e.g. HIGH, EXTREME).
      - Hysteresis: prevents alerting repeatedly when a pair hovers around threshold.
    """
    query = db.query(RVASignal)
    if qualified_only:
        query = query.filter(RVASignal.is_qualified == True, RVASignal.status.in_(["QUALIFIED_FOR_REVIEW", "ACTIVE"]))
    if min_net_edge_bps > 0:
        query = query.filter(RVASignal.net_edge_bps >= min_net_edge_bps)
    if min_strength:
        valid_strengths = ["HIGH", "EXTREME"] if min_strength.upper() == "HIGH" else [min_strength.upper()]
        query = query.filter(RVASignal.strength.in_(valid_strengths))

    all_matches = query.order_by(RVASignal.signal_date.desc(), RVASignal.id.desc()).all()

    # Deduplicate recent consecutive signals for the same pair (hysteresis quiet filter)
    seen_pairs = set()
    quiet_signals = []
    for s in all_matches:
        if s.pair_name not in seen_pairs:
            seen_pairs.add(s.pair_name)
            quiet_signals.append(s)

    return quiet_signals


@router.post("/evaluate", response_model=CandidateEvaluationResponse)
def evaluate_candidates_on_demand(
    expiry_lockout_days: int = Query(5, ge=1, le=30),
    cost_coverage_hurdle: float = Query(2.5, ge=1.0, le=10.0),
    db: Session = Depends(get_db)
):
    """On-demand candidate qualification evaluation across all pairs on latest data."""
    return evaluate_latest_candidates(
        db=db,
        expiry_lockout_days=expiry_lockout_days,
        cost_coverage_hurdle=cost_coverage_hurdle,
        persist_qualified=True
    )


@router.post("/generate")
def recompute_signals(db: Session = Depends(get_db)):
    """Triggers signal recalculation based on latest settlement records."""
    process_normalization_and_spreads(db)
    evaluate_latest_candidates(db=db, persist_qualified=True)
    count = db.query(RVASignal).count()
    return {"message": "Signals regenerated successfully", "total_signals": count}

