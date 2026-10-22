from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models.bhavcopy import BhavcopyRecord
from app.models.normalized_price import NormalizedPrice
from app.models.spread_metrics import SpreadMetric
from app.models.signals import RVASignal
from app.models.backtest import BacktestRun
from app.models.data_quality import DataQualityLog
from app.services.ingestion import seed_contracts

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/config")
def get_config(db: Session = Depends(get_db)):
    """Returns current system configuration and cost settings."""
    return {
        "project_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL,
        "annual_risk_free_rate": settings.ANNUAL_RISK_FREE_RATE,
        "gold_storage_insurance_rate": settings.GOLD_STORAGE_INSURANCE_RATE,
        "mcx_charges": {
            "exchange_turnover_fee_pct": settings.EXCHANGE_TURNOVER_FEE_PCT,
            "sebi_turnover_fee_pct": settings.SEBI_TURNOVER_FEE_PCT,
            "ctt_sell_pct": settings.CTT_SELL_PCT,
            "gst_pct": settings.GST_PCT,
            "stamp_duty_buy_pct": settings.STAMP_DUTY_BUY_PCT,
            "default_slippage_ticks": settings.DEFAULT_SLIPPAGE_TICKS,
        },
        "records_count": db.query(BhavcopyRecord).count(),
        "spread_count": db.query(SpreadMetric).count(),
        "signals_count": db.query(RVASignal).count(),
        "backtest_count": db.query(BacktestRun).count(),
    }


@router.post("/reset")
def reset_database(db: Session = Depends(get_db)):
    """Clears all market records and resets platform to empty state."""
    db.query(RVASignal).delete()
    db.query(SpreadMetric).delete()
    db.query(NormalizedPrice).delete()
    db.query(BhavcopyRecord).delete()
    db.query(BacktestRun).delete()
    db.query(DataQualityLog).delete()
    db.commit()
    seed_contracts(db)
    return {"message": "Database successfully reset to clean initial state."}
