import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MCX Gold RVA — Relative Value Analytics Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "sqlite:///./mcx_gold_rva.db"
    
    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:4173"
    ]
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
        
    # Cost of Carry defaults (India Sovereign/RBI repo proxy ~6.5%, Vault storage ~0.5%)
    ANNUAL_RISK_FREE_RATE: float = 0.065
    GOLD_STORAGE_INSURANCE_RATE: float = 0.005
    
    # MCX Transaction Charges
    EXCHANGE_TURNOVER_FEE_PCT: float = 0.000021  # 0.0021%
    SEBI_TURNOVER_FEE_PCT: float = 0.000001      # 0.0001%
    CTT_SELL_PCT: float = 0.0001                 # 0.01% on sell
    GST_PCT: float = 0.18                        # 18% on exchange & SEBI charges
    STAMP_DUTY_BUY_PCT: float = 0.00002          # 0.002% on buy side
    DEFAULT_SLIPPAGE_TICKS: int = 1
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
