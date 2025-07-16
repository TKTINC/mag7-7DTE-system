import os
import asyncio
import logging
import json
import websockets
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
from sqlalchemy.orm import Session
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from app.config import settings
from app.database import get_db, SessionLocal
from app.models.market_data import (
    Instrument, StockPrice, Option, OptionPriceData, 
    EarningsData, FinancialMetric, AnalystRating
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize InfluxDB client
influxdb_client = InfluxDBClient(
    url=settings.INFLUXDB_URL,
    token=settings.INFLUXDB_TOKEN,
    org=settings.INFLUXDB_ORG
)
write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)

# Polygon.io WebSocket URL
POLYGON_WS_URL = "wss://socket.polygon.io/stocks"

async def get_real_time_quote(symbol: str) -> Dict[str, Any]:
    """
    Get real-time quote for a symbol using Polygon.io REST API.
    """
    url = f"https://api.polygon.io/v2/last/trade/{symbol}"
    params = {
        "apiKey": settings.POLYGON_API_KEY
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "results" not in data:
            raise ValueError(f"Invalid response from Polygon.io: {data}")
        
        result = data["results"]
        
        return {
            "symbol": symbol,
            "last_price": result["p"],
            "bid": None,  # Not available in this endpoint
            "ask": None,  # Not available in this endpoint
            "volume": None,  # Not available in this endpoint
            "timestamp": datetime.fromtimestamp(result["t"] / 1000),
            "change": None,  # Would need previous day's close
            "change_percent": None  # Would need previous day's close
        }

async def get_option_chain(symbol: str, expiration_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Get option chain for a symbol using Polygon.io REST API.
    """
    # If no expiration date is provided, use the closest expiration date around 7 DTE
    if not expiration_date:
        today = datetime.utcnow().date()
        target_date = today + timedelta(days=7)
        # Format as YYYY-MM-DD
        expiration_str = target_date.strftime("%Y-%m-%d")
    else:
        expiration_str = expiration_date.strftime("%Y-%m-%d")
    
    url = f"https://api.polygon.io/v3/reference/options/contracts"
    params = {
        "underlying_ticker": symbol,
        "expiration_date": expiration_str,
        "limit": 1000,
        "apiKey": settings.POLYGON_API_KEY
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "results" not in data:
            raise ValueError(f"Invalid response from Polygon.io: {data}")
        
        return data["results"]

async def get_historical_stock_prices(symbol: str, from_date: datetime, to_date: datetime, timespan: str = "day") -> List[Dict[str, Any]]:
    """
    Get historical stock prices for a symbol using Polygon.io REST API.
    """
    # Format dates as YYYY-MM-DD
    from_str = from_date.strftime("%Y-%m-%d")
    to_str = to_date.strftime("%Y-%m-%d")
    
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/{timespan}/{from_str}/{to_str}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 5000,
        "apiKey": settings.POLYGON_API_KEY
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "results" not in data:
            raise ValueError(f"Invalid response from Polygon.io: {data}")
        
        return data["results"]

async def get_earnings_data(symbol: str) -> Dict[str, Any]:
    """
    Get earnings data for a symbol using Alpha Vantage API.
    """
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "EARNINGS",
        "symbol": symbol,
        "apikey": settings.ALPHA_VANTAGE_API_KEY
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "quarterlyEarnings" not in data:
            raise ValueError(f"Invalid response from Alpha Vantage: {data}")
        
        return data

async def get_financial_metrics(symbol: str) -> Dict[str, Any]:
    """
    Get financial metrics for a symbol using Alpha Vantage API.
    """
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "OVERVIEW",
        "symbol": symbol,
        "apikey": settings.ALPHA_VANTAGE_API_KEY
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "Symbol" not in data:
            raise ValueError(f"Invalid response from Alpha Vantage: {data}")
        
        return data

async def polygon_websocket_client():
    """
    WebSocket client for Polygon.io real-time data.
    """
    auth_message = {
        "action": "auth",
        "params": settings.POLYGON_API_KEY
    }
    
    # Subscribe to all Mag7 stocks
    subscribe_message = {
        "action": "subscribe",
        "params": []
    }
    
    # Add trade and quote channels for each Mag7 stock
    for symbol in settings.MAG7_SYMBOLS:
        subscribe_message["params"].append(f"T.{symbol}")  # Trades
        subscribe_message["params"].append(f"Q.{symbol}")  # Quotes
    
    # Add trade and quote channels for ETFs and indices
    for symbol in settings.ETF_SYMBOLS + settings.INDEX_SYMBOLS:
        subscribe_message["params"].append(f"T.{symbol}")  # Trades
        subscribe_message["params"].append(f"Q.{symbol}")  # Quotes
    
    try:
        async with websockets.connect(POLYGON_WS_URL) as websocket:
            # Authenticate
            await websocket.send(json.dumps(auth_message))
            auth_response = await websocket.recv()
            logger.info(f"Authentication response: {auth_response}")
            
            # Subscribe to channels
            await websocket.send(json.dumps(subscribe_message))
            subscribe_response = await websocket.recv()
            logger.info(f"Subscription response: {subscribe_response}")
            
            # Process incoming messages
            while True:
                message = await websocket.recv()
                await process_websocket_message(message)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        # Reconnect after a delay
        await asyncio.sleep(5)
        asyncio.create_task(polygon_websocket_client())

async def process_websocket_message(message: str):
    """
    Process incoming WebSocket messages from Polygon.io.
    """
    try:
        data = json.loads(message)
        
        # Skip status messages
        if isinstance(data, dict) and "status" in data:
            return
        
        # Process each event in the message
        for event in data:
            event_type = event.get("ev")
            
            if event_type == "T":  # Trade
                await process_trade_event(event)
            elif event_type == "Q":  # Quote
                await process_quote_event(event)
    except Exception as e:
        logger.error(f"Error processing WebSocket message: {e}")

async def process_trade_event(event: Dict[str, Any]):
    """
    Process trade event from Polygon.io WebSocket.
    """
    try:
        symbol = event.get("sym")
        price = event.get("p")
        size = event.get("s")
        timestamp = datetime.fromtimestamp(event.get("t") / 1000)
        
        # Store in InfluxDB
        point = Point("trades") \
            .tag("symbol", symbol) \
            .field("price", price) \
            .field("size", size) \
            .time(timestamp)
        
        write_api.write(bucket=settings.INFLUXDB_BUCKET, record=point)
        
        # Update latest price in database
        db = SessionLocal()
        try:
            instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
            if instrument:
                # Check if we already have a price for this timestamp
                existing_price = db.query(StockPrice).filter(
                    StockPrice.instrument_id == instrument.id,
                    StockPrice.timestamp == timestamp.replace(microsecond=0)
                ).first()
                
                if not existing_price:
                    # Create new price record
                    new_price = StockPrice(
                        instrument_id=instrument.id,
                        timestamp=timestamp,
                        close=price,
                        volume=size
                    )
                    db.add(new_price)
                    db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error processing trade event: {e}")

async def process_quote_event(event: Dict[str, Any]):
    """
    Process quote event from Polygon.io WebSocket.
    """
    try:
        symbol = event.get("sym")
        bid_price = event.get("bp")
        bid_size = event.get("bs")
        ask_price = event.get("ap")
        ask_size = event.get("as")
        timestamp = datetime.fromtimestamp(event.get("t") / 1000)
        
        # Store in InfluxDB
        point = Point("quotes") \
            .tag("symbol", symbol) \
            .field("bid_price", bid_price) \
            .field("bid_size", bid_size) \
            .field("ask_price", ask_price) \
            .field("ask_size", ask_size) \
            .time(timestamp)
        
        write_api.write(bucket=settings.INFLUXDB_BUCKET, record=point)
    except Exception as e:
        logger.error(f"Error processing quote event: {e}")

async def fetch_and_store_option_data():
    """
    Fetch and store option data for all Mag7 stocks.
    """
    db = SessionLocal()
    try:
        for symbol in settings.MAG7_SYMBOLS:
            try:
                # Get instrument
                instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
                if not instrument:
                    logger.warning(f"Instrument {symbol} not found in database")
                    continue
                
                # Get option chain
                options = await get_option_chain(symbol)
                
                for option_data in options:
                    try:
                        option_symbol = option_data.get("ticker")
                        expiration_date = datetime.strptime(option_data.get("expiration_date"), "%Y-%m-%d")
                        strike_price = float(option_data.get("strike_price"))
                        option_type = "call" if option_data.get("contract_type") == "call" else "put"
                        
                        # Check if option already exists
                        existing_option = db.query(Option).filter(Option.symbol == option_symbol).first()
                        
                        if not existing_option:
                            # Create new option
                            new_option = Option(
                                instrument_id=instrument.id,
                                symbol=option_symbol,
                                expiration_date=expiration_date,
                                strike_price=strike_price,
                                option_type=option_type
                            )
                            db.add(new_option)
                            db.commit()
                            
                            logger.info(f"Added new option: {option_symbol}")
                    except Exception as e:
                        logger.error(f"Error processing option {option_data.get('ticker')}: {e}")
                        continue
            except Exception as e:
                logger.error(f"Error fetching options for {symbol}: {e}")
                continue
    finally:
        db.close()

async def fetch_and_store_earnings_data():
    """
    Fetch and store earnings data for all Mag7 stocks.
    """
    db = SessionLocal()
    try:
        for symbol in settings.MAG7_SYMBOLS:
            try:
                # Get instrument
                instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
                if not instrument:
                    logger.warning(f"Instrument {symbol} not found in database")
                    continue
                
                # Get earnings data
                earnings_data = await get_earnings_data(symbol)
                
                if "quarterlyEarnings" in earnings_data:
                    for quarter in earnings_data["quarterlyEarnings"]:
                        try:
                            fiscal_quarter = quarter.get("fiscalDateEnding")
                            reported_date = quarter.get("reportedDate")
                            reported_eps = quarter.get("reportedEPS")
                            estimated_eps = quarter.get("estimatedEPS")
                            surprise = quarter.get("surprise")
                            surprise_percentage = quarter.get("surprisePercentage")
                            
                            if not reported_date:
                                continue
                            
                            earnings_date = datetime.strptime(reported_date, "%Y-%m-%d")
                            
                            # Check if earnings data already exists
                            existing_earnings = db.query(EarningsData).filter(
                                EarningsData.instrument_id == instrument.id,
                                EarningsData.earnings_date == earnings_date
                            ).first()
                            
                            if not existing_earnings:
                                # Create new earnings data
                                new_earnings = EarningsData(
                                    instrument_id=instrument.id,
                                    earnings_date=earnings_date,
                                    fiscal_quarter=fiscal_quarter,
                                    eps_actual=float(reported_eps) if reported_eps else None,
                                    eps_estimate=float(estimated_eps) if estimated_eps else None,
                                    surprise_percentage=float(surprise_percentage) if surprise_percentage else None
                                )
                                db.add(new_earnings)
                                db.commit()
                                
                                logger.info(f"Added new earnings data for {symbol}: {fiscal_quarter}")
                        except Exception as e:
                            logger.error(f"Error processing earnings data for {symbol}: {e}")
                            continue
            except Exception as e:
                logger.error(f"Error fetching earnings data for {symbol}: {e}")
                continue
    finally:
        db.close()

async def fetch_and_store_financial_metrics():
    """
    Fetch and store financial metrics for all Mag7 stocks.
    """
    db = SessionLocal()
    try:
        for symbol in settings.MAG7_SYMBOLS:
            try:
                # Get instrument
                instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
                if not instrument:
                    logger.warning(f"Instrument {symbol} not found in database")
                    continue
                
                # Get financial metrics
                metrics = await get_financial_metrics(symbol)
                
                # Process key metrics
                today = datetime.utcnow().date()
                
                metrics_to_store = [
                    {"metric_type": "pe_ratio", "value": metrics.get("PERatio")},
                    {"metric_type": "peg_ratio", "value": metrics.get("PEGRatio")},
                    {"metric_type": "eps", "value": metrics.get("EPS")},
                    {"metric_type": "revenue_ttm", "value": metrics.get("RevenueTTM")},
                    {"metric_type": "profit_margin", "value": metrics.get("ProfitMargin")},
                    {"metric_type": "market_cap", "value": metrics.get("MarketCapitalization")},
                    {"metric_type": "beta", "value": metrics.get("Beta")},
                    {"metric_type": "dividend_yield", "value": metrics.get("DividendYield")}
                ]
                
                for metric_data in metrics_to_store:
                    try:
                        metric_type = metric_data["metric_type"]
                        value = metric_data["value"]
                        
                        if not value or value == "None":
                            continue
                        
                        # Convert to float
                        value = float(value)
                        
                        # Check if metric already exists for today
                        existing_metric = db.query(FinancialMetric).filter(
                            FinancialMetric.instrument_id == instrument.id,
                            FinancialMetric.metric_type == metric_type,
                            FinancialMetric.date == today
                        ).first()
                        
                        if not existing_metric:
                            # Create new metric
                            new_metric = FinancialMetric(
                                instrument_id=instrument.id,
                                date=today,
                                metric_type=metric_type,
                                value=value
                            )
                            db.add(new_metric)
                            db.commit()
                            
                            logger.info(f"Added new financial metric for {symbol}: {metric_type}={value}")
                    except Exception as e:
                        logger.error(f"Error processing financial metric {metric_type} for {symbol}: {e}")
                        continue
            except Exception as e:
                logger.error(f"Error fetching financial metrics for {symbol}: {e}")
                continue
    finally:
        db.close()

async def data_feed_main():
    """
    Main function for data feed service.
    """
    logger.info("Starting data feed service...")
    
    # Start WebSocket client
    asyncio.create_task(polygon_websocket_client())
    
    # Schedule periodic tasks
    while True:
        try:
            # Fetch and store option data every hour
            await fetch_and_store_option_data()
            
            # Fetch and store earnings data once a day
            await fetch_and_store_earnings_data()
            
            # Fetch and store financial metrics once a day
            await fetch_and_store_financial_metrics()
            
            # Wait for next cycle
            await asyncio.sleep(3600)  # 1 hour
        except Exception as e:
            logger.error(f"Error in data feed main loop: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    asyncio.run(data_feed_main())

