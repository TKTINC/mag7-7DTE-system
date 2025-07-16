import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session

from app.models.market_data import Instrument, Option
from app.models.signal import Signal, SignalType, SignalSource, SignalStatus, SignalFactor

from app.services.signal_strategies.technical_strategies import (
    RSIStrategy, MACDStrategy, BollingerBandsStrategy, MomentumStrategy
)
from app.services.signal_strategies.fundamental_strategies import (
    EarningsStrategy, ValuationStrategy, AnalystRatingStrategy
)
from app.services.signal_strategies.volatility_strategies import (
    IVPercentileStrategy, IVSkewStrategy, VolatilitySurfaceStrategy
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class EnsembleStrategy:
    """
    Ensemble strategy that combines signals from multiple strategies.
    """
    
    def __init__(self, db: Session, min_confidence: float = 0.6, min_strategies: int = 2):
        self.db = db
        self.min_confidence = min_confidence
        self.min_strategies = min_strategies
        
        # Initialize individual strategies
        self.strategies = {
            # Technical strategies
            'rsi': RSIStrategy(db),
            'macd': MACDStrategy(db),
            'bollinger': BollingerBandsStrategy(db),
            'momentum': MomentumStrategy(db),
            
            # Fundamental strategies
            'earnings': EarningsStrategy(db),
            'valuation': ValuationStrategy(db),
            'analyst': AnalystRatingStrategy(db),
            
            # Volatility strategies
            'iv_percentile': IVPercentileStrategy(db),
            'iv_skew': IVSkewStrategy(db),
            'vol_surface': VolatilitySurfaceStrategy(db)
        }
    
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
        Generate signals using an ensemble of strategies.
        """
        all_signals = []
        
        try:
            # Get current price
            current_price = instrument.last_price
            if not current_price:
                return all_signals
            
            # Collect signals from all strategies
            strategy_signals = {}
            
            for name, strategy in self.strategies.items():
                try:
                    signals = strategy.generate_signals(instrument)
                    if signals:
                        strategy_signals[name] = signals
                except Exception as e:
                    logger.error(f"Error generating signals for strategy {name}: {e}")
            
            # Group signals by type
            call_signals = []
            put_signals = []
            
            for strategy_name, signals in strategy_signals.items():
                for signal in signals:
                    if signal.signal_type == SignalType.LONG_CALL:
                        call_signals.append((strategy_name, signal))
                    elif signal.signal_type == SignalType.LONG_PUT:
                        put_signals.append((strategy_name, signal))
            
            # Generate ensemble signals for calls
            if len(call_signals) >= self.min_strategies:
                # Calculate average confidence
                avg_confidence = sum(s.confidence_score for _, s in call_signals) / len(call_signals)
                
                if avg_confidence >= self.min_confidence:
                    # Find ATM call option
                    atm_call = self.find_atm_options(instrument.id, current_price, 'call')
                    if not atm_call:
                        return all_signals
                    
                    # Calculate target price and stop loss
                    target_prices = [s.target_price for _, s in call_signals if s.target_price is not None]
                    stop_losses = [s.stop_loss for _, s in call_signals if s.stop_loss is not None]
                    
                    target_price = sum(target_prices) / len(target_prices) if target_prices else current_price * 1.05
                    stop_loss = sum(stop_losses) / len(stop_losses) if stop_losses else current_price * 0.97
                    
                    # Create ensemble signal
                    signal_data = {
                        'instrument_id': instrument.id,
                        'signal_type': SignalType.LONG_CALL,
                        'signal_source': SignalSource.ENSEMBLE,
                        'status': SignalStatus.PENDING,
                        'entry_price': None,  # Will be set when executed
                        'target_price': target_price,
                        'stop_loss': stop_loss,
                        'confidence_score': avg_confidence,
                        'time_frame': '7d',
                        'option_id': atm_call.id,
                        'option_strike': atm_call.strike_price,
                        'option_expiration': atm_call.expiration_date,
                        'parameters': {
                            'indicator': 'ensemble',
                            'strategies': [name for name, _ in call_signals],
                            'strategy_count': len(call_signals),
                            'avg_confidence': avg_confidence
                        },
                        'notes': f"Ensemble bullish signal for {instrument.symbol}. {len(call_signals)} strategies with avg confidence {avg_confidence:.2f}"
                    }
                    
                    # Save signal
                    signal = self.save_signal(signal_data)
                    if signal:
                        # Save signal factors
                        for i, (strategy_name, strategy_signal) in enumerate(call_signals):
                            # Add strategy factor
                            self.save_signal_factor(signal.id, {
                                'factor_name': f"strategy_{strategy_name}",
                                'factor_value': strategy_signal.confidence_score,
                                'factor_weight': 1.0 / len(call_signals),
                                'factor_category': 'ensemble',
                                'factor_description': f"Strategy: {strategy_name}, Confidence: {strategy_signal.confidence_score:.2f}"
                            })
                            
                            # Add strategy source factor
                            self.save_signal_factor(signal.id, {
                                'factor_name': f"source_{strategy_signal.signal_source.value}",
                                'factor_value': 1.0,
                                'factor_weight': 0.0,  # Informational only
                                'factor_category': 'ensemble',
                                'factor_description': f"Signal source: {strategy_signal.signal_source.value}"
                            })
                        
                        all_signals.append(signal)
            
            # Generate ensemble signals for puts
            if len(put_signals) >= self.min_strategies:
                # Calculate average confidence
                avg_confidence = sum(s.confidence_score for _, s in put_signals) / len(put_signals)
                
                if avg_confidence >= self.min_confidence:
                    # Find ATM put option
                    atm_put = self.find_atm_options(instrument.id, current_price, 'put')
                    if not atm_put:
                        return all_signals
                    
                    # Calculate target price and stop loss
                    target_prices = [s.target_price for _, s in put_signals if s.target_price is not None]
                    stop_losses = [s.stop_loss for _, s in put_signals if s.stop_loss is not None]
                    
                    target_price = sum(target_prices) / len(target_prices) if target_prices else current_price * 0.95
                    stop_loss = sum(stop_losses) / len(stop_losses) if stop_losses else current_price * 1.03
                    
                    # Create ensemble signal
                    signal_data = {
                        'instrument_id': instrument.id,
                        'signal_type': SignalType.LONG_PUT,
                        'signal_source': SignalSource.ENSEMBLE,
                        'status': SignalStatus.PENDING,
                        'entry_price': None,  # Will be set when executed
                        'target_price': target_price,
                        'stop_loss': stop_loss,
                        'confidence_score': avg_confidence,
                        'time_frame': '7d',
                        'option_id': atm_put.id,
                        'option_strike': atm_put.strike_price,
                        'option_expiration': atm_put.expiration_date,
                        'parameters': {
                            'indicator': 'ensemble',
                            'strategies': [name for name, _ in put_signals],
                            'strategy_count': len(put_signals),
                            'avg_confidence': avg_confidence
                        },
                        'notes': f"Ensemble bearish signal for {instrument.symbol}. {len(put_signals)} strategies with avg confidence {avg_confidence:.2f}"
                    }
                    
                    # Save signal
                    signal = self.save_signal(signal_data)
                    if signal:
                        # Save signal factors
                        for i, (strategy_name, strategy_signal) in enumerate(put_signals):
                            # Add strategy factor
                            self.save_signal_factor(signal.id, {
                                'factor_name': f"strategy_{strategy_name}",
                                'factor_value': strategy_signal.confidence_score,
                                'factor_weight': 1.0 / len(put_signals),
                                'factor_category': 'ensemble',
                                'factor_description': f"Strategy: {strategy_name}, Confidence: {strategy_signal.confidence_score:.2f}"
                            })
                            
                            # Add strategy source factor
                            self.save_signal_factor(signal.id, {
                                'factor_name': f"source_{strategy_signal.signal_source.value}",
                                'factor_value': 1.0,
                                'factor_weight': 0.0,  # Informational only
                                'factor_category': 'ensemble',
                                'factor_description': f"Signal source: {strategy_signal.signal_source.value}"
                            })
                        
                        all_signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error generating ensemble signals for {instrument.symbol}: {e}")
        
        return all_signals

class WeightedEnsembleStrategy(EnsembleStrategy):
    """
    Weighted ensemble strategy that assigns different weights to different strategies.
    """
    
    def __init__(self, db: Session, min_confidence: float = 0.6, min_strategies: int = 2):
        super().__init__(db, min_confidence, min_strategies)
        
        # Define strategy weights
        self.strategy_weights = {
            # Technical strategies
            'rsi': 0.7,
            'macd': 0.8,
            'bollinger': 0.6,
            'momentum': 0.7,
            
            # Fundamental strategies
            'earnings': 0.9,
            'valuation': 0.8,
            'analyst': 0.7,
            
            # Volatility strategies
            'iv_percentile': 0.8,
            'iv_skew': 0.7,
            'vol_surface': 0.6
        }
        
        # Define source weights
        self.source_weights = {
            SignalSource.TECHNICAL: 0.7,
            SignalSource.FUNDAMENTAL: 0.9,
            SignalSource.VOLATILITY: 0.8,
            SignalSource.MOMENTUM: 0.7,
            SignalSource.ENSEMBLE: 0.0  # Not used for input
        }
    
    def calculate_weighted_confidence(self, signals: List[Tuple[str, Signal]]) -> float:
        """
        Calculate weighted confidence score for a list of signals.
        """
        if not signals:
            return 0.0
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for strategy_name, signal in signals:
            # Get strategy weight
            strategy_weight = self.strategy_weights.get(strategy_name, 0.5)
            
            # Get source weight
            source_weight = self.source_weights.get(signal.signal_source, 0.5)
            
            # Calculate combined weight
            combined_weight = (strategy_weight + source_weight) / 2.0
            
            # Add to weighted sum
            weighted_sum += signal.confidence_score * combined_weight
            total_weight += combined_weight
        
        # Calculate weighted average
        if total_weight > 0:
            return weighted_sum / total_weight
        else:
            return 0.0
    
    def generate_signals(self, instrument: Instrument) -> List[Signal]:
        """
        Generate signals using a weighted ensemble of strategies.
        """
        all_signals = []
        
        try:
            # Get current price
            current_price = instrument.last_price
            if not current_price:
                return all_signals
            
            # Collect signals from all strategies
            strategy_signals = {}
            
            for name, strategy in self.strategies.items():
                try:
                    signals = strategy.generate_signals(instrument)
                    if signals:
                        strategy_signals[name] = signals
                except Exception as e:
                    logger.error(f"Error generating signals for strategy {name}: {e}")
            
            # Group signals by type
            call_signals = []
            put_signals = []
            
            for strategy_name, signals in strategy_signals.items():
                for signal in signals:
                    if signal.signal_type == SignalType.LONG_CALL:
                        call_signals.append((strategy_name, signal))
                    elif signal.signal_type == SignalType.LONG_PUT:
                        put_signals.append((strategy_name, signal))
            
            # Generate ensemble signals for calls
            if len(call_signals) >= self.min_strategies:
                # Calculate weighted confidence
                weighted_confidence = self.calculate_weighted_confidence(call_signals)
                
                if weighted_confidence >= self.min_confidence:
                    # Find ATM call option
                    atm_call = self.find_atm_options(instrument.id, current_price, 'call')
                    if not atm_call:
                        return all_signals
                    
                    # Calculate target price and stop loss
                    target_prices = [s.target_price for _, s in call_signals if s.target_price is not None]
                    stop_losses = [s.stop_loss for _, s in call_signals if s.stop_loss is not None]
                    
                    target_price = sum(target_prices) / len(target_prices) if target_prices else current_price * 1.05
                    stop_loss = sum(stop_losses) / len(stop_losses) if stop_losses else current_price * 0.97
                    
                    # Create ensemble signal
                    signal_data = {
                        'instrument_id': instrument.id,
                        'signal_type': SignalType.LONG_CALL,
                        'signal_source': SignalSource.ENSEMBLE,
                        'status': SignalStatus.PENDING,
                        'entry_price': None,  # Will be set when executed
                        'target_price': target_price,
                        'stop_loss': stop_loss,
                        'confidence_score': weighted_confidence,
                        'time_frame': '7d',
                        'option_id': atm_call.id,
                        'option_strike': atm_call.strike_price,
                        'option_expiration': atm_call.expiration_date,
                        'parameters': {
                            'indicator': 'weighted_ensemble',
                            'strategies': [name for name, _ in call_signals],
                            'strategy_count': len(call_signals),
                            'weighted_confidence': weighted_confidence
                        },
                        'notes': f"Weighted ensemble bullish signal for {instrument.symbol}. {len(call_signals)} strategies with weighted confidence {weighted_confidence:.2f}"
                    }
                    
                    # Save signal
                    signal = self.save_signal(signal_data)
                    if signal:
                        # Save signal factors
                        for i, (strategy_name, strategy_signal) in enumerate(call_signals):
                            # Get strategy weight
                            strategy_weight = self.strategy_weights.get(strategy_name, 0.5)
                            
                            # Get source weight
                            source_weight = self.source_weights.get(strategy_signal.signal_source, 0.5)
                            
                            # Calculate combined weight
                            combined_weight = (strategy_weight + source_weight) / 2.0
                            
                            # Add strategy factor
                            self.save_signal_factor(signal.id, {
                                'factor_name': f"strategy_{strategy_name}",
                                'factor_value': strategy_signal.confidence_score,
                                'factor_weight': combined_weight,
                                'factor_category': 'ensemble',
                                'factor_description': f"Strategy: {strategy_name}, Confidence: {strategy_signal.confidence_score:.2f}, Weight: {combined_weight:.2f}"
                            })
                            
                            # Add strategy source factor
                            self.save_signal_factor(signal.id, {
                                'factor_name': f"source_{strategy_signal.signal_source.value}",
                                'factor_value': source_weight,
                                'factor_weight': 0.0,  # Informational only
                                'factor_category': 'ensemble',
                                'factor_description': f"Signal source: {strategy_signal.signal_source.value}, Weight: {source_weight:.2f}"
                            })
                        
                        all_signals.append(signal)
            
            # Generate ensemble signals for puts
            if len(put_signals) >= self.min_strategies:
                # Calculate weighted confidence
                weighted_confidence = self.calculate_weighted_confidence(put_signals)
                
                if weighted_confidence >= self.min_confidence:
                    # Find ATM put option
                    atm_put = self.find_atm_options(instrument.id, current_price, 'put')
                    if not atm_put:
                        return all_signals
                    
                    # Calculate target price and stop loss
                    target_prices = [s.target_price for _, s in put_signals if s.target_price is not None]
                    stop_losses = [s.stop_loss for _, s in put_signals if s.stop_loss is not None]
                    
                    target_price = sum(target_prices) / len(target_prices) if target_prices else current_price * 0.95
                    stop_loss = sum(stop_losses) / len(stop_losses) if stop_losses else current_price * 1.03
                    
                    # Create ensemble signal
                    signal_data = {
                        'instrument_id': instrument.id,
                        'signal_type': SignalType.LONG_PUT,
                        'signal_source': SignalSource.ENSEMBLE,
                        'status': SignalStatus.PENDING,
                        'entry_price': None,  # Will be set when executed
                        'target_price': target_price,
                        'stop_loss': stop_loss,
                        'confidence_score': weighted_confidence,
                        'time_frame': '7d',
                        'option_id': atm_put.id,
                        'option_strike': atm_put.strike_price,
                        'option_expiration': atm_put.expiration_date,
                        'parameters': {
                            'indicator': 'weighted_ensemble',
                            'strategies': [name for name, _ in put_signals],
                            'strategy_count': len(put_signals),
                            'weighted_confidence': weighted_confidence
                        },
                        'notes': f"Weighted ensemble bearish signal for {instrument.symbol}. {len(put_signals)} strategies with weighted confidence {weighted_confidence:.2f}"
                    }
                    
                    # Save signal
                    signal = self.save_signal(signal_data)
                    if signal:
                        # Save signal factors
                        for i, (strategy_name, strategy_signal) in enumerate(put_signals):
                            # Get strategy weight
                            strategy_weight = self.strategy_weights.get(strategy_name, 0.5)
                            
                            # Get source weight
                            source_weight = self.source_weights.get(strategy_signal.signal_source, 0.5)
                            
                            # Calculate combined weight
                            combined_weight = (strategy_weight + source_weight) / 2.0
                            
                            # Add strategy factor
                            self.save_signal_factor(signal.id, {
                                'factor_name': f"strategy_{strategy_name}",
                                'factor_value': strategy_signal.confidence_score,
                                'factor_weight': combined_weight,
                                'factor_category': 'ensemble',
                                'factor_description': f"Strategy: {strategy_name}, Confidence: {strategy_signal.confidence_score:.2f}, Weight: {combined_weight:.2f}"
                            })
                            
                            # Add strategy source factor
                            self.save_signal_factor(signal.id, {
                                'factor_name': f"source_{strategy_signal.signal_source.value}",
                                'factor_value': source_weight,
                                'factor_weight': 0.0,  # Informational only
                                'factor_category': 'ensemble',
                                'factor_description': f"Signal source: {strategy_signal.signal_source.value}, Weight: {source_weight:.2f}"
                            })
                        
                        all_signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error generating weighted ensemble signals for {instrument.symbol}: {e}")
        
        return all_signals

