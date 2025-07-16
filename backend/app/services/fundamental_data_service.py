import os
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, SessionLocal
from app.models.market_data import (
    Instrument, EarningsData, FinancialMetric, AnalystRating
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class FundamentalDataService:
    """Service for fetching and processing fundamental data for Mag7 stocks."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def fetch_earnings_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch earnings data for a symbol using Alpha Vantage API.
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
    
    async def fetch_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch company overview data for a symbol using Alpha Vantage API.
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
    
    async def fetch_income_statement(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch income statement data for a symbol using Alpha Vantage API.
        """
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "INCOME_STATEMENT",
            "symbol": symbol,
            "apikey": settings.ALPHA_VANTAGE_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "quarterlyReports" not in data:
                raise ValueError(f"Invalid response from Alpha Vantage: {data}")
            
            return data
    
    async def fetch_balance_sheet(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch balance sheet data for a symbol using Alpha Vantage API.
        """
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "BALANCE_SHEET",
            "symbol": symbol,
            "apikey": settings.ALPHA_VANTAGE_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "quarterlyReports" not in data:
                raise ValueError(f"Invalid response from Alpha Vantage: {data}")
            
            return data
    
    async def fetch_cash_flow(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch cash flow data for a symbol using Alpha Vantage API.
        """
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "CASH_FLOW",
            "symbol": symbol,
            "apikey": settings.ALPHA_VANTAGE_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "quarterlyReports" not in data:
                raise ValueError(f"Invalid response from Alpha Vantage: {data}")
            
            return data
    
    async def fetch_analyst_ratings(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch analyst ratings for a symbol using a third-party API.
        
        Note: This is a placeholder. In a real implementation, you would use a
        service like Benzinga, Refinitiv, or Bloomberg for analyst ratings.
        """
        # Placeholder for analyst ratings API
        # In a real implementation, you would use a service like Benzinga, Refinitiv, or Bloomberg
        
        # For now, return mock data
        return [
            {
                "analyst_firm": "Morgan Stanley",
                "rating_date": datetime.utcnow() - timedelta(days=5),
                "rating": "Overweight",
                "price_target": 250.0,
                "previous_rating": "Equal-weight",
                "previous_price_target": 230.0
            },
            {
                "analyst_firm": "Goldman Sachs",
                "rating_date": datetime.utcnow() - timedelta(days=10),
                "rating": "Buy",
                "price_target": 260.0,
                "previous_rating": "Buy",
                "previous_price_target": 245.0
            },
            {
                "analyst_firm": "JP Morgan",
                "rating_date": datetime.utcnow() - timedelta(days=15),
                "rating": "Neutral",
                "price_target": 235.0,
                "previous_rating": "Neutral",
                "previous_price_target": 225.0
            }
        ]
    
    async def process_earnings_data(self, instrument: Instrument, data: Dict[str, Any]):
        """
        Process and store earnings data for an instrument.
        """
        try:
            if "quarterlyEarnings" in data:
                for quarter in data["quarterlyEarnings"]:
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
                        existing_earnings = self.db.query(EarningsData).filter(
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
                            self.db.add(new_earnings)
                            self.db.commit()
                            
                            logger.info(f"Added new earnings data for {instrument.symbol}: {fiscal_quarter}")
                    except Exception as e:
                        logger.error(f"Error processing earnings data for {instrument.symbol}: {e}")
                        continue
            
            # Update instrument with next earnings date
            if "quarterlyEarnings" in data and data["quarterlyEarnings"]:
                # Sort by fiscal date ending (descending)
                sorted_earnings = sorted(
                    data["quarterlyEarnings"],
                    key=lambda x: x.get("fiscalDateEnding", ""),
                    reverse=True
                )
                
                # Get the most recent fiscal quarter
                most_recent = sorted_earnings[0]
                fiscal_date = most_recent.get("fiscalDateEnding")
                
                if fiscal_date:
                    # Estimate next earnings date (approximately 3 months after the most recent)
                    fiscal_date_dt = datetime.strptime(fiscal_date, "%Y-%m-%d")
                    next_earnings_date = fiscal_date_dt + timedelta(days=90)
                    
                    # Update instrument
                    instrument.earnings_schedule = {
                        "last_date": fiscal_date,
                        "next_date": next_earnings_date.isoformat()
                    }
                    self.db.commit()
                    
                    logger.info(f"Updated earnings schedule for {instrument.symbol}")
        
        except Exception as e:
            logger.error(f"Error processing earnings data for {instrument.symbol}: {e}")
            self.db.rollback()
    
    async def process_company_overview(self, instrument: Instrument, data: Dict[str, Any]):
        """
        Process and store company overview data for an instrument.
        """
        try:
            today = datetime.utcnow().date()
            
            metrics_to_store = [
                {"metric_type": "pe_ratio", "value": data.get("PERatio")},
                {"metric_type": "peg_ratio", "value": data.get("PEGRatio")},
                {"metric_type": "eps", "value": data.get("EPS")},
                {"metric_type": "revenue_ttm", "value": data.get("RevenueTTM")},
                {"metric_type": "profit_margin", "value": data.get("ProfitMargin")},
                {"metric_type": "market_cap", "value": data.get("MarketCapitalization")},
                {"metric_type": "beta", "value": data.get("Beta")},
                {"metric_type": "dividend_yield", "value": data.get("DividendYield")},
                {"metric_type": "52_week_high", "value": data.get("52WeekHigh")},
                {"metric_type": "52_week_low", "value": data.get("52WeekLow")},
                {"metric_type": "50_day_ma", "value": data.get("50DayMovingAverage")},
                {"metric_type": "200_day_ma", "value": data.get("200DayMovingAverage")},
                {"metric_type": "shares_outstanding", "value": data.get("SharesOutstanding")},
                {"metric_type": "book_value", "value": data.get("BookValue")},
                {"metric_type": "price_to_book", "value": data.get("PriceToBookRatio")}
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
                    existing_metric = self.db.query(FinancialMetric).filter(
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
                        self.db.add(new_metric)
                        self.db.commit()
                        
                        logger.info(f"Added new financial metric for {instrument.symbol}: {metric_type}={value}")
                except Exception as e:
                    logger.error(f"Error processing financial metric {metric_type} for {instrument.symbol}: {e}")
                    continue
            
            # Update instrument with sector and description
            instrument.sector = data.get("Sector")
            instrument.description = data.get("Description")
            self.db.commit()
            
            logger.info(f"Updated instrument details for {instrument.symbol}")
        
        except Exception as e:
            logger.error(f"Error processing company overview for {instrument.symbol}: {e}")
            self.db.rollback()
    
    async def process_analyst_ratings(self, instrument: Instrument, ratings: List[Dict[str, Any]]):
        """
        Process and store analyst ratings for an instrument.
        """
        try:
            for rating_data in ratings:
                try:
                    analyst_firm = rating_data.get("analyst_firm")
                    rating_date = rating_data.get("rating_date")
                    rating = rating_data.get("rating")
                    price_target = rating_data.get("price_target")
                    previous_rating = rating_data.get("previous_rating")
                    previous_price_target = rating_data.get("previous_price_target")
                    
                    # Check if rating already exists
                    existing_rating = self.db.query(AnalystRating).filter(
                        AnalystRating.instrument_id == instrument.id,
                        AnalystRating.analyst_firm == analyst_firm,
                        AnalystRating.rating_date == rating_date
                    ).first()
                    
                    if not existing_rating:
                        # Create new rating
                        new_rating = AnalystRating(
                            instrument_id=instrument.id,
                            analyst_firm=analyst_firm,
                            rating_date=rating_date,
                            rating=rating,
                            price_target=price_target,
                            previous_rating=previous_rating,
                            previous_price_target=previous_price_target
                        )
                        self.db.add(new_rating)
                        self.db.commit()
                        
                        logger.info(f"Added new analyst rating for {instrument.symbol}: {analyst_firm} - {rating}")
                except Exception as e:
                    logger.error(f"Error processing analyst rating for {instrument.symbol}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error processing analyst ratings for {instrument.symbol}: {e}")
            self.db.rollback()
    
    async def update_fundamental_data(self):
        """
        Update fundamental data for all Mag7 stocks.
        """
        for symbol in settings.MAG7_SYMBOLS:
            try:
                # Get instrument
                instrument = self.db.query(Instrument).filter(Instrument.symbol == symbol).first()
                if not instrument:
                    logger.warning(f"Instrument {symbol} not found in database")
                    continue
                
                # Fetch and process earnings data
                earnings_data = await self.fetch_earnings_data(symbol)
                await self.process_earnings_data(instrument, earnings_data)
                
                # Fetch and process company overview
                company_overview = await self.fetch_company_overview(symbol)
                await self.process_company_overview(instrument, company_overview)
                
                # Fetch and process analyst ratings
                analyst_ratings = await self.fetch_analyst_ratings(symbol)
                await self.process_analyst_ratings(instrument, analyst_ratings)
                
                # Wait to avoid API rate limits
                await asyncio.sleep(1)
            
            except Exception as e:
                logger.error(f"Error updating fundamental data for {symbol}: {e}")
                continue

async def fundamental_data_service_main():
    """Main function for fundamental data service."""
    logger.info("Starting fundamental data service...")
    
    while True:
        try:
            # Create database session
            db = SessionLocal()
            
            try:
                # Create fundamental data service
                service = FundamentalDataService(db)
                
                # Update fundamental data
                await service.update_fundamental_data()
                
                logger.info("Fundamental data update completed successfully")
            finally:
                db.close()
            
            # Wait for next cycle (daily update)
            await asyncio.sleep(24 * 60 * 60)  # 24 hours
        
        except Exception as e:
            logger.error(f"Error in fundamental data service main loop: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    asyncio.run(fundamental_data_service_main())

