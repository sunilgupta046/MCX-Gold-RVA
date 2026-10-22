from app.routers.health import router as health_router
from app.routers.contracts import router as contracts_router
from app.routers.bhavcopy import router as bhavcopy_router
from app.routers.analytics import router as analytics_router
from app.routers.signals import router as signals_router
from app.routers.backtest import router as backtest_router
from app.routers.data_quality import router as data_quality_router
from app.routers.admin import router as admin_router
from app.routers.ingestion import router as ingestion_router

__all__ = [
    "health_router",
    "contracts_router",
    "bhavcopy_router",
    "analytics_router",
    "signals_router",
    "backtest_router",
    "data_quality_router",
    "admin_router",
    "ingestion_router",
]
