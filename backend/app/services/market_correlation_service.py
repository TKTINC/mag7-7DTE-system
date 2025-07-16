import os
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from influxdb_client import InfluxDBClient
from influxdb_client.client.flux_table import FluxTable

from app.config import settings
from app.database import get_db, SessionLocal
from app.models.market_data import (
    Instrument, StockPrice, CorrelationData
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
query_api = influxdb_client.query_api()

class MarketCorrelationService:
    """Service for calculating and analyzing correlations between Mag7 stocks."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_historical_prices(self, symbols: List[str], days: int = 30) -> pd.DataFrame:
        """
        Get historical prices for a list of symbols.
        
        Returns a DataFrame with dates as index and symbols as columns.
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Create empty DataFrame
        df = pd.DataFrame()
        
        for symbol in symbols:
            # Get instrument
            instrument = self.db.query(Instrument).filter(Instrument.symbol == symbol).first()
            if not instrument:
                logger.warning(f"Instrument {symbol} not found in database")
                continue
            
            # Get historical prices
            prices = self.db.query(StockPrice).filter(
                StockPrice.instrument_id == instrument.id,
                StockPrice.timestamp >= start_date,
                StockPrice.timestamp <= end_date
            ).order_by(StockPrice.timestamp).all()
            
            if not prices:
                logger.warning(f"No price data found for {symbol}")
                continue
            
            # Convert to DataFrame
            symbol_df = pd.DataFrame([{
                'timestamp': p.timestamp.date(),
                'close': p.close
            } for p in prices])
            
            # Set timestamp as index
            symbol_df.set_index('timestamp', inplace=True)
            
            # Add to main DataFrame
            df[symbol] = symbol_df['close']
        
        return df
    
    async def calculate_correlation_matrix(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate correlation matrix from price DataFrame.
        """
        # Calculate returns
        returns_df = price_df.pct_change().dropna()
        
        # Calculate correlation matrix
        corr_matrix = returns_df.corr()
        
        return corr_matrix
    
    async def calculate_beta(self, price_df: pd.DataFrame, market_symbol: str = 'SPY') -> Dict[str, float]:
        """
        Calculate beta for each symbol relative to a market index.
        """
        # Calculate returns
        returns_df = price_df.pct_change().dropna()
        
        # Check if market symbol exists in DataFrame
        if market_symbol not in returns_df.columns:
            logger.warning(f"Market symbol {market_symbol} not found in price data")
            return {}
        
        # Calculate beta for each symbol
        betas = {}
        market_returns = returns_df[market_symbol]
        
        for symbol in returns_df.columns:
            if symbol == market_symbol:
                continue
            
            # Calculate beta
            cov = returns_df[symbol].cov(market_returns)
            var = market_returns.var()
            beta = cov / var
            
            betas[symbol] = beta
        
        return betas
    
    async def calculate_rolling_correlation(self, price_df: pd.DataFrame, window: int = 10) -> Dict[str, pd.DataFrame]:
        """
        Calculate rolling correlation for each pair of symbols.
        """
        # Calculate returns
        returns_df = price_df.pct_change().dropna()
        
        # Calculate rolling correlation for each pair
        rolling_corr = {}
        
        for i, symbol1 in enumerate(returns_df.columns):
            for j, symbol2 in enumerate(returns_df.columns):
                if i >= j:  # Only calculate for unique pairs
                    continue
                
                # Calculate rolling correlation
                pair_corr = returns_df[symbol1].rolling(window=window).corr(returns_df[symbol2])
                
                # Store in dictionary
                pair_name = f"{symbol1}_{symbol2}"
                rolling_corr[pair_name] = pair_corr
        
        return rolling_corr
    
    async def identify_correlation_changes(self, rolling_corr: Dict[str, pd.DataFrame], threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Identify significant changes in correlation.
        """
        changes = []
        
        for pair_name, corr_series in rolling_corr.items():
            # Skip if not enough data
            if len(corr_series) < 5:
                continue
            
            # Calculate change in correlation
            recent_corr = corr_series.iloc[-1]
            prev_corr = corr_series.iloc[-5]
            
            if abs(recent_corr - prev_corr) > threshold:
                # Significant change detected
                symbols = pair_name.split('_')
                
                changes.append({
                    'pair': pair_name,
                    'symbol1': symbols[0],
                    'symbol2': symbols[1],
                    'recent_correlation': recent_corr,
                    'previous_correlation': prev_corr,
                    'change': recent_corr - prev_corr
                })
        
        return changes
    
    async def store_correlation_data(self, corr_matrix: pd.DataFrame, betas: Dict[str, float]):
        """
        Store correlation data in the database.
        """
        try:
            today = datetime.utcnow().date()
            
            # Store correlation matrix
            for i, symbol1 in enumerate(corr_matrix.columns):
                instrument1 = self.db.query(Instrument).filter(Instrument.symbol == symbol1).first()
                if not instrument1:
                    continue
                
                for j, symbol2 in enumerate(corr_matrix.columns):
                    if i >= j:  # Only store unique pairs
                        continue
                    
                    instrument2 = self.db.query(Instrument).filter(Instrument.symbol == symbol2).first()
                    if not instrument2:
                        continue
                    
                    # Get correlation value
                    corr_value = corr_matrix.loc[symbol1, symbol2]
                    
                    # Check if correlation data already exists
                    existing_corr = self.db.query(CorrelationData).filter(
                        CorrelationData.instrument1_id == instrument1.id,
                        CorrelationData.instrument2_id == instrument2.id,
                        CorrelationData.date == today
                    ).first()
                    
                    if not existing_corr:
                        # Create new correlation data
                        new_corr = CorrelationData(
                            instrument1_id=instrument1.id,
                            instrument2_id=instrument2.id,
                            date=today,
                            correlation=corr_value
                        )
                        self.db.add(new_corr)
                        self.db.commit()
                        
                        logger.info(f"Added new correlation data for {symbol1}-{symbol2}: {corr_value:.4f}")
                    else:
                        # Update existing correlation data
                        existing_corr.correlation = corr_value
                        self.db.commit()
                        
                        logger.info(f"Updated correlation data for {symbol1}-{symbol2}: {corr_value:.4f}")
            
            # Store beta values
            for symbol, beta in betas.items():
                instrument = self.db.query(Instrument).filter(Instrument.symbol == symbol).first()
                if not instrument:
                    continue
                
                # Update instrument with beta
                instrument.beta = beta
                self.db.commit()
                
                logger.info(f"Updated beta for {symbol}: {beta:.4f}")
        
        except Exception as e:
            logger.error(f"Error storing correlation data: {e}")
            self.db.rollback()
    
    async def analyze_sector_correlations(self) -> Dict[str, float]:
        """
        Analyze correlations between sectors.
        """
        # Get all instruments with sector information
        instruments = self.db.query(Instrument).filter(Instrument.sector != None).all()
        
        # Group instruments by sector
        sectors = {}
        for instrument in instruments:
            if instrument.sector not in sectors:
                sectors[instrument.sector] = []
            
            sectors[instrument.sector].append(instrument.symbol)
        
        # Get historical prices for all symbols
        all_symbols = [instrument.symbol for instrument in instruments]
        price_df = await self.get_historical_prices(all_symbols)
        
        # Calculate returns
        returns_df = price_df.pct_change().dropna()
        
        # Calculate sector returns
        sector_returns = {}
        for sector, symbols in sectors.items():
            # Skip if no symbols in this sector
            if not symbols or not all(symbol in returns_df.columns for symbol in symbols):
                continue
            
            # Calculate average return for sector
            sector_returns[sector] = returns_df[symbols].mean(axis=1)
        
        # Convert to DataFrame
        sector_returns_df = pd.DataFrame(sector_returns)
        
        # Calculate correlation matrix
        sector_corr = sector_returns_df.corr()
        
        # Convert to dictionary
        sector_corr_dict = {}
        for i, sector1 in enumerate(sector_corr.columns):
            for j, sector2 in enumerate(sector_corr.columns):
                if i >= j:  # Only include unique pairs
                    continue
                
                pair_name = f"{sector1}_{sector2}"
                sector_corr_dict[pair_name] = sector_corr.loc[sector1, sector2]
        
        return sector_corr_dict
    
    async def analyze_mag7_correlations(self) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """
        Analyze correlations between Mag7 stocks.
        """
        # Get historical prices for Mag7 stocks
        price_df = await self.get_historical_prices(settings.MAG7_SYMBOLS)
        
        # Calculate correlation matrix
        corr_matrix = await self.calculate_correlation_matrix(price_df)
        
        # Calculate beta values
        betas = await self.calculate_beta(price_df)
        
        # Store correlation data
        await self.store_correlation_data(corr_matrix, betas)
        
        return corr_matrix, betas
    
    async def analyze_correlation_trends(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Analyze trends in correlations over time.
        """
        # Get historical prices for Mag7 stocks and market indices
        symbols = settings.MAG7_SYMBOLS + settings.ETF_SYMBOLS
        price_df = await self.get_historical_prices(symbols, days=60)
        
        # Calculate rolling correlation
        rolling_corr = await self.calculate_rolling_correlation(price_df)
        
        # Identify significant changes
        changes = await self.identify_correlation_changes(rolling_corr)
        
        # Group changes by symbol
        changes_by_symbol = {}
        for change in changes:
            symbol1 = change['symbol1']
            symbol2 = change['symbol2']
            
            if symbol1 not in changes_by_symbol:
                changes_by_symbol[symbol1] = []
            
            if symbol2 not in changes_by_symbol:
                changes_by_symbol[symbol2] = []
            
            changes_by_symbol[symbol1].append(change)
            changes_by_symbol[symbol2].append(change)
        
        return changes_by_symbol
    
    async def update_correlation_data(self):
        """
        Update correlation data for all Mag7 stocks.
        """
        try:
            # Analyze Mag7 correlations
            corr_matrix, betas = await self.analyze_mag7_correlations()
            
            # Analyze sector correlations
            sector_corr = await self.analyze_sector_correlations()
            
            # Analyze correlation trends
            correlation_trends = await self.analyze_correlation_trends()
            
            logger.info("Correlation analysis completed successfully")
        
        except Exception as e:
            logger.error(f"Error updating correlation data: {e}")

async def market_correlation_service_main():
    """Main function for market correlation service."""
    logger.info("Starting market correlation service...")
    
    while True:
        try:
            # Create database session
            db = SessionLocal()
            
            try:
                # Create market correlation service
                service = MarketCorrelationService(db)
                
                # Update correlation data
                await service.update_correlation_data()
                
                logger.info("Market correlation update completed successfully")
            finally:
                db.close()
            
            # Wait for next cycle (daily update)
            await asyncio.sleep(24 * 60 * 60)  # 24 hours
        
        except Exception as e:
            logger.error(f"Error in market correlation service main loop: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    asyncio.run(market_correlation_service_main())

