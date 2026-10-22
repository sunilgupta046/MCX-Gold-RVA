from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.data_quality import DataQualityAuditResponse
from app.services.data_quality import run_data_quality_checks
from app.models.data_quality import DataQualityLog
from datetime import datetime

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


@router.get("/report", response_model=DataQualityAuditResponse)
def get_report(db: Session = Depends(get_db)):
    """Retrieves current data quality audit report and anomaly flags."""
    res = run_data_quality_checks(db)
    return DataQualityAuditResponse(
        audit_date=datetime.utcnow(),
        total_records=res["total_records"],
        distinct_dates=res["distinct_dates"],
        contracts_checked=res["contracts_checked"],
        missing_dates_detected=res["missing_dates_detected"],
        zero_volume_days=res["zero_volume_days"],
        price_jump_anomalies=res["price_jump_anomalies"],
        overall_health_score=res["overall_health_score"],
        status=res["status"],
        anomalies=res["anomalies"],
        warnings=res["warnings"],
        is_demo_dataset=res["is_demo_dataset"]
    )


@router.post("/audit", response_model=DataQualityAuditResponse)
def run_audit(db: Session = Depends(get_db)):
    """Executes a fresh data quality audit scan and logs the result."""
    res = run_data_quality_checks(db)
    
    log = DataQualityLog(
        total_records=res["total_records"],
        distinct_dates=res["distinct_dates"],
        contracts_checked=res["contracts_checked"],
        missing_dates_detected=res["missing_dates_detected"],
        zero_volume_days=res["zero_volume_days"],
        price_jump_anomalies=res["price_jump_anomalies"],
        overall_health_score=res["overall_health_score"],
        status=res["status"],
        details={"anomalies": res["anomalies"]}
    )
    db.add(log)
    db.commit()

    return DataQualityAuditResponse(
        audit_date=datetime.utcnow(),
        total_records=res["total_records"],
        distinct_dates=res["distinct_dates"],
        contracts_checked=res["contracts_checked"],
        missing_dates_detected=res["missing_dates_detected"],
        zero_volume_days=res["zero_volume_days"],
        price_jump_anomalies=res["price_jump_anomalies"],
        overall_health_score=res["overall_health_score"],
        status=res["status"],
        anomalies=res["anomalies"],
        warnings=res["warnings"],
        is_demo_dataset=res["is_demo_dataset"]
    )
