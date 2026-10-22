from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.contract import Contract
from app.models.bhavcopy import BhavcopyRecord
from app.schemas.contract import ContractResponse
from app.services.ingestion import seed_contracts

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("", response_model=List[ContractResponse])
def get_contracts(db: Session = Depends(get_db)):
    """Retrieves all tracked MCX Gold contract specifications."""
    seed_contracts(db)
    contracts = db.query(Contract).all()
    return contracts


@router.get("/{symbol}/summary")
def get_contract_summary(symbol: str, db: Session = Depends(get_db)):
    """Returns detailed market statistics for a specific contract."""
    contract = db.query(Contract).filter(Contract.symbol == symbol.upper()).first()
    if not contract:
        raise HTTPException(status_code=404, detail=f"Contract '{symbol}' not found.")

    latest_record = (
        db.query(BhavcopyRecord)
        .filter(BhavcopyRecord.symbol == symbol.upper())
        .order_by(BhavcopyRecord.trade_date.desc())
        .first()
    )

    records_count = db.query(BhavcopyRecord).filter(BhavcopyRecord.symbol == symbol.upper()).count()

    return {
        "symbol": contract.symbol,
        "name": contract.name,
        "trading_unit_grams": contract.trading_unit_grams,
        "quotation_unit_grams": contract.quotation_unit_grams,
        "tick_size": contract.tick_size,
        "contract_multiplier": contract.contract_multiplier,
        "description": contract.description,
        "total_historical_records": records_count,
        "latest_settle_price": latest_record.settle_price if latest_record else None,
        "latest_trade_date": latest_record.trade_date if latest_record else None,
        "latest_volume_lots": latest_record.volume_lots if latest_record else 0,
        "latest_open_interest": latest_record.open_interest if latest_record else 0,
        "is_demo_data": latest_record.is_demo if latest_record else False,
    }
