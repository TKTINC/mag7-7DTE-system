import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session

from app.models.market_data import (
    Instrument, StockPrice, Option, OptionPriceData, VolatilityData
)
from app.models.signal import Signal, SignalType, SignalSource, SignalStatus, SignalFactor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class VolatilityStrategy:
    """Base class for volatility-based strategies."""
    
    def __init__(self, db: Session):
        self.db = db
    
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

class IVPercentileStrategy(VolatilityStrategy):
    """Strategy based on implied volatility percentile."""
    
    def __init__(self, db: Session, low_threshold: float = 20.0, high_threshold: float = 80.0):
        super().__init__(db)
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold
    
    def get_volatility_data(self, instrument: Instrument) -> Optional[VolatilityData]:
        """
        Get latest volatility data for an instrument.
        """
        volatility_data = self.db.query(VolatilityData).filter(
            VolatilityData.instrument_id == instrument.id
        ).order_by(VolatilityData.date.desc()).first()
        
        return volatility_data
    
    def generate_signals(self, instrument: Instrument) -> List[Signal]:
        """
        Generate signals based on implied volatility percentile.
        """
        signals = []
        
        try:
            # Get current price
            current_price = instrument.last_price
            if not current_price:
                return signals
            
            # Get volatility data
            volatility_data = self.get_volatility_data(instrument)
            if not volatility_data or volatility_data.iv_percentile is None:
                return signals
            
            # Check for low IV percentile (bullish for long calls)
            if volatility_data.iv_percentile < self.low_threshold:
                # Find ATM call option
                atm_call = self.find_atm_options(instrument.id, current_price, 'call')
                if not atm_call:
                    return signals
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_CALL,
                    'signal_source': SignalSource.VOLATILITY,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 1.05,  # 5% profit target
                    'stop_loss': current_price * 0.97,  # 3% stop loss
                    'confidence_score': 0.6 + ((self.low_threshold - volatility_data.iv_percentile) / self.low_threshold * 0.3),  # Scale confidence based on IV percentile
                    'time_frame': '7d',
                    'option_id': atm_call.id,
                    'option_strike': atm_call.strike_price,
                    'option_expiration': atm_call.expiration_date,
                    'parameters': {
                        'indicator': 'iv_percentile',
                        'iv_percentile': volatility_data.iv_percentile,
                        'iv_rank': volatility_data.iv_rank,
                        'iv_avg': volatility_data.implied_volatility_avg,
                        'iv_min': volatility_data.implied_volatility_min,
                        'iv_max': volatility_data.implied_volatility_max
                    },
                    'notes': f"Low IV percentile for {instrument.symbol}. IV percentile: {volatility_data.iv_percentile:.2f}%"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'iv_percentile',
                        'factor_value': volatility_data.iv_percentile,
                        'factor_weight': 0.6,
                        'factor_category': 'volatility',
                        'factor_description': f"IV percentile: {volatility_data.iv_percentile:.2f}%"
                    })
                    
                    # Add IV rank factor
                    if volatility_data.iv_rank is not None:
                        self.save_signal_factor(signal.id, {
                            'factor_name': 'iv_rank',
                            'factor_value': volatility_data.iv_rank,
                            'factor_weight': 0.4,
                            'factor_category': 'volatility',
                            'factor_description': f"IV rank: {volatility_data.iv_rank:.2f}%"
                        })
                    
                    signals.append(signal)
            
            # Check for high IV percentile (bullish for long puts)
            elif volatility_data.iv_percentile > self.high_threshold:
                # Find ATM put option
                atm_put = self.find_atm_options(instrument.id, current_price, 'put')
                if not atm_put:
                    return signals
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_PUT,
                    'signal_source': SignalSource.VOLATILITY,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 0.95,  # 5% profit target
                    'stop_loss': current_price * 1.03,  # 3% stop loss
                    'confidence_score': 0.6 + ((volatility_data.iv_percentile - self.high_threshold) / (100 - self.high_threshold) * 0.3),  # Scale confidence based on IV percentile
                    'time_frame': '7d',
                    'option_id': atm_put.id,
                    'option_strike': atm_put.strike_price,
                    'option_expiration': atm_put.expiration_date,
                    'parameters': {
                        'indicator': 'iv_percentile',
                        'iv_percentile': volatility_data.iv_percentile,
                        'iv_rank': volatility_data.iv_rank,
                        'iv_avg': volatility_data.implied_volatility_avg,
                        'iv_min': volatility_data.implied_volatility_min,
                        'iv_max': volatility_data.implied_volatility_max
                    },
                    'notes': f"High IV percentile for {instrument.symbol}. IV percentile: {volatility_data.iv_percentile:.2f}%"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'iv_percentile',
                        'factor_value': volatility_data.iv_percentile,
                        'factor_weight': 0.6,
                        'factor_category': 'volatility',
                        'factor_description': f"IV percentile: {volatility_data.iv_percentile:.2f}%"
                    })
                    
                    # Add IV rank factor
                    if volatility_data.iv_rank is not None:
                        self.save_signal_factor(signal.id, {
                            'factor_name': 'iv_rank',
                            'factor_value': volatility_data.iv_rank,
                            'factor_weight': 0.4,
                            'factor_category': 'volatility',
                            'factor_description': f"IV rank: {volatility_data.iv_rank:.2f}%"
                        })
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error generating IV percentile signals for {instrument.symbol}: {e}")
        
        return signals

class IVSkewStrategy(VolatilityStrategy):
    """Strategy based on implied volatility skew."""
    
    def __init__(self, db: Session, skew_threshold: float = 0.15):
        super().__init__(db)
        self.skew_threshold = skew_threshold
    
    def calculate_iv_skew(self, instrument: Instrument) -> Optional[Dict[str, float]]:
        """
        Calculate implied volatility skew for an instrument.
        
        IV skew is the difference between put and call implied volatilities
        at equidistant strikes from the current price.
        """
        try:
            # Get current price
            current_price = instrument.last_price
            if not current_price:
                return None
            
            # Get options expiring in ~7 days
            target_date = datetime.utcnow().date() + timedelta(days=7)
            min_date = target_date - timedelta(days=2)
            max_date = target_date + timedelta(days=2)
            
            options = self.db.query(Option).filter(
                Option.instrument_id == instrument.id,
                Option.expiration_date >= min_date,
                Option.expiration_date <= max_date
            ).all()
            
            if not options:
                return None
            
            # Group options by type
            calls = [o for o in options if o.option_type == 'call']
            puts = [o for o in options if o.option_type == 'put']
            
            if not calls or not puts:
                return None
            
            # Find ATM strike
            atm_strike = min(options, key=lambda x: abs(x.strike_price - current_price)).strike_price
            
            # Calculate skew at different strike distances
            skews = {}
            
            for distance in [0.05, 0.10, 0.15]:  # 5%, 10%, 15% OTM
                # Find OTM call and put at similar distances
                otm_call_strike = atm_strike * (1 + distance)
                otm_put_strike = atm_strike * (1 - distance)
                
                # Find closest strikes
                otm_call = min(calls, key=lambda x: abs(x.strike_price - otm_call_strike))
                otm_put = min(puts, key=lambda x: abs(x.strike_price - otm_put_strike))
                
                # Get latest price data
                otm_call_price = self.db.query(OptionPriceData).filter(
                    OptionPriceData.option_id == otm_call.id
                ).order_by(OptionPriceData.timestamp.desc()).first()
                
                otm_put_price = self.db.query(OptionPriceData).filter(
                    OptionPriceData.option_id == otm_put.id
                ).order_by(OptionPriceData.timestamp.desc()).first()
                
                if not otm_call_price or not otm_put_price:
                    continue
                
                # Calculate skew
                if otm_call_price.implied_volatility is not None and otm_put_price.implied_volatility is not None:
                    skew = otm_put_price.implied_volatility - otm_call_price.implied_volatility
                    skews[f"{int(distance*100)}pct"] = skew
            
            if not skews:
                return None
            
            # Calculate average skew
            avg_skew = sum(skews.values()) / len(skews)
            
            return {
                'skews': skews,
                'avg_skew': avg_skew
            }
        
        except Exception as e:
            logger.error(f"Error calculating IV skew for {instrument.symbol}: {e}")
            return None
    
    def generate_signals(self, instrument: Instrument) -> List[Signal]:
        """
        Generate signals based on implied volatility skew.
        """
        signals = []
        
        try:
            # Get current price
            current_price = instrument.last_price
            if not current_price:
                return signals
            
            # Calculate IV skew
            skew_data = self.calculate_iv_skew(instrument)
            if not skew_data or 'avg_skew' not in skew_data:
                return signals
            
            # Check for high positive skew (bearish market sentiment)
            if skew_data['avg_skew'] > self.skew_threshold:
                # Find ATM put option
                atm_put = self.find_atm_options(instrument.id, current_price, 'put')
                if not atm_put:
                    return signals
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_PUT,
                    'signal_source': SignalSource.VOLATILITY,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 0.95,  # 5% profit target
                    'stop_loss': current_price * 1.03,  # 3% stop loss
                    'confidence_score': 0.6 + min(0.3, (skew_data['avg_skew'] - self.skew_threshold) / self.skew_threshold),  # Scale confidence based on skew
                    'time_frame': '7d',
                    'option_id': atm_put.id,
                    'option_strike': atm_put.strike_price,
                    'option_expiration': atm_put.expiration_date,
                    'parameters': {
                        'indicator': 'iv_skew',
                        'avg_skew': skew_data['avg_skew'],
                        'skews': skew_data['skews']
                    },
                    'notes': f"High IV skew for {instrument.symbol}. Avg skew: {skew_data['avg_skew']:.4f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'iv_skew',
                        'factor_value': skew_data['avg_skew'],
                        'factor_weight': 0.7,
                        'factor_category': 'volatility',
                        'factor_description': f"IV skew: {skew_data['avg_skew']:.4f}"
                    })
                    
                    # Add individual skew factors
                    for distance, skew in skew_data['skews'].items():
                        self.save_signal_factor(signal.id, {
                            'factor_name': f"iv_skew_{distance}",
                            'factor_value': skew,
                            'factor_weight': 0.3 / len(skew_data['skews']),
                            'factor_category': 'volatility',
                            'factor_description': f"IV skew at {distance}: {skew:.4f}"
                        })
                    
                    signals.append(signal)
            
            # Check for high negative skew (unusual, but can indicate bullish reversal)
            elif skew_data['avg_skew'] < -self.skew_threshold:
                # Find ATM call option
                atm_call = self.find_atm_options(instrument.id, current_price, 'call')
                if not atm_call:
                    return signals
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_CALL,
                    'signal_source': SignalSource.VOLATILITY,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 1.05,  # 5% profit target
                    'stop_loss': current_price * 0.97,  # 3% stop loss
                    'confidence_score': 0.6 + min(0.3, (abs(skew_data['avg_skew']) - self.skew_threshold) / self.skew_threshold),  # Scale confidence based on skew
                    'time_frame': '7d',
                    'option_id': atm_call.id,
                    'option_strike': atm_call.strike_price,
                    'option_expiration': atm_call.expiration_date,
                    'parameters': {
                        'indicator': 'iv_skew',
                        'avg_skew': skew_data['avg_skew'],
                        'skews': skew_data['skews']
                    },
                    'notes': f"Negative IV skew for {instrument.symbol}. Avg skew: {skew_data['avg_skew']:.4f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'iv_skew',
                        'factor_value': skew_data['avg_skew'],
                        'factor_weight': 0.7,
                        'factor_category': 'volatility',
                        'factor_description': f"IV skew: {skew_data['avg_skew']:.4f}"
                    })
                    
                    # Add individual skew factors
                    for distance, skew in skew_data['skews'].items():
                        self.save_signal_factor(signal.id, {
                            'factor_name': f"iv_skew_{distance}",
                            'factor_value': skew,
                            'factor_weight': 0.3 / len(skew_data['skews']),
                            'factor_category': 'volatility',
                            'factor_description': f"IV skew at {distance}: {skew:.4f}"
                        })
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error generating IV skew signals for {instrument.symbol}: {e}")
        
        return signals

class VolatilitySurfaceStrategy(VolatilityStrategy):
    """Strategy based on volatility surface analysis."""
    
    def __init__(self, db: Session):
        super().__init__(db)
    
    def analyze_volatility_surface(self, instrument: Instrument) -> Optional[Dict[str, Any]]:
        """
        Analyze volatility surface for an instrument.
        
        Volatility surface is a 3D representation of implied volatility
        across different strikes and expirations.
        """
        try:
            # Get current price
            current_price = instrument.last_price
            if not current_price:
                return None
            
            # Get options with different expirations
            options = self.db.query(Option).filter(
                Option.instrument_id == instrument.id,
                Option.expiration_date >= datetime.utcnow().date()
            ).all()
            
            if not options:
                return None
            
            # Group options by expiration date
            expirations = {}
            for option in options:
                exp_date = option.expiration_date
                if exp_date not in expirations:
                    expirations[exp_date] = []
                
                expirations[exp_date].append(option)
            
            # Analyze volatility surface
            surface_data = {}
            
            for exp_date, exp_options in expirations.items():
                # Calculate days to expiration
                days_to_exp = (exp_date - datetime.utcnow().date()).days
                
                # Skip if too far in the future
                if days_to_exp > 60:
                    continue
                
                # Group options by type
                calls = [o for o in exp_options if o.option_type == 'call']
                puts = [o for o in exp_options if o.option_type == 'put']
                
                if not calls or not puts:
                    continue
                
                # Get implied volatilities
                call_ivs = {}
                put_ivs = {}
                
                for call in calls:
                    # Get latest price data
                    price_data = self.db.query(OptionPriceData).filter(
                        OptionPriceData.option_id == call.id
                    ).order_by(OptionPriceData.timestamp.desc()).first()
                    
                    if price_data and price_data.implied_volatility is not None:
                        # Calculate moneyness
                        moneyness = call.strike_price / current_price - 1
                        call_ivs[moneyness] = price_data.implied_volatility
                
                for put in puts:
                    # Get latest price data
                    price_data = self.db.query(OptionPriceData).filter(
                        OptionPriceData.option_id == put.id
                    ).order_by(OptionPriceData.timestamp.desc()).first()
                    
                    if price_data and price_data.implied_volatility is not None:
                        # Calculate moneyness
                        moneyness = 1 - put.strike_price / current_price
                        put_ivs[moneyness] = price_data.implied_volatility
                
                if not call_ivs or not put_ivs:
                    continue
                
                # Calculate volatility smile
                smile_data = {
                    'moneyness': sorted(list(set(list(call_ivs.keys()) + list(put_ivs.keys())))),
                    'call_ivs': [call_ivs.get(m, None) for m in sorted(list(set(list(call_ivs.keys()) + list(put_ivs.keys()))))],
                    'put_ivs': [put_ivs.get(m, None) for m in sorted(list(set(list(call_ivs.keys()) + list(put_ivs.keys()))))]
                }
                
                # Calculate skew
                atm_call_iv = None
                atm_put_iv = None
                
                for moneyness, iv in call_ivs.items():
                    if abs(moneyness) < 0.01:  # Close to ATM
                        atm_call_iv = iv
                        break
                
                for moneyness, iv in put_ivs.items():
                    if abs(moneyness) < 0.01:  # Close to ATM
                        atm_put_iv = iv
                        break
                
                if atm_call_iv is not None and atm_put_iv is not None:
                    skew = atm_put_iv - atm_call_iv
                else:
                    skew = None
                
                # Calculate term structure
                if days_to_exp == 7:  # 7 DTE
                    term_structure = {
                        'days_to_exp': days_to_exp,
                        'atm_call_iv': atm_call_iv,
                        'atm_put_iv': atm_put_iv,
                        'skew': skew
                    }
                
                # Store data
                surface_data[days_to_exp] = {
                    'smile': smile_data,
                    'skew': skew,
                    'atm_call_iv': atm_call_iv,
                    'atm_put_iv': atm_put_iv
                }
            
            if not surface_data:
                return None
            
            # Calculate term structure slope
            term_days = sorted(surface_data.keys())
            if len(term_days) >= 2:
                # Calculate slope between shortest and longest expiration
                short_exp = term_days[0]
                long_exp = term_days[-1]
                
                if surface_data[short_exp]['atm_call_iv'] is not None and surface_data[long_exp]['atm_call_iv'] is not None:
                    term_slope = (surface_data[long_exp]['atm_call_iv'] - surface_data[short_exp]['atm_call_iv']) / (long_exp - short_exp)
                else:
                    term_slope = None
            else:
                term_slope = None
            
            return {
                'surface_data': surface_data,
                'term_slope': term_slope
            }
        
        except Exception as e:
            logger.error(f"Error analyzing volatility surface for {instrument.symbol}: {e}")
            return None
    
    def generate_signals(self, instrument: Instrument) -> List[Signal]:
        """
        Generate signals based on volatility surface analysis.
        """
        signals = []
        
        try:
            # Get current price
            current_price = instrument.last_price
            if not current_price:
                return signals
            
            # Analyze volatility surface
            surface_analysis = self.analyze_volatility_surface(instrument)
            if not surface_analysis or 'surface_data' not in surface_analysis:
                return signals
            
            # Check for 7 DTE data
            if 7 not in surface_analysis['surface_data']:
                return signals
            
            # Get 7 DTE data
            dte7_data = surface_analysis['surface_data'][7]
            
            # Check for high skew (bearish)
            if dte7_data['skew'] is not None and dte7_data['skew'] > 0.1:
                # Find ATM put option
                atm_put = self.find_atm_options(instrument.id, current_price, 'put')
                if not atm_put:
                    return signals
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_PUT,
                    'signal_source': SignalSource.VOLATILITY,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 0.95,  # 5% profit target
                    'stop_loss': current_price * 1.03,  # 3% stop loss
                    'confidence_score': 0.6 + min(0.3, dte7_data['skew'] * 2),  # Scale confidence based on skew
                    'time_frame': '7d',
                    'option_id': atm_put.id,
                    'option_strike': atm_put.strike_price,
                    'option_expiration': atm_put.expiration_date,
                    'parameters': {
                        'indicator': 'volatility_surface',
                        'skew': dte7_data['skew'],
                        'atm_call_iv': dte7_data['atm_call_iv'],
                        'atm_put_iv': dte7_data['atm_put_iv'],
                        'term_slope': surface_analysis['term_slope']
                    },
                    'notes': f"High volatility skew for {instrument.symbol}. 7 DTE skew: {dte7_data['skew']:.4f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'vol_skew',
                        'factor_value': dte7_data['skew'],
                        'factor_weight': 0.5,
                        'factor_category': 'volatility',
                        'factor_description': f"Volatility skew: {dte7_data['skew']:.4f}"
                    })
                    
                    # Add term structure factor
                    if surface_analysis['term_slope'] is not None:
                        self.save_signal_factor(signal.id, {
                            'factor_name': 'term_slope',
                            'factor_value': surface_analysis['term_slope'],
                            'factor_weight': 0.3,
                            'factor_category': 'volatility',
                            'factor_description': f"Term structure slope: {surface_analysis['term_slope']:.4f}"
                        })
                    
                    # Add ATM IV factor
                    if dte7_data['atm_put_iv'] is not None:
                        self.save_signal_factor(signal.id, {
                            'factor_name': 'atm_put_iv',
                            'factor_value': dte7_data['atm_put_iv'],
                            'factor_weight': 0.2,
                            'factor_category': 'volatility',
                            'factor_description': f"ATM put IV: {dte7_data['atm_put_iv']:.4f}"
                        })
                    
                    signals.append(signal)
            
            # Check for negative term slope (bearish)
            elif surface_analysis['term_slope'] is not None and surface_analysis['term_slope'] < -0.01:
                # Find ATM put option
                atm_put = self.find_atm_options(instrument.id, current_price, 'put')
                if not atm_put:
                    return signals
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_PUT,
                    'signal_source': SignalSource.VOLATILITY,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 0.95,  # 5% profit target
                    'stop_loss': current_price * 1.03,  # 3% stop loss
                    'confidence_score': 0.6 + min(0.3, abs(surface_analysis['term_slope']) * 20),  # Scale confidence based on term slope
                    'time_frame': '7d',
                    'option_id': atm_put.id,
                    'option_strike': atm_put.strike_price,
                    'option_expiration': atm_put.expiration_date,
                    'parameters': {
                        'indicator': 'volatility_surface',
                        'skew': dte7_data['skew'],
                        'atm_call_iv': dte7_data['atm_call_iv'],
                        'atm_put_iv': dte7_data['atm_put_iv'],
                        'term_slope': surface_analysis['term_slope']
                    },
                    'notes': f"Negative volatility term structure for {instrument.symbol}. Term slope: {surface_analysis['term_slope']:.4f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'term_slope',
                        'factor_value': surface_analysis['term_slope'],
                        'factor_weight': 0.6,
                        'factor_category': 'volatility',
                        'factor_description': f"Term structure slope: {surface_analysis['term_slope']:.4f}"
                    })
                    
                    # Add skew factor
                    if dte7_data['skew'] is not None:
                        self.save_signal_factor(signal.id, {
                            'factor_name': 'vol_skew',
                            'factor_value': dte7_data['skew'],
                            'factor_weight': 0.4,
                            'factor_category': 'volatility',
                            'factor_description': f"Volatility skew: {dte7_data['skew']:.4f}"
                        })
                    
                    signals.append(signal)
            
            # Check for low skew and positive term slope (bullish)
            elif (dte7_data['skew'] is not None and dte7_data['skew'] < 0.05 and 
                  surface_analysis['term_slope'] is not None and surface_analysis['term_slope'] > 0.005):
                # Find ATM call option
                atm_call = self.find_atm_options(instrument.id, current_price, 'call')
                if not atm_call:
                    return signals
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_CALL,
                    'signal_source': SignalSource.VOLATILITY,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 1.05,  # 5% profit target
                    'stop_loss': current_price * 0.97,  # 3% stop loss
                    'confidence_score': 0.6 + min(0.3, surface_analysis['term_slope'] * 30),  # Scale confidence based on term slope
                    'time_frame': '7d',
                    'option_id': atm_call.id,
                    'option_strike': atm_call.strike_price,
                    'option_expiration': atm_call.expiration_date,
                    'parameters': {
                        'indicator': 'volatility_surface',
                        'skew': dte7_data['skew'],
                        'atm_call_iv': dte7_data['atm_call_iv'],
                        'atm_put_iv': dte7_data['atm_put_iv'],
                        'term_slope': surface_analysis['term_slope']
                    },
                    'notes': f"Bullish volatility surface for {instrument.symbol}. Low skew: {dte7_data['skew']:.4f}, Positive term slope: {surface_analysis['term_slope']:.4f}"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'term_slope',
                        'factor_value': surface_analysis['term_slope'],
                        'factor_weight': 0.5,
                        'factor_category': 'volatility',
                        'factor_description': f"Term structure slope: {surface_analysis['term_slope']:.4f}"
                    })
                    
                    # Add skew factor
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'vol_skew',
                        'factor_value': dte7_data['skew'],
                        'factor_weight': 0.3,
                        'factor_category': 'volatility',
                        'factor_description': f"Volatility skew: {dte7_data['skew']:.4f}"
                    })
                    
                    # Add ATM IV factor
                    if dte7_data['atm_call_iv'] is not None:
                        self.save_signal_factor(signal.id, {
                            'factor_name': 'atm_call_iv',
                            'factor_value': dte7_data['atm_call_iv'],
                            'factor_weight': 0.2,
                            'factor_category': 'volatility',
                            'factor_description': f"ATM call IV: {dte7_data['atm_call_iv']:.4f}"
                        })
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error generating volatility surface signals for {instrument.symbol}: {e}")
        
        return signals

