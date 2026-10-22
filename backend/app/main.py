from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from app.config import settings
from app.database import init_db, SessionLocal
from app.services.ingestion import seed_contracts, generate_synthetic_demo_bhavcopy
from app.models.bhavcopy import BhavcopyRecord
from app.routers import (
    health_router,
    contracts_router,
    bhavcopy_router,
    analytics_router,
    signals_router,
    backtest_router,
    data_quality_router,
    admin_router,
    ingestion_router,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcx_gold_rva")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema via lifespan...")
    init_db()
    
    # Auto-seed contracts & default demo records if completely empty
    db = SessionLocal()
    try:
        seed_contracts(db)
        record_count = db.query(BhavcopyRecord).count()
        if record_count == 0:
            logger.info("Empty database detected. Seeding initial 90-day DEMO Bhavcopy dataset...")
            generate_synthetic_demo_bhavcopy(db, days=90)
            logger.info("Initial DEMO dataset created and analyzed.")
    except Exception as e:
        logger.error(f"Error during startup initialization: {e}")
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Quantitative Relative Value Analytics (RVA) platform for MCX Gold futures contracts (GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL).",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred.", "error": str(exc)},
    )


# Mount routers
app.include_router(health_router, prefix="")
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(contracts_router, prefix=settings.API_V1_STR)
app.include_router(bhavcopy_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(signals_router, prefix=settings.API_V1_STR)
app.include_router(backtest_router, prefix=settings.API_V1_STR)
app.include_router(data_quality_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(ingestion_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "message": "Welcome to MCX Gold RVA — Relative Value Analytics Platform",
        "docs": "/docs",
        "health": "/health",
        "version": settings.VERSION,
        "team": "COZY NEXUS"
    }
