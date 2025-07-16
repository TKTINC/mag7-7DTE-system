from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.market_data import Instrument, StockPrice, Option, OptionPriceData, EarningsData, FinancialMetric, AnalystRating
from app.schemas.market_data import (
    InstrumentResponse, StockPriceResponse, OptionResponse, 
    OptionPriceResponse, EarningsDataResponse, FinancialMetricResponse,
    AnalystRatingResponse
)
from app.services.data_feed_service import get_real_time_quote

router = APIRouter()

@router.get("/instruments", response_model=List[InstrumentResponse])
def get_instruments(
    type: Optional[str] = None,
    sector: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all instruments with optional filtering by type and sector.
    """
    query = db.query(Instrument)
    
    if type:
        query = query.filter(Instrument.type == type)
    
    if sector:
        query = query.filter(Instrument.sector == sector)
    
    return query.all()

@router.get("/instruments/{symbol}", response_model=InstrumentResponse)
def get_instrument(symbol: str, db: Session = Depends(get_db)):
    """
    Get instrument details by symbol.
    """
    instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument with symbol {symbol} not found")
    return instrument

@router.get("/stock-prices/{symbol}", response_model=List[StockPriceResponse])
def get_stock_prices(
    symbol: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    interval: Optional[str] = "1d",
    db: Session = Depends(get_db)
):
    """
    Get historical stock prices for a symbol.
    """
    instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument with symbol {symbol} not found")
    
    query = db.query(StockPrice).filter(StockPrice.instrument_id == instrument.id)
    
    if start_date:
        query = query.filter(StockPrice.timestamp >= start_date)
    
    if end_date:
        query = query.filter(StockPrice.timestamp <= end_date)
    
    # Default to last 30 days if no dates provided
    if not start_date and not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        query = query.filter(StockPrice.timestamp >= start_date, StockPrice.timestamp <= end_date)
    
    # Order by timestamp
    query = query.order_by(StockPrice.timestamp)
    
    return query.all()

@router.get("/options/{symbol}", response_model=List[OptionResponse])
def get_options(
    symbol: str,
    expiration_date: Optional[datetime] = None,
    min_dte: Optional[int] = None,
    max_dte: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get options for a symbol with optional filtering by expiration date or DTE range.
    """
    instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument with symbol {symbol} not found")
    
    query = db.query(Option).filter(Option.instrument_id == instrument.id)
    
    if expiration_date:
        query = query.filter(Option.expiration_date == expiration_date)
    
    today = datetime.utcnow().date()
    
    if min_dte is not None:
        min_date = today + timedelta(days=min_dte)
        query = query.filter(Option.expiration_date >= min_date)
    
    if max_dte is not None:
        max_date = today + timedelta(days=max_dte)
        query = query.filter(Option.expiration_date <= max_date)
    
    # Default to options with DTE around 7 days if no filters provided
    if not expiration_date and min_dte is None and max_dte is None:
        target_dte = 7
        min_date = today + timedelta(days=target_dte - 2)
        max_date = today + timedelta(days=target_dte + 2)
        query = query.filter(Option.expiration_date >= min_date, Option.expiration_date <= max_date)
    
    # Order by expiration date and strike price
    query = query.order_by(Option.expiration_date, Option.strike_price)
    
    return query.all()

@router.get("/option-prices/{option_symbol}", response_model=List[OptionPriceResponse])
def get_option_prices(
    option_symbol: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get historical option prices for an option symbol.
    """
    option = db.query(Option).filter(Option.symbol == option_symbol).first()
    if not option:
        raise HTTPException(status_code=404, detail=f"Option with symbol {option_symbol} not found")
    
    query = db.query(OptionPriceData).filter(OptionPriceData.option_id == option.id)
    
    if start_date:
        query = query.filter(OptionPriceData.timestamp >= start_date)
    
    if end_date:
        query = query.filter(OptionPriceData.timestamp <= end_date)
    
    # Default to last 7 days if no dates provided
    if not start_date and not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        query = query.filter(OptionPriceData.timestamp >= start_date, OptionPriceData.timestamp <= end_date)
    
    # Order by timestamp
    query = query.order_by(OptionPriceData.timestamp)
    
    return query.all()

@router.get("/earnings/{symbol}", response_model=List[EarningsDataResponse])
def get_earnings_data(
    symbol: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get earnings data for a symbol.
    """
    instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument with symbol {symbol} not found")
    
    query = db.query(EarningsData).filter(EarningsData.instrument_id == instrument.id)
    
    if start_date:
        query = query.filter(EarningsData.earnings_date >= start_date)
    
    if end_date:
        query = query.filter(EarningsData.earnings_date <= end_date)
    
    # Order by earnings date
    query = query.order_by(EarningsData.earnings_date.desc())
    
    return query.all()

@router.get("/financials/{symbol}", response_model=List[FinancialMetricResponse])
def get_financial_metrics(
    symbol: str,
    metric_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get financial metrics for a symbol.
    """
    instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument with symbol {symbol} not found")
    
    query = db.query(FinancialMetric).filter(FinancialMetric.instrument_id == instrument.id)
    
    if metric_type:
        query = query.filter(FinancialMetric.metric_type == metric_type)
    
    if start_date:
        query = query.filter(FinancialMetric.date >= start_date)
    
    if end_date:
        query = query.filter(FinancialMetric.date <= end_date)
    
    # Order by date
    query = query.order_by(FinancialMetric.date.desc())
    
    return query.all()

@router.get("/analyst-ratings/{symbol}", response_model=List[AnalystRatingResponse])
def get_analyst_ratings(
    symbol: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get analyst ratings for a symbol.
    """
    instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument with symbol {symbol} not found")
    
    query = db.query(AnalystRating).filter(AnalystRating.instrument_id == instrument.id)
    
    if start_date:
        query = query.filter(AnalystRating.rating_date >= start_date)
    
    if end_date:
        query = query.filter(AnalystRating.rating_date <= end_date)
    
    # Order by rating date
    query = query.order_by(AnalystRating.rating_date.desc())
    
    return query.all()

@router.get("/real-time-quote/{symbol}")
async def get_real_time_stock_quote(symbol: str):
    """
    Get real-time stock quote for a symbol.
    """
    try:
        quote = await get_real_time_quote(symbol)
        return quote
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

