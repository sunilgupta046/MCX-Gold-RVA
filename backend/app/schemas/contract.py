from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class ContractBase(BaseModel):
    symbol: str
    name: str
    trading_unit_grams: float
    quotation_unit_grams: float
    quotation_base_grams: Optional[float] = None
    purity: Optional[float] = 999.0
    tick_size: float
    contract_multiplier: float
    description: Optional[str] = None
    is_active: bool = True


class ContractResponse(ContractBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
