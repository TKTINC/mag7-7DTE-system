from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uvicorn
import logging
from datetime import datetime

from app.config import settings
from app.database import get_db
from app.api.v1 import market_data, signals, trading, analytics, reporting, conversational_ai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="A sophisticated algorithmic trading platform focused on the Magnificent 7 stocks with 7-day-to-expiration options strategies.",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(market_data.router, prefix="/api/v1/market-data", tags=["Market Data"])
app.include_router(signals.router, prefix="/api/v1/signals", tags=["Signals"])
app.include_router(trading.router, prefix="/api/v1/trading", tags=["Trading"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(reporting.router, prefix="/api/v1/reporting", tags=["Reporting"])
app.include_router(conversational_ai.router, prefix="/api/v1/ai", tags=["Conversational AI"])

@app.get("/")
def read_root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/api/v1/config")
def get_public_config():
    """Return public configuration settings for the frontend."""
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "mag7_symbols": settings.MAG7_SYMBOLS,
        "etf_symbols": settings.ETF_SYMBOLS,
        "index_symbols": settings.INDEX_SYMBOLS,
        "default_dte": settings.DEFAULT_DTE,
        "trading_hours": {
            "start": settings.TRADING_HOURS_START,
            "end": settings.TRADING_HOURS_END,
        },
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

