import os
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from influxdb_client import InfluxDBClient
from influxdb_client.client.flux_table import FluxTable

from app.config import settings
from app.database import get_db, SessionLocal
from app.models.market_data import (
    Instrument, StockPrice, Option, OptionPriceData, 
    EarningsData, FinancialMetric, AnalystRating
)
from app.models.signal import (
    Signal, SignalType, SignalSource, SignalStatus,
    SignalFactor
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

class SignalGenerator:
    """Base class for signal generators."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def generate_signals(self):
        """Generate signals for all instruments."""
        raise NotImplementedError("Subclasses must implement generate_signals method")
    
    def save_signal(self, signal_data: Dict[str, Any]):
        """Save signal to database."""
        try:
            # Create signal
            signal = Signal(**signal_data)
            self.db.add(signal)
            self.db.commit()
            self.db.refresh(signal)
            
            logger.info(f"Created signal: {signal.id} for instrument {signal.instrument_id}")
            return signal
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving signal: {e}")
            return None
    
    def save_signal_factor(self, signal_id: int, factor_data: Dict[str, Any]):
        """Save signal factor to database."""
        try:
            # Create signal factor
            factor_data["signal_id"] = signal_id
            factor = SignalFactor(**factor_data)
            self.db.add(factor)
            self.db.commit()
            
            logger.info(f"Created signal factor for signal {signal_id}: {factor_data['factor_name']}")
            return factor
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving signal factor: {e}")
            return None

class TechnicalSignalGenerator(SignalGenerator):
    """Generate signals based on technical analysis."""
    
    async def generate_signals(self):
        """Generate technical signals for all Mag7 stocks."""
        for symbol in settings.MAG7_SYMBOLS:
            try:
                # Get instrument
                instrument = self.db.query(Instrument).filter(Instrument.symbol == symbol).first()
                if not instrument:
                    logger.warning(f"Instrument {symbol} not found in database")
                    continue
                
                # Get historical prices
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=60)  # Need enough data for indicators
                
                prices = self.db.query(StockPrice).filter(
                    StockPrice.instrument_id == instrument.id,
                    StockPrice.timestamp >= start_date,
                    StockPrice.timestamp <= end_date
                ).order_by(StockPrice.timestamp).all()
                
                if not prices:
                    logger.warning(f"No price data found for {symbol}")
                    continue
                
                # Convert to DataFrame
                df = pd.DataFrame([{
                    'timestamp': p.timestamp,
                    'open': p.open,
                    'high': p.high,
                    'low': p.low,
                    'close': p.close,
                    'volume': p.volume
                } for p in prices])
                
                # Generate signals
                await self.generate_rsi_signals(instrument, df)
                await self.generate_macd_signals(instrument, df)
                await self.generate_bollinger_signals(instrument, df)
                
            except Exception as e:
                logger.error(f"Error generating technical signals for {symbol}: {e}")
    
    async def generate_rsi_signals(self, instrument: Instrument, df: pd.DataFrame):
        """Generate signals based on RSI indicator."""
        try:
            # Calculate RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            df['rsi'] = rsi
            
            # Get latest RSI value
            latest_rsi = df['rsi'].iloc[-1]
            
            # Generate signals based on RSI
            if latest_rsi < 30:  # Oversold
                # Check for options with 7 DTE
                target_date = datetime.utcnow().date() + timedelta(days=7)
                min_date = target_date - timedelta(days=2)
                max_date = target_date + timedelta(days=2)
                
                options = self.db.query(Option).filter(
                    Option.instrument_id == instrument.id,
                    Option.expiration_date >= min_date,
                    Option.expiration_date <= max_date,
                    Option.option_type == 'call'
                ).all()
                
                if not options:
                    logger.warning(f"No suitable options found for {instrument.symbol}")
                    return
                
                # Find ATM option
                current_price = df['close'].iloc[-1]
                atm_option = min(options, key=lambda x: abs(x.strike_price - current_price))
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_CALL,
                    'signal_source': SignalSource.TECHNICAL,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 1.05,  # 5% profit target
                    'stop_loss': current_price * 0.97,  # 3% stop loss
                    'confidence_score': (30 - latest_rsi) / 30,  # Higher confidence for lower RSI
                    'time_frame': '7d',
                    'option_id': atm_option.id,
                    'option_strike': atm_option.strike_price,
                    'option_expiration': atm_option.expiration_date,
                    'parameters': {
                        'indicator': 'rsi',
                        'rsi_value': latest_rsi,
                        'rsi_period': 14
                    },
                    'notes': f"RSI oversold signal for {instrument.symbol}. RSI: {latest_rsi:.2f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                
                if signal:
                    # Save signal factors
                    self.save_signal_factor({
                        'factor_name': 'rsi',
                        'factor_value': latest_rsi,
                        'factor_weight': 0.7,
                        'factor_category': 'technical',
                        'factor_description': f"RSI(14) value: {latest_rsi:.2f}"
                    })
                    
                    # Add volume factor
                    volume_change = df['volume'].iloc[-1] / df['volume'].iloc[-5:].mean()
                    self.save_signal_factor({
                        'factor_name': 'volume_change',
                        'factor_value': volume_change,
                        'factor_weight': 0.3,
                        'factor_category': 'technical',
                        'factor_description': f"Volume change: {volume_change:.2f}x average"
                    })
            
            elif latest_rsi > 70:  # Overbought
                # Check for options with 7 DTE
                target_date = datetime.utcnow().date() + timedelta(days=7)
                min_date = target_date - timedelta(days=2)
                max_date = target_date + timedelta(days=2)
                
                options = self.db.query(Option).filter(
                    Option.instrument_id == instrument.id,
                    Option.expiration_date >= min_date,
                    Option.expiration_date <= max_date,
                    Option.option_type == 'put'
                ).all()
                
                if not options:
                    logger.warning(f"No suitable options found for {instrument.symbol}")
                    return
                
                # Find ATM option
                current_price = df['close'].iloc[-1]
                atm_option = min(options, key=lambda x: abs(x.strike_price - current_price))
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_PUT,
                    'signal_source': SignalSource.TECHNICAL,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 0.95,  # 5% profit target
                    'stop_loss': current_price * 1.03,  # 3% stop loss
                    'confidence_score': (latest_rsi - 70) / 30,  # Higher confidence for higher RSI
                    'time_frame': '7d',
                    'option_id': atm_option.id,
                    'option_strike': atm_option.strike_price,
                    'option_expiration': atm_option.expiration_date,
                    'parameters': {
                        'indicator': 'rsi',
                        'rsi_value': latest_rsi,
                        'rsi_period': 14
                    },
                    'notes': f"RSI overbought signal for {instrument.symbol}. RSI: {latest_rsi:.2f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                
                if signal:
                    # Save signal factors
                    self.save_signal_factor({
                        'factor_name': 'rsi',
                        'factor_value': latest_rsi,
                        'factor_weight': 0.7,
                        'factor_category': 'technical',
                        'factor_description': f"RSI(14) value: {latest_rsi:.2f}"
                    })
                    
                    # Add volume factor
                    volume_change = df['volume'].iloc[-1] / df['volume'].iloc[-5:].mean()
                    self.save_signal_factor({
                        'factor_name': 'volume_change',
                        'factor_value': volume_change,
                        'factor_weight': 0.3,
                        'factor_category': 'technical',
                        'factor_description': f"Volume change: {volume_change:.2f}x average"
                    })
        
        except Exception as e:
            logger.error(f"Error generating RSI signals for {instrument.symbol}: {e}")
    
    async def generate_macd_signals(self, instrument: Instrument, df: pd.DataFrame):
        """Generate signals based on MACD indicator."""
        try:
            # Calculate MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal_line = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal_line
            
            df['macd'] = macd
            df['signal_line'] = signal_line
            df['histogram'] = histogram
            
            # Check for MACD crossover
            if df['macd'].iloc[-2] < df['signal_line'].iloc[-2] and df['macd'].iloc[-1] > df['signal_line'].iloc[-1]:
                # Bullish crossover
                
                # Check for options with 7 DTE
                target_date = datetime.utcnow().date() + timedelta(days=7)
                min_date = target_date - timedelta(days=2)
                max_date = target_date + timedelta(days=2)
                
                options = self.db.query(Option).filter(
                    Option.instrument_id == instrument.id,
                    Option.expiration_date >= min_date,
                    Option.expiration_date <= max_date,
                    Option.option_type == 'call'
                ).all()
                
                if not options:
                    logger.warning(f"No suitable options found for {instrument.symbol}")
                    return
                
                # Find ATM option
                current_price = df['close'].iloc[-1]
                atm_option = min(options, key=lambda x: abs(x.strike_price - current_price))
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_CALL,
                    'signal_source': SignalSource.TECHNICAL,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 1.05,  # 5% profit target
                    'stop_loss': current_price * 0.97,  # 3% stop loss
                    'confidence_score': 0.7,  # Fixed confidence for MACD crossover
                    'time_frame': '7d',
                    'option_id': atm_option.id,
                    'option_strike': atm_option.strike_price,
                    'option_expiration': atm_option.expiration_date,
                    'parameters': {
                        'indicator': 'macd',
                        'macd_value': df['macd'].iloc[-1],
                        'signal_line_value': df['signal_line'].iloc[-1],
                        'histogram_value': df['histogram'].iloc[-1]
                    },
                    'notes': f"MACD bullish crossover for {instrument.symbol}. MACD: {df['macd'].iloc[-1]:.4f}, Signal: {df['signal_line'].iloc[-1]:.4f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                
                if signal:
                    # Save signal factors
                    self.save_signal_factor({
                        'factor_name': 'macd_crossover',
                        'factor_value': 1.0,  # Bullish crossover
                        'factor_weight': 0.6,
                        'factor_category': 'technical',
                        'factor_description': f"MACD bullish crossover. MACD: {df['macd'].iloc[-1]:.4f}, Signal: {df['signal_line'].iloc[-1]:.4f}"
                    })
                    
                    # Add histogram factor
                    self.save_signal_factor({
                        'factor_name': 'macd_histogram',
                        'factor_value': df['histogram'].iloc[-1],
                        'factor_weight': 0.4,
                        'factor_category': 'technical',
                        'factor_description': f"MACD histogram: {df['histogram'].iloc[-1]:.4f}"
                    })
            
            elif df['macd'].iloc[-2] > df['signal_line'].iloc[-2] and df['macd'].iloc[-1] < df['signal_line'].iloc[-1]:
                # Bearish crossover
                
                # Check for options with 7 DTE
                target_date = datetime.utcnow().date() + timedelta(days=7)
                min_date = target_date - timedelta(days=2)
                max_date = target_date + timedelta(days=2)
                
                options = self.db.query(Option).filter(
                    Option.instrument_id == instrument.id,
                    Option.expiration_date >= min_date,
                    Option.expiration_date <= max_date,
                    Option.option_type == 'put'
                ).all()
                
                if not options:
                    logger.warning(f"No suitable options found for {instrument.symbol}")
                    return
                
                # Find ATM option
                current_price = df['close'].iloc[-1]
                atm_option = min(options, key=lambda x: abs(x.strike_price - current_price))
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_PUT,
                    'signal_source': SignalSource.TECHNICAL,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 0.95,  # 5% profit target
                    'stop_loss': current_price * 1.03,  # 3% stop loss
                    'confidence_score': 0.7,  # Fixed confidence for MACD crossover
                    'time_frame': '7d',
                    'option_id': atm_option.id,
                    'option_strike': atm_option.strike_price,
                    'option_expiration': atm_option.expiration_date,
                    'parameters': {
                        'indicator': 'macd',
                        'macd_value': df['macd'].iloc[-1],
                        'signal_line_value': df['signal_line'].iloc[-1],
                        'histogram_value': df['histogram'].iloc[-1]
                    },
                    'notes': f"MACD bearish crossover for {instrument.symbol}. MACD: {df['macd'].iloc[-1]:.4f}, Signal: {df['signal_line'].iloc[-1]:.4f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                
                if signal:
                    # Save signal factors
                    self.save_signal_factor({
                        'factor_name': 'macd_crossover',
                        'factor_value': -1.0,  # Bearish crossover
                        'factor_weight': 0.6,
                        'factor_category': 'technical',
                        'factor_description': f"MACD bearish crossover. MACD: {df['macd'].iloc[-1]:.4f}, Signal: {df['signal_line'].iloc[-1]:.4f}"
                    })
                    
                    # Add histogram factor
                    self.save_signal_factor({
                        'factor_name': 'macd_histogram',
                        'factor_value': df['histogram'].iloc[-1],
                        'factor_weight': 0.4,
                        'factor_category': 'technical',
                        'factor_description': f"MACD histogram: {df['histogram'].iloc[-1]:.4f}"
                    })
        
        except Exception as e:
            logger.error(f"Error generating MACD signals for {instrument.symbol}: {e}")
    
    async def generate_bollinger_signals(self, instrument: Instrument, df: pd.DataFrame):
        """Generate signals based on Bollinger Bands."""
        try:
            # Calculate Bollinger Bands
            window = 20
            df['sma'] = df['close'].rolling(window=window).mean()
            df['std'] = df['close'].rolling(window=window).std()
            df['upper_band'] = df['sma'] + 2 * df['std']
            df['lower_band'] = df['sma'] - 2 * df['std']
            
            # Check for price crossing below lower band
            if df['close'].iloc[-2] > df['lower_band'].iloc[-2] and df['close'].iloc[-1] < df['lower_band'].iloc[-1]:
                # Potential bounce (bullish)
                
                # Check for options with 7 DTE
                target_date = datetime.utcnow().date() + timedelta(days=7)
                min_date = target_date - timedelta(days=2)
                max_date = target_date + timedelta(days=2)
                
                options = self.db.query(Option).filter(
                    Option.instrument_id == instrument.id,
                    Option.expiration_date >= min_date,
                    Option.expiration_date <= max_date,
                    Option.option_type == 'call'
                ).all()
                
                if not options:
                    logger.warning(f"No suitable options found for {instrument.symbol}")
                    return
                
                # Find ATM option
                current_price = df['close'].iloc[-1]
                atm_option = min(options, key=lambda x: abs(x.strike_price - current_price))
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_CALL,
                    'signal_source': SignalSource.TECHNICAL,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': df['sma'].iloc[-1],  # Target the middle band (SMA)
                    'stop_loss': current_price * 0.97,  # 3% stop loss
                    'confidence_score': 0.65,  # Fixed confidence for Bollinger Band signal
                    'time_frame': '7d',
                    'option_id': atm_option.id,
                    'option_strike': atm_option.strike_price,
                    'option_expiration': atm_option.expiration_date,
                    'parameters': {
                        'indicator': 'bollinger_bands',
                        'sma_value': df['sma'].iloc[-1],
                        'upper_band_value': df['upper_band'].iloc[-1],
                        'lower_band_value': df['lower_band'].iloc[-1]
                    },
                    'notes': f"Bollinger Band lower band break for {instrument.symbol}. Price: {current_price:.2f}, Lower Band: {df['lower_band'].iloc[-1]:.2f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                
                if signal:
                    # Save signal factors
                    self.save_signal_factor({
                        'factor_name': 'bollinger_band_position',
                        'factor_value': (current_price - df['lower_band'].iloc[-1]) / (df['upper_band'].iloc[-1] - df['lower_band'].iloc[-1]),
                        'factor_weight': 0.7,
                        'factor_category': 'technical',
                        'factor_description': f"Position within Bollinger Bands (0 = lower band, 1 = upper band)"
                    })
                    
                    # Add bandwidth factor
                    bandwidth = (df['upper_band'].iloc[-1] - df['lower_band'].iloc[-1]) / df['sma'].iloc[-1]
                    self.save_signal_factor({
                        'factor_name': 'bollinger_bandwidth',
                        'factor_value': bandwidth,
                        'factor_weight': 0.3,
                        'factor_category': 'technical',
                        'factor_description': f"Bollinger Bandwidth: {bandwidth:.4f}"
                    })
            
            # Check for price crossing above upper band
            elif df['close'].iloc[-2] < df['upper_band'].iloc[-2] and df['close'].iloc[-1] > df['upper_band'].iloc[-1]:
                # Potential reversal (bearish)
                
                # Check for options with 7 DTE
                target_date = datetime.utcnow().date() + timedelta(days=7)
                min_date = target_date - timedelta(days=2)
                max_date = target_date + timedelta(days=2)
                
                options = self.db.query(Option).filter(
                    Option.instrument_id == instrument.id,
                    Option.expiration_date >= min_date,
                    Option.expiration_date <= max_date,
                    Option.option_type == 'put'
                ).all()
                
                if not options:
                    logger.warning(f"No suitable options found for {instrument.symbol}")
                    return
                
                # Find ATM option
                current_price = df['close'].iloc[-1]
                atm_option = min(options, key=lambda x: abs(x.strike_price - current_price))
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_PUT,
                    'signal_source': SignalSource.TECHNICAL,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': df['sma'].iloc[-1],  # Target the middle band (SMA)
                    'stop_loss': current_price * 1.03,  # 3% stop loss
                    'confidence_score': 0.65,  # Fixed confidence for Bollinger Band signal
                    'time_frame': '7d',
                    'option_id': atm_option.id,
                    'option_strike': atm_option.strike_price,
                    'option_expiration': atm_option.expiration_date,
                    'parameters': {
                        'indicator': 'bollinger_bands',
                        'sma_value': df['sma'].iloc[-1],
                        'upper_band_value': df['upper_band'].iloc[-1],
                        'lower_band_value': df['lower_band'].iloc[-1]
                    },
                    'notes': f"Bollinger Band upper band break for {instrument.symbol}. Price: {current_price:.2f}, Upper Band: {df['upper_band'].iloc[-1]:.2f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                
                if signal:
                    # Save signal factors
                    self.save_signal_factor({
                        'factor_name': 'bollinger_band_position',
                        'factor_value': (current_price - df['lower_band'].iloc[-1]) / (df['upper_band'].iloc[-1] - df['lower_band'].iloc[-1]),
                        'factor_weight': 0.7,
                        'factor_category': 'technical',
                        'factor_description': f"Position within Bollinger Bands (0 = lower band, 1 = upper band)"
                    })
                    
                    # Add bandwidth factor
                    bandwidth = (df['upper_band'].iloc[-1] - df['lower_band'].iloc[-1]) / df['sma'].iloc[-1]
                    self.save_signal_factor({
                        'factor_name': 'bollinger_bandwidth',
                        'factor_value': bandwidth,
                        'factor_weight': 0.3,
                        'factor_category': 'technical',
                        'factor_description': f"Bollinger Bandwidth: {bandwidth:.4f}"
                    })
        
        except Exception as e:
            logger.error(f"Error generating Bollinger Band signals for {instrument.symbol}: {e}")

class FundamentalSignalGenerator(SignalGenerator):
    """Generate signals based on fundamental analysis."""
    
    async def generate_signals(self):
        """Generate fundamental signals for all Mag7 stocks."""
        for symbol in settings.MAG7_SYMBOLS:
            try:
                # Get instrument
                instrument = self.db.query(Instrument).filter(Instrument.symbol == symbol).first()
                if not instrument:
                    logger.warning(f"Instrument {symbol} not found in database")
                    continue
                
                # Generate signals
                await self.generate_earnings_signals(instrument)
                await self.generate_valuation_signals(instrument)
                
            except Exception as e:
                logger.error(f"Error generating fundamental signals for {symbol}: {e}")
    
    async def generate_earnings_signals(self, instrument: Instrument):
        """Generate signals based on upcoming earnings."""
        try:
            # Check if instrument has earnings schedule
            if not instrument.earnings_schedule:
                logger.warning(f"No earnings schedule found for {instrument.symbol}")
                return
            
            # Parse next earnings date
            next_earnings_date = datetime.fromisoformat(instrument.earnings_schedule.get("next_date"))
            
            # Check if earnings are within the next 14 days
            days_to_earnings = (next_earnings_date.date() - datetime.utcnow().date()).days
            
            if 3 <= days_to_earnings <= 14:
                # Get historical earnings data
                earnings_data = self.db.query(EarningsData).filter(
                    EarningsData.instrument_id == instrument.id
                ).order_by(EarningsData.earnings_date.desc()).limit(8).all()
                
                if not earnings_data:
                    logger.warning(f"No historical earnings data found for {instrument.symbol}")
                    return
                
                # Calculate average surprise percentage
                surprise_percentages = [e.surprise_percentage for e in earnings_data if e.surprise_percentage is not None]
                avg_surprise = sum(surprise_percentages) / len(surprise_percentages) if surprise_percentages else 0
                
                # Count positive surprises
                positive_surprises = sum(1 for sp in surprise_percentages if sp > 0)
                positive_surprise_ratio = positive_surprises / len(surprise_percentages) if surprise_percentages else 0
                
                # Determine signal direction based on historical earnings performance
                if positive_surprise_ratio >= 0.75 and avg_surprise > 5:
                    # Strong history of positive surprises, bullish signal
                    
                    # Check for options with expiration after earnings
                    min_expiration = next_earnings_date + timedelta(days=1)
                    max_expiration = next_earnings_date + timedelta(days=10)
                    
                    options = self.db.query(Option).filter(
                        Option.instrument_id == instrument.id,
                        Option.expiration_date >= min_expiration,
                        Option.expiration_date <= max_expiration,
                        Option.option_type == 'call'
                    ).all()
                    
                    if not options:
                        logger.warning(f"No suitable options found for {instrument.symbol}")
                        return
                    
                    # Get current price
                    current_price = self.db.query(StockPrice).filter(
                        StockPrice.instrument_id == instrument.id
                    ).order_by(StockPrice.timestamp.desc()).first().close
                    
                    # Find ATM option
                    atm_option = min(options, key=lambda x: abs(x.strike_price - current_price))
                    
                    # Create signal
                    signal_data = {
                        'instrument_id': instrument.id,
                        'signal_type': SignalType.LONG_CALL,
                        'signal_source': SignalSource.EARNINGS,
                        'status': SignalStatus.PENDING,
                        'entry_price': None,  # Will be set when executed
                        'target_price': current_price * 1.08,  # 8% profit target
                        'stop_loss': current_price * 0.95,  # 5% stop loss
                        'confidence_score': 0.7 * positive_surprise_ratio + 0.3 * min(1.0, avg_surprise / 10),
                        'time_frame': f"{days_to_earnings}d",
                        'option_id': atm_option.id,
                        'option_strike': atm_option.strike_price,
                        'option_expiration': atm_option.expiration_date,
                        'earnings_impact': 0.9,  # High impact from earnings
                        'parameters': {
                            'days_to_earnings': days_to_earnings,
                            'avg_surprise_percentage': avg_surprise,
                            'positive_surprise_ratio': positive_surprise_ratio
                        },
                        'notes': f"Earnings play for {instrument.symbol}. Earnings date: {next_earnings_date.strftime('%Y-%m-%d')}. Historical positive surprise ratio: {positive_surprise_ratio:.2f}"
                    }
                    
                    # Save signal
                    signal = self.save_signal(signal_data)
                    
                    if signal:
                        # Save signal factors
                        self.save_signal_factor({
                            'factor_name': 'earnings_surprise_history',
                            'factor_value': avg_surprise,
                            'factor_weight': 0.5,
                            'factor_category': 'fundamental',
                            'factor_description': f"Average earnings surprise: {avg_surprise:.2f}%"
                        })
                        
                        self.save_signal_factor({
                            'factor_name': 'positive_surprise_ratio',
                            'factor_value': positive_surprise_ratio,
                            'factor_weight': 0.3,
                            'factor_category': 'fundamental',
                            'factor_description': f"Positive surprise ratio: {positive_surprise_ratio:.2f}"
                        })
                        
                        self.save_signal_factor({
                            'factor_name': 'days_to_earnings',
                            'factor_value': days_to_earnings,
                            'factor_weight': 0.2,
                            'factor_category': 'fundamental',
                            'factor_description': f"Days to earnings: {days_to_earnings}"
                        })
                
                elif positive_surprise_ratio <= 0.25 or avg_surprise < -5:
                    # History of negative surprises, bearish signal
                    
                    # Check for options with expiration after earnings
                    min_expiration = next_earnings_date + timedelta(days=1)
                    max_expiration = next_earnings_date + timedelta(days=10)
                    
                    options = self.db.query(Option).filter(
                        Option.instrument_id == instrument.id,
                        Option.expiration_date >= min_expiration,
                        Option.expiration_date <= max_expiration,
                        Option.option_type == 'put'
                    ).all()
                    
                    if not options:
                        logger.warning(f"No suitable options found for {instrument.symbol}")
                        return
                    
                    # Get current price
                    current_price = self.db.query(StockPrice).filter(
                        StockPrice.instrument_id == instrument.id
                    ).order_by(StockPrice.timestamp.desc()).first().close
                    
                    # Find ATM option
                    atm_option = min(options, key=lambda x: abs(x.strike_price - current_price))
                    
                    # Create signal
                    signal_data = {
                        'instrument_id': instrument.id,
                        'signal_type': SignalType.LONG_PUT,
                        'signal_source': SignalSource.EARNINGS,
                        'status': SignalStatus.PENDING,
                        'entry_price': None,  # Will be set when executed
                        'target_price': current_price * 0.92,  # 8% profit target
                        'stop_loss': current_price * 1.05,  # 5% stop loss
                        'confidence_score': 0.7 * (1 - positive_surprise_ratio) + 0.3 * min(1.0, abs(avg_surprise) / 10),
                        'time_frame': f"{days_to_earnings}d",
                        'option_id': atm_option.id,
                        'option_strike': atm_option.strike_price,
                        'option_expiration': atm_option.expiration_date,
                        'earnings_impact': 0.9,  # High impact from earnings
                        'parameters': {
                            'days_to_earnings': days_to_earnings,
                            'avg_surprise_percentage': avg_surprise,
                            'positive_surprise_ratio': positive_surprise_ratio
                        },
                        'notes': f"Earnings play for {instrument.symbol}. Earnings date: {next_earnings_date.strftime('%Y-%m-%d')}. Historical positive surprise ratio: {positive_surprise_ratio:.2f}"
                    }
                    
                    # Save signal
                    signal = self.save_signal(signal_data)
                    
                    if signal:
                        # Save signal factors
                        self.save_signal_factor({
                            'factor_name': 'earnings_surprise_history',
                            'factor_value': avg_surprise,
                            'factor_weight': 0.5,
                            'factor_category': 'fundamental',
                            'factor_description': f"Average earnings surprise: {avg_surprise:.2f}%"
                        })
                        
                        self.save_signal_factor({
                            'factor_name': 'positive_surprise_ratio',
                            'factor_value': positive_surprise_ratio,
                            'factor_weight': 0.3,
                            'factor_category': 'fundamental',
                            'factor_description': f"Positive surprise ratio: {positive_surprise_ratio:.2f}"
                        })
                        
                        self.save_signal_factor({
                            'factor_name': 'days_to_earnings',
                            'factor_value': days_to_earnings,
                            'factor_weight': 0.2,
                            'factor_category': 'fundamental',
                            'factor_description': f"Days to earnings: {days_to_earnings}"
                        })
        
        except Exception as e:
            logger.error(f"Error generating earnings signals for {instrument.symbol}: {e}")
    
    async def generate_valuation_signals(self, instrument: Instrument):
        """Generate signals based on valuation metrics."""
        try:
            # Get latest financial metrics
            pe_ratio = self.db.query(FinancialMetric).filter(
                FinancialMetric.instrument_id == instrument.id,
                FinancialMetric.metric_type == 'pe_ratio'
            ).order_by(FinancialMetric.date.desc()).first()
            
            peg_ratio = self.db.query(FinancialMetric).filter(
                FinancialMetric.instrument_id == instrument.id,
                FinancialMetric.metric_type == 'peg_ratio'
            ).order_by(FinancialMetric.date.desc()).first()
            
            if not pe_ratio or not peg_ratio:
                logger.warning(f"Missing valuation metrics for {instrument.symbol}")
                return
            
            # Get current price
            current_price = self.db.query(StockPrice).filter(
                StockPrice.instrument_id == instrument.id
            ).order_by(StockPrice.timestamp.desc()).first().close
            
            # Check for undervaluation
            if pe_ratio.value < 15 and peg_ratio.value < 1.0:
                # Undervalued, bullish signal
                
                # Check for options with 7 DTE
                target_date = datetime.utcnow().date() + timedelta(days=7)
                min_date = target_date - timedelta(days=2)
                max_date = target_date + timedelta(days=2)
                
                options = self.db.query(Option).filter(
                    Option.instrument_id == instrument.id,
                    Option.expiration_date >= min_date,
                    Option.expiration_date <= max_date,
                    Option.option_type == 'call'
                ).all()
                
                if not options:
                    logger.warning(f"No suitable options found for {instrument.symbol}")
                    return
                
                # Find ATM option
                atm_option = min(options, key=lambda x: abs(x.strike_price - current_price))
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_CALL,
                    'signal_source': SignalSource.FUNDAMENTAL,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 1.05,  # 5% profit target
                    'stop_loss': current_price * 0.97,  # 3% stop loss
                    'confidence_score': 0.6,  # Moderate confidence for valuation signals
                    'time_frame': '7d',
                    'option_id': atm_option.id,
                    'option_strike': atm_option.strike_price,
                    'option_expiration': atm_option.expiration_date,
                    'valuation_impact': 0.8,  # High impact from valuation
                    'parameters': {
                        'pe_ratio': pe_ratio.value,
                        'peg_ratio': peg_ratio.value
                    },
                    'notes': f"Valuation signal for {instrument.symbol}. PE Ratio: {pe_ratio.value:.2f}, PEG Ratio: {peg_ratio.value:.2f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                
                if signal:
                    # Save signal factors
                    self.save_signal_factor({
                        'factor_name': 'pe_ratio',
                        'factor_value': pe_ratio.value,
                        'factor_weight': 0.5,
                        'factor_category': 'fundamental',
                        'factor_description': f"PE Ratio: {pe_ratio.value:.2f}"
                    })
                    
                    self.save_signal_factor({
                        'factor_name': 'peg_ratio',
                        'factor_value': peg_ratio.value,
                        'factor_weight': 0.5,
                        'factor_category': 'fundamental',
                        'factor_description': f"PEG Ratio: {peg_ratio.value:.2f}"
                    })
            
            # Check for overvaluation
            elif pe_ratio.value > 30 and peg_ratio.value > 2.0:
                # Overvalued, bearish signal
                
                # Check for options with 7 DTE
                target_date = datetime.utcnow().date() + timedelta(days=7)
                min_date = target_date - timedelta(days=2)
                max_date = target_date + timedelta(days=2)
                
                options = self.db.query(Option).filter(
                    Option.instrument_id == instrument.id,
                    Option.expiration_date >= min_date,
                    Option.expiration_date <= max_date,
                    Option.option_type == 'put'
                ).all()
                
                if not options:
                    logger.warning(f"No suitable options found for {instrument.symbol}")
                    return
                
                # Find ATM option
                atm_option = min(options, key=lambda x: abs(x.strike_price - current_price))
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_PUT,
                    'signal_source': SignalSource.FUNDAMENTAL,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 0.95,  # 5% profit target
                    'stop_loss': current_price * 1.03,  # 3% stop loss
                    'confidence_score': 0.6,  # Moderate confidence for valuation signals
                    'time_frame': '7d',
                    'option_id': atm_option.id,
                    'option_strike': atm_option.strike_price,
                    'option_expiration': atm_option.expiration_date,
                    'valuation_impact': 0.8,  # High impact from valuation
                    'parameters': {
                        'pe_ratio': pe_ratio.value,
                        'peg_ratio': peg_ratio.value
                    },
                    'notes': f"Valuation signal for {instrument.symbol}. PE Ratio: {pe_ratio.value:.2f}, PEG Ratio: {peg_ratio.value:.2f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                
                if signal:
                    # Save signal factors
                    self.save_signal_factor({
                        'factor_name': 'pe_ratio',
                        'factor_value': pe_ratio.value,
                        'factor_weight': 0.5,
                        'factor_category': 'fundamental',
                        'factor_description': f"PE Ratio: {pe_ratio.value:.2f}"
                    })
                    
                    self.save_signal_factor({
                        'factor_name': 'peg_ratio',
                        'factor_value': peg_ratio.value,
                        'factor_weight': 0.5,
                        'factor_category': 'fundamental',
                        'factor_description': f"PEG Ratio: {peg_ratio.value:.2f}"
                    })
        
        except Exception as e:
            logger.error(f"Error generating valuation signals for {instrument.symbol}: {e}")

class VolatilitySignalGenerator(SignalGenerator):
    """Generate signals based on volatility analysis."""
    
    async def generate_signals(self):
        """Generate volatility signals for all Mag7 stocks."""
        for symbol in settings.MAG7_SYMBOLS:
            try:
                # Get instrument
                instrument = self.db.query(Instrument).filter(Instrument.symbol == symbol).first()
                if not instrument:
                    logger.warning(f"Instrument {symbol} not found in database")
                    continue
                
                # Generate signals
                await self.generate_iv_percentile_signals(instrument)
                await self.generate_iv_skew_signals(instrument)
                
            except Exception as e:
                logger.error(f"Error generating volatility signals for {symbol}: {e}")
    
    async def generate_iv_percentile_signals(self, instrument: Instrument):
        """Generate signals based on implied volatility percentile."""
        try:
            # Get volatility data
            volatility_data = self.db.query(VolatilityData).filter(
                VolatilityData.instrument_id == instrument.id
            ).order_by(VolatilityData.date.desc()).first()
            
            if not volatility_data:
                logger.warning(f"No volatility data found for {instrument.symbol}")
                return
            
            # Check for low IV percentile
            if volatility_data.iv_percentile < 20:
                # Low IV, potential for long volatility strategies
                
                # Check for options with 7 DTE
                target_date = datetime.utcnow().date() + timedelta(days=7)
                min_date = target_date - timedelta(days=2)
                max_date = target_date + timedelta(days=2)
                
                # Get current price
                current_price = self.db.query(StockPrice).filter(
                    StockPrice.instrument_id == instrument.id
                ).order_by(StockPrice.timestamp.desc()).first().close
                
                # Find call options
                call_options = self.db.query(Option).filter(
                    Option.instrument_id == instrument.id,
                    Option.expiration_date >= min_date,
                    Option.expiration_date <= max_date,
                    Option.option_type == 'call'
                ).all()
                
                # Find put options
                put_options = self.db.query(Option).filter(
                    Option.instrument_id == instrument.id,
                    Option.expiration_date >= min_date,
                    Option.expiration_date <= max_date,
                    Option.option_type == 'put'
                ).all()
                
                if not call_options or not put_options:
                    logger.warning(f"No suitable options found for {instrument.symbol}")
                    return
                
                # Find ATM options
                atm_call = min(call_options, key=lambda x: abs(x.strike_price - current_price))
                atm_put = min(put_options, key=lambda x: abs(x.strike_price - current_price))
                
                # Create signal for long straddle
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_CALL,  # Simplified to long call for now
                    'signal_source': SignalSource.VOLATILITY,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': None,  # Not applicable for volatility strategies
                    'stop_loss': None,  # Not applicable for volatility strategies
                    'confidence_score': 0.7 * (1 - volatility_data.iv_percentile / 100),  # Higher confidence for lower IV percentile
                    'time_frame': '7d',
                    'option_id': atm_call.id,
                    'option_strike': atm_call.strike_price,
                    'option_expiration': atm_call.expiration_date,
                    'implied_volatility': volatility_data.implied_volatility_avg,
                    'parameters': {
                        'iv_percentile': volatility_data.iv_percentile,
                        'iv_rank': volatility_data.iv_rank,
                        'strategy': 'long_volatility'
                    },
                    'notes': f"Low IV percentile signal for {instrument.symbol}. IV Percentile: {volatility_data.iv_percentile:.2f}%, IV Rank: {volatility_data.iv_rank:.2f}%"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                
                if signal:
                    # Save signal factors
                    self.save_signal_factor({
                        'factor_name': 'iv_percentile',
                        'factor_value': volatility_data.iv_percentile,
                        'factor_weight': 0.6,
                        'factor_category': 'volatility',
                        'factor_description': f"IV Percentile: {volatility_data.iv_percentile:.2f}%"
                    })
                    
                    self.save_signal_factor({
                        'factor_name': 'iv_rank',
                        'factor_value': volatility_data.iv_rank,
                        'factor_weight': 0.4,
                        'factor_category': 'volatility',
                        'factor_description': f"IV Rank: {volatility_data.iv_rank:.2f}%"
                    })
            
            # Check for high IV percentile
            elif volatility_data.iv_percentile > 80:
                # High IV, potential for short volatility strategies
                
                # Check for options with 7 DTE
                target_date = datetime.utcnow().date() + timedelta(days=7)
                min_date = target_date - timedelta(days=2)
                max_date = target_date + timedelta(days=2)
                
                # Get current price
                current_price = self.db.query(StockPrice).filter(
                    StockPrice.instrument_id == instrument.id
                ).order_by(StockPrice.timestamp.desc()).first().close
                
                # Find call options
                call_options = self.db.query(Option).filter(
                    Option.instrument_id == instrument.id,
                    Option.expiration_date >= min_date,
                    Option.expiration_date <= max_date,
                    Option.option_type == 'call'
                ).all()
                
                # Find put options
                put_options = self.db.query(Option).filter(
                    Option.instrument_id == instrument.id,
                    Option.expiration_date >= min_date,
                    Option.expiration_date <= max_date,
                    Option.option_type == 'put'
                ).all()
                
                if not call_options or not put_options:
                    logger.warning(f"No suitable options found for {instrument.symbol}")
                    return
                
                # Find ATM options
                atm_call = min(call_options, key=lambda x: abs(x.strike_price - current_price))
                atm_put = min(put_options, key=lambda x: abs(x.strike_price - current_price))
                
                # Create signal for short straddle
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.SHORT_CALL,  # Simplified to short call for now
                    'signal_source': SignalSource.VOLATILITY,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': None,  # Not applicable for volatility strategies
                    'stop_loss': None,  # Not applicable for volatility strategies
                    'confidence_score': 0.7 * (volatility_data.iv_percentile / 100),  # Higher confidence for higher IV percentile
                    'time_frame': '7d',
                    'option_id': atm_call.id,
                    'option_strike': atm_call.strike_price,
                    'option_expiration': atm_call.expiration_date,
                    'implied_volatility': volatility_data.implied_volatility_avg,
                    'parameters': {
                        'iv_percentile': volatility_data.iv_percentile,
                        'iv_rank': volatility_data.iv_rank,
                        'strategy': 'short_volatility'
                    },
                    'notes': f"High IV percentile signal for {instrument.symbol}. IV Percentile: {volatility_data.iv_percentile:.2f}%, IV Rank: {volatility_data.iv_rank:.2f}%"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                
                if signal:
                    # Save signal factors
                    self.save_signal_factor({
                        'factor_name': 'iv_percentile',
                        'factor_value': volatility_data.iv_percentile,
                        'factor_weight': 0.6,
                        'factor_category': 'volatility',
                        'factor_description': f"IV Percentile: {volatility_data.iv_percentile:.2f}%"
                    })
                    
                    self.save_signal_factor({
                        'factor_name': 'iv_rank',
                        'factor_value': volatility_data.iv_rank,
                        'factor_weight': 0.4,
                        'factor_category': 'volatility',
                        'factor_description': f"IV Rank: {volatility_data.iv_rank:.2f}%"
                    })
        
        except Exception as e:
            logger.error(f"Error generating IV percentile signals for {instrument.symbol}: {e}")
    
    async def generate_iv_skew_signals(self, instrument: Instrument):
        """Generate signals based on implied volatility skew."""
        # Implementation for IV skew signals would go here
        pass

class EnsembleSignalGenerator(SignalGenerator):
    """Generate signals based on ensemble of multiple signal sources."""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.technical_generator = TechnicalSignalGenerator(db)
        self.fundamental_generator = FundamentalSignalGenerator(db)
        self.volatility_generator = VolatilitySignalGenerator(db)
    
    async def generate_signals(self):
        """Generate ensemble signals for all Mag7 stocks."""
        # First, generate signals from individual generators
        await self.technical_generator.generate_signals()
        await self.fundamental_generator.generate_signals()
        await self.volatility_generator.generate_signals()
        
        # Then, generate ensemble signals based on the individual signals
        for symbol in settings.MAG7_SYMBOLS:
            try:
                # Get instrument
                instrument = self.db.query(Instrument).filter(Instrument.symbol == symbol).first()
                if not instrument:
                    logger.warning(f"Instrument {symbol} not found in database")
                    continue
                
                # Get recent signals
                recent_signals = self.db.query(Signal).filter(
                    Signal.instrument_id == instrument.id,
                    Signal.generation_time >= datetime.utcnow() - timedelta(days=1)
                ).all()
                
                # Count bullish and bearish signals
                bullish_signals = [s for s in recent_signals if s.signal_type in [SignalType.LONG_CALL, SignalType.SHORT_PUT]]
                bearish_signals = [s for s in recent_signals if s.signal_type in [SignalType.LONG_PUT, SignalType.SHORT_CALL]]
                
                # Calculate weighted confidence
                bullish_confidence = sum(s.confidence_score for s in bullish_signals) if bullish_signals else 0
                bearish_confidence = sum(s.confidence_score for s in bearish_signals) if bearish_signals else 0
                
                # Generate ensemble signal if there's a clear bias
                if bullish_confidence > 1.5 and bullish_confidence > bearish_confidence * 2:
                    # Strong bullish bias
                    await self.generate_ensemble_bullish_signal(instrument, bullish_signals)
                elif bearish_confidence > 1.5 and bearish_confidence > bullish_confidence * 2:
                    # Strong bearish bias
                    await self.generate_ensemble_bearish_signal(instrument, bearish_signals)
            
            except Exception as e:
                logger.error(f"Error generating ensemble signals for {symbol}: {e}")
    
    async def generate_ensemble_bullish_signal(self, instrument: Instrument, bullish_signals: List[Signal]):
        """Generate ensemble bullish signal."""
        try:
            # Check for options with 7 DTE
            target_date = datetime.utcnow().date() + timedelta(days=7)
            min_date = target_date - timedelta(days=2)
            max_date = target_date + timedelta(days=2)
            
            # Get current price
            current_price = self.db.query(StockPrice).filter(
                StockPrice.instrument_id == instrument.id
            ).order_by(StockPrice.timestamp.desc()).first().close
            
            # Find call options
            call_options = self.db.query(Option).filter(
                Option.instrument_id == instrument.id,
                Option.expiration_date >= min_date,
                Option.expiration_date <= max_date,
                Option.option_type == 'call'
            ).all()
            
            if not call_options:
                logger.warning(f"No suitable options found for {instrument.symbol}")
                return
            
            # Find ATM option
            atm_call = min(call_options, key=lambda x: abs(x.strike_price - current_price))
            
            # Calculate ensemble confidence
            ensemble_confidence = min(0.95, sum(s.confidence_score for s in bullish_signals) / len(bullish_signals) * 1.2)
            
            # Create signal
            signal_data = {
                'instrument_id': instrument.id,
                'signal_type': SignalType.LONG_CALL,
                'signal_source': SignalSource.ENSEMBLE,
                'status': SignalStatus.PENDING,
                'entry_price': None,  # Will be set when executed
                'target_price': current_price * 1.05,  # 5% profit target
                'stop_loss': current_price * 0.97,  # 3% stop loss
                'confidence_score': ensemble_confidence,
                'time_frame': '7d',
                'option_id': atm_call.id,
                'option_strike': atm_call.strike_price,
                'option_expiration': atm_call.expiration_date,
                'parameters': {
                    'component_signals': [s.id for s in bullish_signals],
                    'component_count': len(bullish_signals)
                },
                'notes': f"Ensemble bullish signal for {instrument.symbol} based on {len(bullish_signals)} component signals."
            }
            
            # Save signal
            signal = self.save_signal(signal_data)
            
            if signal:
                # Save signal factors
                self.save_signal_factor({
                    'factor_name': 'ensemble_component_count',
                    'factor_value': len(bullish_signals),
                    'factor_weight': 0.3,
                    'factor_category': 'ensemble',
                    'factor_description': f"Number of component signals: {len(bullish_signals)}"
                })
                
                # Add factors for each signal source
                source_counts = {}
                for s in bullish_signals:
                    source = s.signal_source.value
                    source_counts[source] = source_counts.get(source, 0) + 1
                
                for source, count in source_counts.items():
                    self.save_signal_factor({
                        'factor_name': f"{source}_signal_count",
                        'factor_value': count,
                        'factor_weight': 0.7 / len(source_counts),
                        'factor_category': 'ensemble',
                        'factor_description': f"Number of {source} signals: {count}"
                    })
        
        except Exception as e:
            logger.error(f"Error generating ensemble bullish signal for {instrument.symbol}: {e}")
    
    async def generate_ensemble_bearish_signal(self, instrument: Instrument, bearish_signals: List[Signal]):
        """Generate ensemble bearish signal."""
        try:
            # Check for options with 7 DTE
            target_date = datetime.utcnow().date() + timedelta(days=7)
            min_date = target_date - timedelta(days=2)
            max_date = target_date + timedelta(days=2)
            
            # Get current price
            current_price = self.db.query(StockPrice).filter(
                StockPrice.instrument_id == instrument.id
            ).order_by(StockPrice.timestamp.desc()).first().close
            
            # Find put options
            put_options = self.db.query(Option).filter(
                Option.instrument_id == instrument.id,
                Option.expiration_date >= min_date,
                Option.expiration_date <= max_date,
                Option.option_type == 'put'
            ).all()
            
            if not put_options:
                logger.warning(f"No suitable options found for {instrument.symbol}")
                return
            
            # Find ATM option
            atm_put = min(put_options, key=lambda x: abs(x.strike_price - current_price))
            
            # Calculate ensemble confidence
            ensemble_confidence = min(0.95, sum(s.confidence_score for s in bearish_signals) / len(bearish_signals) * 1.2)
            
            # Create signal
            signal_data = {
                'instrument_id': instrument.id,
                'signal_type': SignalType.LONG_PUT,
                'signal_source': SignalSource.ENSEMBLE,
                'status': SignalStatus.PENDING,
                'entry_price': None,  # Will be set when executed
                'target_price': current_price * 0.95,  # 5% profit target
                'stop_loss': current_price * 1.03,  # 3% stop loss
                'confidence_score': ensemble_confidence,
                'time_frame': '7d',
                'option_id': atm_put.id,
                'option_strike': atm_put.strike_price,
                'option_expiration': atm_put.expiration_date,
                'parameters': {
                    'component_signals': [s.id for s in bearish_signals],
                    'component_count': len(bearish_signals)
                },
                'notes': f"Ensemble bearish signal for {instrument.symbol} based on {len(bearish_signals)} component signals."
            }
            
            # Save signal
            signal = self.save_signal(signal_data)
            
            if signal:
                # Save signal factors
                self.save_signal_factor({
                    'factor_name': 'ensemble_component_count',
                    'factor_value': len(bearish_signals),
                    'factor_weight': 0.3,
                    'factor_category': 'ensemble',
                    'factor_description': f"Number of component signals: {len(bearish_signals)}"
                })
                
                # Add factors for each signal source
                source_counts = {}
                for s in bearish_signals:
                    source = s.signal_source.value
                    source_counts[source] = source_counts.get(source, 0) + 1
                
                for source, count in source_counts.items():
                    self.save_signal_factor({
                        'factor_name': f"{source}_signal_count",
                        'factor_value': count,
                        'factor_weight': 0.7 / len(source_counts),
                        'factor_category': 'ensemble',
                        'factor_description': f"Number of {source} signals: {count}"
                    })
        
        except Exception as e:
            logger.error(f"Error generating ensemble bearish signal for {instrument.symbol}: {e}")

async def signal_generation_main():
    """Main function for signal generation service."""
    logger.info("Starting signal generation service...")
    
    while True:
        try:
            # Create database session
            db = SessionLocal()
            
            try:
                # Create ensemble signal generator
                generator = EnsembleSignalGenerator(db)
                
                # Generate signals
                await generator.generate_signals()
                
                logger.info("Signal generation completed successfully")
            finally:
                db.close()
            
            # Wait for next cycle
            await asyncio.sleep(settings.SIGNAL_GENERATION_INTERVAL * 60)  # Convert minutes to seconds
        
        except Exception as e:
            logger.error(f"Error in signal generation main loop: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    asyncio.run(signal_generation_main())

