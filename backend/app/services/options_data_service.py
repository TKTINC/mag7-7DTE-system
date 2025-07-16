import os
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import httpx
from sqlalchemy.orm import Session
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from app.config import settings
from app.database import get_db, SessionLocal
from app.models.market_data import (
    Instrument, Option, OptionPriceData, VolatilityData
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

class OptionsDataService:
    """Service for fetching and processing options data for Mag7 stocks."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def fetch_option_chain(self, symbol: str, expiration_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Fetch option chain for a symbol using Polygon.io REST API.
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
    
    async def fetch_option_price(self, option_symbol: str) -> Dict[str, Any]:
        """
        Fetch option price data for an option symbol using Polygon.io REST API.
        """
        url = f"https://api.polygon.io/v2/last/trade/{option_symbol}"
        params = {
            "apiKey": settings.POLYGON_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "results" not in data:
                raise ValueError(f"Invalid response from Polygon.io: {data}")
            
            return data["results"]
    
    async def fetch_option_quotes(self, option_symbol: str) -> Dict[str, Any]:
        """
        Fetch option quotes data for an option symbol using Polygon.io REST API.
        """
        url = f"https://api.polygon.io/v3/quotes/{option_symbol}"
        params = {
            "limit": 1,
            "apiKey": settings.POLYGON_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "results" not in data:
                raise ValueError(f"Invalid response from Polygon.io: {data}")
            
            return data["results"][0] if data["results"] else {}
    
    async def fetch_historical_option_prices(self, option_symbol: str, from_date: datetime, to_date: datetime) -> List[Dict[str, Any]]:
        """
        Fetch historical option prices for an option symbol using Polygon.io REST API.
        """
        # Format dates as YYYY-MM-DD
        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")
        
        url = f"https://api.polygon.io/v2/aggs/ticker/{option_symbol}/range/1/day/{from_str}/{to_str}"
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
    
    async def calculate_implied_volatility(self, option_data: Dict[str, Any], stock_price: float) -> float:
        """
        Calculate implied volatility for an option using the Black-Scholes model.
        
        Note: This is a simplified implementation. In a real-world scenario,
        you would use a more sophisticated model or a third-party service.
        """
        # Placeholder for implied volatility calculation
        # In a real implementation, you would use a proper options pricing model
        
        # For now, return a random value between 0.2 and 0.6
        return np.random.uniform(0.2, 0.6)
    
    async def calculate_greeks(self, option_data: Dict[str, Any], stock_price: float, implied_volatility: float) -> Dict[str, float]:
        """
        Calculate option Greeks using the Black-Scholes model.
        
        Note: This is a simplified implementation. In a real-world scenario,
        you would use a more sophisticated model or a third-party service.
        """
        # Placeholder for Greeks calculation
        # In a real implementation, you would use a proper options pricing model
        
        # For now, return random values
        return {
            "delta": np.random.uniform(-1.0, 1.0),
            "gamma": np.random.uniform(0.0, 0.1),
            "theta": np.random.uniform(-1.0, 0.0),
            "vega": np.random.uniform(0.0, 1.0)
        }
    
    async def process_option_chain(self, instrument: Instrument, option_chain: List[Dict[str, Any]]):
        """
        Process and store option chain data for an instrument.
        """
        try:
            for option_data in option_chain:
                try:
                    option_symbol = option_data.get("ticker")
                    expiration_date = datetime.strptime(option_data.get("expiration_date"), "%Y-%m-%d")
                    strike_price = float(option_data.get("strike_price"))
                    option_type = "call" if option_data.get("contract_type") == "call" else "put"
                    
                    # Check if option already exists
                    existing_option = self.db.query(Option).filter(Option.symbol == option_symbol).first()
                    
                    if not existing_option:
                        # Create new option
                        new_option = Option(
                            instrument_id=instrument.id,
                            symbol=option_symbol,
                            expiration_date=expiration_date,
                            strike_price=strike_price,
                            option_type=option_type
                        )
                        self.db.add(new_option)
                        self.db.commit()
                        
                        logger.info(f"Added new option: {option_symbol}")
                        
                        # Use the new option for price data
                        option = new_option
                    else:
                        option = existing_option
                    
                    # Fetch option price data
                    try:
                        price_data = await self.fetch_option_price(option_symbol)
                        quote_data = await self.fetch_option_quotes(option_symbol)
                        
                        # Get current stock price
                        stock_price = self.db.query(Instrument).filter(
                            Instrument.id == instrument.id
                        ).first().last_price
                        
                        # Calculate implied volatility and Greeks
                        implied_volatility = await self.calculate_implied_volatility(option_data, stock_price)
                        greeks = await self.calculate_greeks(option_data, stock_price, implied_volatility)
                        
                        # Create option price data
                        timestamp = datetime.fromtimestamp(price_data.get("t") / 1000)
                        
                        # Check if price data already exists for this timestamp
                        existing_price = self.db.query(OptionPriceData).filter(
                            OptionPriceData.option_id == option.id,
                            OptionPriceData.timestamp == timestamp.replace(microsecond=0)
                        ).first()
                        
                        if not existing_price:
                            # Create new price data
                            new_price = OptionPriceData(
                                option_id=option.id,
                                timestamp=timestamp,
                                bid=quote_data.get("bid_price") if quote_data else None,
                                ask=quote_data.get("ask_price") if quote_data else None,
                                last=price_data.get("p"),
                                volume=price_data.get("s"),
                                open_interest=None,  # Not available from this API
                                implied_volatility=implied_volatility,
                                delta=greeks.get("delta"),
                                gamma=greeks.get("gamma"),
                                theta=greeks.get("theta"),
                                vega=greeks.get("vega")
                            )
                            self.db.add(new_price)
                            self.db.commit()
                            
                            logger.info(f"Added new option price data for {option_symbol}")
                            
                            # Store in InfluxDB for time-series analysis
                            point = Point("option_prices") \
                                .tag("symbol", option_symbol) \
                                .tag("option_type", option_type) \
                                .tag("strike_price", str(strike_price)) \
                                .field("bid", quote_data.get("bid_price") if quote_data else None) \
                                .field("ask", quote_data.get("ask_price") if quote_data else None) \
                                .field("last", price_data.get("p")) \
                                .field("volume", price_data.get("s")) \
                                .field("implied_volatility", implied_volatility) \
                                .field("delta", greeks.get("delta")) \
                                .field("gamma", greeks.get("gamma")) \
                                .field("theta", greeks.get("theta")) \
                                .field("vega", greeks.get("vega")) \
                                .time(timestamp)
                            
                            write_api.write(bucket=settings.INFLUXDB_BUCKET, record=point)
                    
                    except Exception as e:
                        logger.error(f"Error fetching price data for {option_symbol}: {e}")
                        continue
                
                except Exception as e:
                    logger.error(f"Error processing option {option_data.get('ticker')}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error processing option chain for {instrument.symbol}: {e}")
            self.db.rollback()
    
    async def calculate_volatility_metrics(self, instrument: Instrument):
        """
        Calculate and store volatility metrics for an instrument.
        """
        try:
            # Get all options for this instrument
            options = self.db.query(Option).filter(
                Option.instrument_id == instrument.id,
                Option.expiration_date >= datetime.utcnow().date()
            ).all()
            
            if not options:
                logger.warning(f"No options found for {instrument.symbol}")
                return
            
            # Calculate average implied volatility
            iv_values = []
            for option in options:
                # Get latest price data
                price_data = self.db.query(OptionPriceData).filter(
                    OptionPriceData.option_id == option.id
                ).order_by(OptionPriceData.timestamp.desc()).first()
                
                if price_data and price_data.implied_volatility:
                    iv_values.append(price_data.implied_volatility)
            
            if not iv_values:
                logger.warning(f"No implied volatility data found for {instrument.symbol}")
                return
            
            # Calculate metrics
            iv_avg = sum(iv_values) / len(iv_values)
            iv_min = min(iv_values)
            iv_max = max(iv_values)
            
            # Calculate IV percentile and rank
            # For this, we need historical IV data
            # For now, use placeholder values
            iv_percentile = np.random.uniform(0, 100)
            iv_rank = np.random.uniform(0, 100)
            
            # Create or update volatility data
            today = datetime.utcnow().date()
            
            existing_data = self.db.query(VolatilityData).filter(
                VolatilityData.instrument_id == instrument.id,
                VolatilityData.date == today
            ).first()
            
            if not existing_data:
                # Create new volatility data
                new_data = VolatilityData(
                    instrument_id=instrument.id,
                    date=today,
                    implied_volatility_avg=iv_avg,
                    implied_volatility_min=iv_min,
                    implied_volatility_max=iv_max,
                    iv_percentile=iv_percentile,
                    iv_rank=iv_rank
                )
                self.db.add(new_data)
                self.db.commit()
                
                logger.info(f"Added new volatility data for {instrument.symbol}")
            else:
                # Update existing volatility data
                existing_data.implied_volatility_avg = iv_avg
                existing_data.implied_volatility_min = iv_min
                existing_data.implied_volatility_max = iv_max
                existing_data.iv_percentile = iv_percentile
                existing_data.iv_rank = iv_rank
                self.db.commit()
                
                logger.info(f"Updated volatility data for {instrument.symbol}")
        
        except Exception as e:
            logger.error(f"Error calculating volatility metrics for {instrument.symbol}: {e}")
            self.db.rollback()
    
    async def update_options_data(self):
        """
        Update options data for all Mag7 stocks.
        """
        for symbol in settings.MAG7_SYMBOLS:
            try:
                # Get instrument
                instrument = self.db.query(Instrument).filter(Instrument.symbol == symbol).first()
                if not instrument:
                    logger.warning(f"Instrument {symbol} not found in database")
                    continue
                
                # Find expiration dates around 7 DTE
                today = datetime.utcnow().date()
                target_dates = [
                    today + timedelta(days=7),  # 7 DTE
                    today + timedelta(days=14),  # 14 DTE (for comparison)
                    today + timedelta(days=30)   # 30 DTE (for comparison)
                ]
                
                for target_date in target_dates:
                    # Fetch option chain
                    option_chain = await self.fetch_option_chain(symbol, target_date)
                    
                    # Process option chain
                    await self.process_option_chain(instrument, option_chain)
                
                # Calculate volatility metrics
                await self.calculate_volatility_metrics(instrument)
                
                # Wait to avoid API rate limits
                await asyncio.sleep(1)
            
            except Exception as e:
                logger.error(f"Error updating options data for {symbol}: {e}")
                continue

async def options_data_service_main():
    """Main function for options data service."""
    logger.info("Starting options data service...")
    
    while True:
        try:
            # Create database session
            db = SessionLocal()
            
            try:
                # Create options data service
                service = OptionsDataService(db)
                
                # Update options data
                await service.update_options_data()
                
                logger.info("Options data update completed successfully")
            finally:
                db.close()
            
            # Wait for next cycle (hourly update)
            await asyncio.sleep(60 * 60)  # 1 hour
        
        except Exception as e:
            logger.error(f"Error in options data service main loop: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    asyncio.run(options_data_service_main())

