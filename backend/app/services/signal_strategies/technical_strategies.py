import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session

from app.models.market_data import Instrument, StockPrice, Option
from app.models.signal import Signal, SignalType, SignalSource, SignalStatus, SignalFactor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class TechnicalStrategy:
    """Base class for technical analysis strategies."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_historical_prices(self, instrument_id: int, days: int = 60) -> pd.DataFrame:
        """
        Get historical prices for an instrument.
        
        Returns a DataFrame with OHLCV data.
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get historical prices
        prices = self.db.query(StockPrice).filter(
            StockPrice.instrument_id == instrument_id,
            StockPrice.timestamp >= start_date,
            StockPrice.timestamp <= end_date
        ).order_by(StockPrice.timestamp).all()
        
        if not prices:
            logger.warning(f"No price data found for instrument ID {instrument_id}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'timestamp': p.timestamp,
            'open': p.open,
            'high': p.high,
            'low': p.low,
            'close': p.close,
            'volume': p.volume
        } for p in prices])
        
        return df
    
    def find_atm_options(self, instrument_id: int, current_price: float, option_type: str, days_to_expiration: int = 7) -> Optional[Option]:
        """
        Find at-the-money options for a given instrument.
        """
        target_date = datetime.utcnow().date() + timedelta(days=days_to_expiration)
        min_date = target_date - timedelta(days=2)
        max_date = target_date + timedelta(days=2)
        
        options = self.db.query(Option).filter(
            Option.instrument_id == instrument_id,
            Option.expiration_date >= min_date,
            Option.expiration_date <= max_date,
            Option.option_type == option_type
        ).all()
        
        if not options:
            logger.warning(f"No suitable options found for instrument ID {instrument_id}")
            return None
        
        # Find ATM option
        atm_option = min(options, key=lambda x: abs(x.strike_price - current_price))
        
        return atm_option
    
    def save_signal(self, signal_data: Dict[str, Any]) -> Optional[Signal]:
        """
        Save signal to database.
        """
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
    
    def save_signal_factor(self, signal_id: int, factor_data: Dict[str, Any]) -> Optional[SignalFactor]:
        """
        Save signal factor to database.
        """
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
    
    def generate_signals(self, instrument: Instrument) -> List[Signal]:
        """
        Generate signals for an instrument.
        
        This method should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement generate_signals method")

class RSIStrategy(TechnicalStrategy):
    """Strategy based on Relative Strength Index (RSI)."""
    
    def __init__(self, db: Session, period: int = 14, oversold: float = 30, overbought: float = 70):
        super().__init__(db)
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate RSI for a price DataFrame.
        """
        # Calculate price changes
        delta = df['close'].diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss
        avg_gain = gain.rolling(window=self.period).mean()
        avg_loss = loss.rolling(window=self.period).mean()
        
        # Calculate RS
        rs = avg_gain / avg_loss
        
        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))
        
        # Add to DataFrame
        df['rsi'] = rsi
        
        return df
    
    def generate_signals(self, instrument: Instrument) -> List[Signal]:
        """
        Generate signals based on RSI.
        """
        signals = []
        
        try:
            # Get historical prices
            df = self.get_historical_prices(instrument.id)
            if df.empty:
                return signals
            
            # Calculate RSI
            df = self.calculate_rsi(df)
            
            # Get latest RSI value
            latest_rsi = df['rsi'].iloc[-1]
            
            # Get current price
            current_price = df['close'].iloc[-1]
            
            # Check for oversold condition (bullish signal)
            if latest_rsi < self.oversold:
                # Find ATM call option
                atm_call = self.find_atm_options(instrument.id, current_price, 'call')
                if not atm_call:
                    return signals
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_CALL,
                    'signal_source': SignalSource.TECHNICAL,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 1.05,  # 5% profit target
                    'stop_loss': current_price * 0.97,  # 3% stop loss
                    'confidence_score': (self.oversold - latest_rsi) / self.oversold,  # Higher confidence for lower RSI
                    'time_frame': '7d',
                    'option_id': atm_call.id,
                    'option_strike': atm_call.strike_price,
                    'option_expiration': atm_call.expiration_date,
                    'parameters': {
                        'indicator': 'rsi',
                        'rsi_value': latest_rsi,
                        'rsi_period': self.period
                    },
                    'notes': f"RSI oversold signal for {instrument.symbol}. RSI: {latest_rsi:.2f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'rsi',
                        'factor_value': latest_rsi,
                        'factor_weight': 0.7,
                        'factor_category': 'technical',
                        'factor_description': f"RSI({self.period}) value: {latest_rsi:.2f}"
                    })
                    
                    # Add volume factor
                    volume_change = df['volume'].iloc[-1] / df['volume'].iloc[-5:].mean()
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'volume_change',
                        'factor_value': volume_change,
                        'factor_weight': 0.3,
                        'factor_category': 'technical',
                        'factor_description': f"Volume change: {volume_change:.2f}x average"
                    })
                    
                    signals.append(signal)
            
            # Check for overbought condition (bearish signal)
            elif latest_rsi > self.overbought:
                # Find ATM put option
                atm_put = self.find_atm_options(instrument.id, current_price, 'put')
                if not atm_put:
                    return signals
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_PUT,
                    'signal_source': SignalSource.TECHNICAL,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 0.95,  # 5% profit target
                    'stop_loss': current_price * 1.03,  # 3% stop loss
                    'confidence_score': (latest_rsi - self.overbought) / (100 - self.overbought),  # Higher confidence for higher RSI
                    'time_frame': '7d',
                    'option_id': atm_put.id,
                    'option_strike': atm_put.strike_price,
                    'option_expiration': atm_put.expiration_date,
                    'parameters': {
                        'indicator': 'rsi',
                        'rsi_value': latest_rsi,
                        'rsi_period': self.period
                    },
                    'notes': f"RSI overbought signal for {instrument.symbol}. RSI: {latest_rsi:.2f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'rsi',
                        'factor_value': latest_rsi,
                        'factor_weight': 0.7,
                        'factor_category': 'technical',
                        'factor_description': f"RSI({self.period}) value: {latest_rsi:.2f}"
                    })
                    
                    # Add volume factor
                    volume_change = df['volume'].iloc[-1] / df['volume'].iloc[-5:].mean()
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'volume_change',
                        'factor_value': volume_change,
                        'factor_weight': 0.3,
                        'factor_category': 'technical',
                        'factor_description': f"Volume change: {volume_change:.2f}x average"
                    })
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error generating RSI signals for {instrument.symbol}: {e}")
        
        return signals

class MACDStrategy(TechnicalStrategy):
    """Strategy based on Moving Average Convergence Divergence (MACD)."""
    
    def __init__(self, db: Session, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__(db)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MACD for a price DataFrame.
        """
        # Calculate EMA
        exp1 = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        exp2 = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        
        # Calculate MACD line
        macd = exp1 - exp2
        
        # Calculate signal line
        signal = macd.ewm(span=self.signal_period, adjust=False).mean()
        
        # Calculate histogram
        histogram = macd - signal
        
        # Add to DataFrame
        df['macd'] = macd
        df['signal'] = signal
        df['histogram'] = histogram
        
        return df
    
    def generate_signals(self, instrument: Instrument) -> List[Signal]:
        """
        Generate signals based on MACD.
        """
        signals = []
        
        try:
            # Get historical prices
            df = self.get_historical_prices(instrument.id)
            if df.empty:
                return signals
            
            # Calculate MACD
            df = self.calculate_macd(df)
            
            # Get current price
            current_price = df['close'].iloc[-1]
            
            # Check for bullish crossover
            if df['macd'].iloc[-2] < df['signal'].iloc[-2] and df['macd'].iloc[-1] > df['signal'].iloc[-1]:
                # Find ATM call option
                atm_call = self.find_atm_options(instrument.id, current_price, 'call')
                if not atm_call:
                    return signals
                
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
                    'option_id': atm_call.id,
                    'option_strike': atm_call.strike_price,
                    'option_expiration': atm_call.expiration_date,
                    'parameters': {
                        'indicator': 'macd',
                        'macd_value': df['macd'].iloc[-1],
                        'signal_value': df['signal'].iloc[-1],
                        'histogram_value': df['histogram'].iloc[-1]
                    },
                    'notes': f"MACD bullish crossover for {instrument.symbol}. MACD: {df['macd'].iloc[-1]:.4f}, Signal: {df['signal'].iloc[-1]:.4f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'macd_crossover',
                        'factor_value': 1.0,  # Bullish crossover
                        'factor_weight': 0.6,
                        'factor_category': 'technical',
                        'factor_description': f"MACD bullish crossover. MACD: {df['macd'].iloc[-1]:.4f}, Signal: {df['signal'].iloc[-1]:.4f}"
                    })
                    
                    # Add histogram factor
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'macd_histogram',
                        'factor_value': df['histogram'].iloc[-1],
                        'factor_weight': 0.4,
                        'factor_category': 'technical',
                        'factor_description': f"MACD histogram: {df['histogram'].iloc[-1]:.4f}"
                    })
                    
                    signals.append(signal)
            
            # Check for bearish crossover
            elif df['macd'].iloc[-2] > df['signal'].iloc[-2] and df['macd'].iloc[-1] < df['signal'].iloc[-1]:
                # Find ATM put option
                atm_put = self.find_atm_options(instrument.id, current_price, 'put')
                if not atm_put:
                    return signals
                
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
                    'option_id': atm_put.id,
                    'option_strike': atm_put.strike_price,
                    'option_expiration': atm_put.expiration_date,
                    'parameters': {
                        'indicator': 'macd',
                        'macd_value': df['macd'].iloc[-1],
                        'signal_value': df['signal'].iloc[-1],
                        'histogram_value': df['histogram'].iloc[-1]
                    },
                    'notes': f"MACD bearish crossover for {instrument.symbol}. MACD: {df['macd'].iloc[-1]:.4f}, Signal: {df['signal'].iloc[-1]:.4f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'macd_crossover',
                        'factor_value': -1.0,  # Bearish crossover
                        'factor_weight': 0.6,
                        'factor_category': 'technical',
                        'factor_description': f"MACD bearish crossover. MACD: {df['macd'].iloc[-1]:.4f}, Signal: {df['signal'].iloc[-1]:.4f}"
                    })
                    
                    # Add histogram factor
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'macd_histogram',
                        'factor_value': df['histogram'].iloc[-1],
                        'factor_weight': 0.4,
                        'factor_category': 'technical',
                        'factor_description': f"MACD histogram: {df['histogram'].iloc[-1]:.4f}"
                    })
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error generating MACD signals for {instrument.symbol}: {e}")
        
        return signals

class BollingerBandsStrategy(TechnicalStrategy):
    """Strategy based on Bollinger Bands."""
    
    def __init__(self, db: Session, period: int = 20, std_dev: float = 2.0):
        super().__init__(db)
        self.period = period
        self.std_dev = std_dev
    
    def calculate_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Bollinger Bands for a price DataFrame.
        """
        # Calculate SMA
        df['sma'] = df['close'].rolling(window=self.period).mean()
        
        # Calculate standard deviation
        df['std'] = df['close'].rolling(window=self.period).std()
        
        # Calculate upper and lower bands
        df['upper_band'] = df['sma'] + (df['std'] * self.std_dev)
        df['lower_band'] = df['sma'] - (df['std'] * self.std_dev)
        
        # Calculate bandwidth
        df['bandwidth'] = (df['upper_band'] - df['lower_band']) / df['sma']
        
        # Calculate %B
        df['percent_b'] = (df['close'] - df['lower_band']) / (df['upper_band'] - df['lower_band'])
        
        return df
    
    def generate_signals(self, instrument: Instrument) -> List[Signal]:
        """
        Generate signals based on Bollinger Bands.
        """
        signals = []
        
        try:
            # Get historical prices
            df = self.get_historical_prices(instrument.id)
            if df.empty:
                return signals
            
            # Calculate Bollinger Bands
            df = self.calculate_bollinger_bands(df)
            
            # Get current price
            current_price = df['close'].iloc[-1]
            
            # Check for price crossing below lower band (bullish)
            if df['close'].iloc[-2] > df['lower_band'].iloc[-2] and df['close'].iloc[-1] < df['lower_band'].iloc[-1]:
                # Find ATM call option
                atm_call = self.find_atm_options(instrument.id, current_price, 'call')
                if not atm_call:
                    return signals
                
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
                    'option_id': atm_call.id,
                    'option_strike': atm_call.strike_price,
                    'option_expiration': atm_call.expiration_date,
                    'parameters': {
                        'indicator': 'bollinger_bands',
                        'sma_value': df['sma'].iloc[-1],
                        'upper_band_value': df['upper_band'].iloc[-1],
                        'lower_band_value': df['lower_band'].iloc[-1],
                        'percent_b': df['percent_b'].iloc[-1],
                        'bandwidth': df['bandwidth'].iloc[-1]
                    },
                    'notes': f"Bollinger Band lower band break for {instrument.symbol}. Price: {current_price:.2f}, Lower Band: {df['lower_band'].iloc[-1]:.2f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'percent_b',
                        'factor_value': df['percent_b'].iloc[-1],
                        'factor_weight': 0.5,
                        'factor_category': 'technical',
                        'factor_description': f"Percent B: {df['percent_b'].iloc[-1]:.4f}"
                    })
                    
                    # Add bandwidth factor
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'bandwidth',
                        'factor_value': df['bandwidth'].iloc[-1],
                        'factor_weight': 0.3,
                        'factor_category': 'technical',
                        'factor_description': f"Bandwidth: {df['bandwidth'].iloc[-1]:.4f}"
                    })
                    
                    # Add volatility factor
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'volatility',
                        'factor_value': df['std'].iloc[-1] / df['close'].iloc[-1],
                        'factor_weight': 0.2,
                        'factor_category': 'technical',
                        'factor_description': f"Volatility: {(df['std'].iloc[-1] / df['close'].iloc[-1]):.4f}"
                    })
                    
                    signals.append(signal)
            
            # Check for price crossing above upper band (bearish)
            elif df['close'].iloc[-2] < df['upper_band'].iloc[-2] and df['close'].iloc[-1] > df['upper_band'].iloc[-1]:
                # Find ATM put option
                atm_put = self.find_atm_options(instrument.id, current_price, 'put')
                if not atm_put:
                    return signals
                
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
                    'option_id': atm_put.id,
                    'option_strike': atm_put.strike_price,
                    'option_expiration': atm_put.expiration_date,
                    'parameters': {
                        'indicator': 'bollinger_bands',
                        'sma_value': df['sma'].iloc[-1],
                        'upper_band_value': df['upper_band'].iloc[-1],
                        'lower_band_value': df['lower_band'].iloc[-1],
                        'percent_b': df['percent_b'].iloc[-1],
                        'bandwidth': df['bandwidth'].iloc[-1]
                    },
                    'notes': f"Bollinger Band upper band break for {instrument.symbol}. Price: {current_price:.2f}, Upper Band: {df['upper_band'].iloc[-1]:.2f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'percent_b',
                        'factor_value': df['percent_b'].iloc[-1],
                        'factor_weight': 0.5,
                        'factor_category': 'technical',
                        'factor_description': f"Percent B: {df['percent_b'].iloc[-1]:.4f}"
                    })
                    
                    # Add bandwidth factor
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'bandwidth',
                        'factor_value': df['bandwidth'].iloc[-1],
                        'factor_weight': 0.3,
                        'factor_category': 'technical',
                        'factor_description': f"Bandwidth: {df['bandwidth'].iloc[-1]:.4f}"
                    })
                    
                    # Add volatility factor
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'volatility',
                        'factor_value': df['std'].iloc[-1] / df['close'].iloc[-1],
                        'factor_weight': 0.2,
                        'factor_category': 'technical',
                        'factor_description': f"Volatility: {(df['std'].iloc[-1] / df['close'].iloc[-1]):.4f}"
                    })
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error generating Bollinger Bands signals for {instrument.symbol}: {e}")
        
        return signals

class MomentumStrategy(TechnicalStrategy):
    """Strategy based on price momentum."""
    
    def __init__(self, db: Session, period: int = 10, threshold: float = 0.05):
        super().__init__(db)
        self.period = period
        self.threshold = threshold
    
    def calculate_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate momentum indicators for a price DataFrame.
        """
        # Calculate ROC (Rate of Change)
        df['roc'] = df['close'].pct_change(periods=self.period) * 100
        
        # Calculate momentum
        df['momentum'] = df['close'] / df['close'].shift(self.period) - 1
        
        # Calculate ADX (Average Directional Index)
        # This is a simplified version
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean()
        
        # Calculate +DI and -DI
        up_move = df['high'] - df['high'].shift()
        down_move = df['low'].shift() - df['low']
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        plus_di = 100 * pd.Series(plus_dm).rolling(window=14).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).rolling(window=14).mean() / atr
        
        # Calculate ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=14).mean()
        
        df['adx'] = adx
        df['plus_di'] = plus_di
        df['minus_di'] = minus_di
        
        return df
    
    def generate_signals(self, instrument: Instrument) -> List[Signal]:
        """
        Generate signals based on momentum.
        """
        signals = []
        
        try:
            # Get historical prices
            df = self.get_historical_prices(instrument.id)
            if df.empty:
                return signals
            
            # Calculate momentum indicators
            df = self.calculate_momentum(df)
            
            # Get current price
            current_price = df['close'].iloc[-1]
            
            # Check for strong positive momentum
            if df['momentum'].iloc[-1] > self.threshold and df['adx'].iloc[-1] > 25 and df['plus_di'].iloc[-1] > df['minus_di'].iloc[-1]:
                # Find ATM call option
                atm_call = self.find_atm_options(instrument.id, current_price, 'call')
                if not atm_call:
                    return signals
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_CALL,
                    'signal_source': SignalSource.MOMENTUM,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * (1 + 2 * self.threshold),  # 2x threshold as profit target
                    'stop_loss': current_price * (1 - self.threshold),  # threshold as stop loss
                    'confidence_score': min(0.9, df['momentum'].iloc[-1] / (2 * self.threshold)),  # Scale confidence based on momentum
                    'time_frame': '7d',
                    'option_id': atm_call.id,
                    'option_strike': atm_call.strike_price,
                    'option_expiration': atm_call.expiration_date,
                    'parameters': {
                        'indicator': 'momentum',
                        'momentum_value': df['momentum'].iloc[-1],
                        'roc_value': df['roc'].iloc[-1],
                        'adx_value': df['adx'].iloc[-1],
                        'plus_di': df['plus_di'].iloc[-1],
                        'minus_di': df['minus_di'].iloc[-1]
                    },
                    'notes': f"Strong bullish momentum for {instrument.symbol}. Momentum: {df['momentum'].iloc[-1]:.4f}, ADX: {df['adx'].iloc[-1]:.2f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'momentum',
                        'factor_value': df['momentum'].iloc[-1],
                        'factor_weight': 0.4,
                        'factor_category': 'technical',
                        'factor_description': f"Momentum: {df['momentum'].iloc[-1]:.4f}"
                    })
                    
                    # Add ADX factor
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'adx',
                        'factor_value': df['adx'].iloc[-1],
                        'factor_weight': 0.3,
                        'factor_category': 'technical',
                        'factor_description': f"ADX: {df['adx'].iloc[-1]:.2f}"
                    })
                    
                    # Add directional indicator factor
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'directional_indicator',
                        'factor_value': df['plus_di'].iloc[-1] - df['minus_di'].iloc[-1],
                        'factor_weight': 0.3,
                        'factor_category': 'technical',
                        'factor_description': f"Directional Indicator: {df['plus_di'].iloc[-1] - df['minus_di'].iloc[-1]:.2f}"
                    })
                    
                    signals.append(signal)
            
            # Check for strong negative momentum
            elif df['momentum'].iloc[-1] < -self.threshold and df['adx'].iloc[-1] > 25 and df['minus_di'].iloc[-1] > df['plus_di'].iloc[-1]:
                # Find ATM put option
                atm_put = self.find_atm_options(instrument.id, current_price, 'put')
                if not atm_put:
                    return signals
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_PUT,
                    'signal_source': SignalSource.MOMENTUM,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * (1 - 2 * self.threshold),  # 2x threshold as profit target
                    'stop_loss': current_price * (1 + self.threshold),  # threshold as stop loss
                    'confidence_score': min(0.9, abs(df['momentum'].iloc[-1]) / (2 * self.threshold)),  # Scale confidence based on momentum
                    'time_frame': '7d',
                    'option_id': atm_put.id,
                    'option_strike': atm_put.strike_price,
                    'option_expiration': atm_put.expiration_date,
                    'parameters': {
                        'indicator': 'momentum',
                        'momentum_value': df['momentum'].iloc[-1],
                        'roc_value': df['roc'].iloc[-1],
                        'adx_value': df['adx'].iloc[-1],
                        'plus_di': df['plus_di'].iloc[-1],
                        'minus_di': df['minus_di'].iloc[-1]
                    },
                    'notes': f"Strong bearish momentum for {instrument.symbol}. Momentum: {df['momentum'].iloc[-1]:.4f}, ADX: {df['adx'].iloc[-1]:.2f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'momentum',
                        'factor_value': df['momentum'].iloc[-1],
                        'factor_weight': 0.4,
                        'factor_category': 'technical',
                        'factor_description': f"Momentum: {df['momentum'].iloc[-1]:.4f}"
                    })
                    
                    # Add ADX factor
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'adx',
                        'factor_value': df['adx'].iloc[-1],
                        'factor_weight': 0.3,
                        'factor_category': 'technical',
                        'factor_description': f"ADX: {df['adx'].iloc[-1]:.2f}"
                    })
                    
                    # Add directional indicator factor
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'directional_indicator',
                        'factor_value': df['minus_di'].iloc[-1] - df['plus_di'].iloc[-1],
                        'factor_weight': 0.3,
                        'factor_category': 'technical',
                        'factor_description': f"Directional Indicator: {df['minus_di'].iloc[-1] - df['plus_di'].iloc[-1]:.2f}"
                    })
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error generating momentum signals for {instrument.symbol}: {e}")
        
        return signals

