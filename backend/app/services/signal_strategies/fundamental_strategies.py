import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session

from app.models.market_data import (
    Instrument, StockPrice, Option, EarningsData, 
    FinancialMetric, AnalystRating
)
from app.models.signal import Signal, SignalType, SignalSource, SignalStatus, SignalFactor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class FundamentalStrategy:
    """Base class for fundamental analysis strategies."""
    
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

class EarningsStrategy(FundamentalStrategy):
    """Strategy based on earnings events and surprises."""
    
    def __init__(self, db: Session, days_before: int = 5, days_after: int = 2):
        super().__init__(db)
        self.days_before = days_before
        self.days_after = days_after
    
    def get_upcoming_earnings(self, instrument: Instrument) -> Optional[datetime]:
        """
        Get upcoming earnings date for an instrument.
        """
        if not instrument.earnings_schedule or "next_date" not in instrument.earnings_schedule:
            return None
        
        try:
            next_date_str = instrument.earnings_schedule["next_date"]
            next_date = datetime.fromisoformat(next_date_str)
            return next_date
        except (ValueError, TypeError):
            return None
    
    def get_historical_earnings_surprises(self, instrument: Instrument, limit: int = 4) -> List[EarningsData]:
        """
        Get historical earnings surprises for an instrument.
        """
        earnings_data = self.db.query(EarningsData).filter(
            EarningsData.instrument_id == instrument.id
        ).order_by(EarningsData.earnings_date.desc()).limit(limit).all()
        
        return earnings_data
    
    def calculate_earnings_surprise_trend(self, earnings_data: List[EarningsData]) -> float:
        """
        Calculate the trend in earnings surprises.
        
        Returns a value between -1 and 1, where:
        - Positive values indicate improving surprises
        - Negative values indicate deteriorating surprises
        - Zero indicates no clear trend
        """
        if not earnings_data or len(earnings_data) < 2:
            return 0.0
        
        # Sort by earnings date (oldest first)
        sorted_data = sorted(earnings_data, key=lambda x: x.earnings_date)
        
        # Calculate surprise percentages
        surprises = [e.surprise_percentage for e in sorted_data if e.surprise_percentage is not None]
        
        if not surprises or len(surprises) < 2:
            return 0.0
        
        # Calculate trend
        # Simple approach: compare most recent with average of previous
        most_recent = surprises[-1]
        previous_avg = sum(surprises[:-1]) / len(surprises[:-1])
        
        # Normalize to [-1, 1]
        trend = (most_recent - previous_avg) / 100.0
        
        return max(-1.0, min(1.0, trend))
    
    def generate_signals(self, instrument: Instrument) -> List[Signal]:
        """
        Generate signals based on earnings events and surprises.
        """
        signals = []
        
        try:
            # Get current price
            current_price = instrument.last_price
            if not current_price:
                return signals
            
            # Get upcoming earnings date
            upcoming_earnings = self.get_upcoming_earnings(instrument)
            if not upcoming_earnings:
                return signals
            
            # Calculate days until earnings
            today = datetime.utcnow().date()
            earnings_date = upcoming_earnings.date()
            days_until_earnings = (earnings_date - today).days
            
            # Get historical earnings surprises
            historical_earnings = self.get_historical_earnings_surprises(instrument)
            
            # Calculate earnings surprise trend
            surprise_trend = self.calculate_earnings_surprise_trend(historical_earnings)
            
            # Check if we're approaching earnings (within days_before)
            if 0 < days_until_earnings <= self.days_before:
                # Determine signal type based on historical surprises
                if surprise_trend > 0.2:  # Strong positive trend
                    # Find ATM call option
                    atm_call = self.find_atm_options(instrument.id, current_price, 'call')
                    if not atm_call:
                        return signals
                    
                    # Create signal
                    signal_data = {
                        'instrument_id': instrument.id,
                        'signal_type': SignalType.LONG_CALL,
                        'signal_source': SignalSource.FUNDAMENTAL,
                        'status': SignalStatus.PENDING,
                        'entry_price': None,  # Will be set when executed
                        'target_price': current_price * 1.07,  # 7% profit target
                        'stop_loss': current_price * 0.95,  # 5% stop loss
                        'confidence_score': 0.6 + (surprise_trend * 0.3),  # Scale confidence based on trend
                        'time_frame': '7d',
                        'option_id': atm_call.id,
                        'option_strike': atm_call.strike_price,
                        'option_expiration': atm_call.expiration_date,
                        'parameters': {
                            'indicator': 'earnings',
                            'days_until_earnings': days_until_earnings,
                            'surprise_trend': surprise_trend,
                            'historical_surprises': [
                                {
                                    'date': e.earnings_date.isoformat(),
                                    'surprise': e.surprise_percentage
                                } for e in historical_earnings if e.surprise_percentage is not None
                            ]
                        },
                        'notes': f"Bullish earnings play for {instrument.symbol}. Earnings in {days_until_earnings} days with positive surprise trend."
                    }
                    
                    # Save signal
                    signal = self.save_signal(signal_data)
                    if signal:
                        # Save signal factors
                        self.save_signal_factor(signal.id, {
                            'factor_name': 'earnings_surprise_trend',
                            'factor_value': surprise_trend,
                            'factor_weight': 0.6,
                            'factor_category': 'fundamental',
                            'factor_description': f"Earnings surprise trend: {surprise_trend:.4f}"
                        })
                        
                        # Add days until earnings factor
                        self.save_signal_factor(signal.id, {
                            'factor_name': 'days_until_earnings',
                            'factor_value': days_until_earnings,
                            'factor_weight': 0.4,
                            'factor_category': 'fundamental',
                            'factor_description': f"Days until earnings: {days_until_earnings}"
                        })
                        
                        signals.append(signal)
                
                elif surprise_trend < -0.2:  # Strong negative trend
                    # Find ATM put option
                    atm_put = self.find_atm_options(instrument.id, current_price, 'put')
                    if not atm_put:
                        return signals
                    
                    # Create signal
                    signal_data = {
                        'instrument_id': instrument.id,
                        'signal_type': SignalType.LONG_PUT,
                        'signal_source': SignalSource.FUNDAMENTAL,
                        'status': SignalStatus.PENDING,
                        'entry_price': None,  # Will be set when executed
                        'target_price': current_price * 0.93,  # 7% profit target
                        'stop_loss': current_price * 1.05,  # 5% stop loss
                        'confidence_score': 0.6 + (abs(surprise_trend) * 0.3),  # Scale confidence based on trend
                        'time_frame': '7d',
                        'option_id': atm_put.id,
                        'option_strike': atm_put.strike_price,
                        'option_expiration': atm_put.expiration_date,
                        'parameters': {
                            'indicator': 'earnings',
                            'days_until_earnings': days_until_earnings,
                            'surprise_trend': surprise_trend,
                            'historical_surprises': [
                                {
                                    'date': e.earnings_date.isoformat(),
                                    'surprise': e.surprise_percentage
                                } for e in historical_earnings if e.surprise_percentage is not None
                            ]
                        },
                        'notes': f"Bearish earnings play for {instrument.symbol}. Earnings in {days_until_earnings} days with negative surprise trend."
                    }
                    
                    # Save signal
                    signal = self.save_signal(signal_data)
                    if signal:
                        # Save signal factors
                        self.save_signal_factor(signal.id, {
                            'factor_name': 'earnings_surprise_trend',
                            'factor_value': surprise_trend,
                            'factor_weight': 0.6,
                            'factor_category': 'fundamental',
                            'factor_description': f"Earnings surprise trend: {surprise_trend:.4f}"
                        })
                        
                        # Add days until earnings factor
                        self.save_signal_factor(signal.id, {
                            'factor_name': 'days_until_earnings',
                            'factor_value': days_until_earnings,
                            'factor_weight': 0.4,
                            'factor_category': 'fundamental',
                            'factor_description': f"Days until earnings: {days_until_earnings}"
                        })
                        
                        signals.append(signal)
            
            # Check if we're just after earnings (within days_after)
            elif -self.days_after <= days_until_earnings <= 0:
                # Get most recent earnings data
                most_recent = self.db.query(EarningsData).filter(
                    EarningsData.instrument_id == instrument.id,
                    EarningsData.earnings_date <= datetime.utcnow()
                ).order_by(EarningsData.earnings_date.desc()).first()
                
                if most_recent and most_recent.surprise_percentage is not None:
                    # Determine signal type based on surprise
                    if most_recent.surprise_percentage > 10:  # Strong positive surprise
                        # Find ATM call option
                        atm_call = self.find_atm_options(instrument.id, current_price, 'call')
                        if not atm_call:
                            return signals
                        
                        # Create signal
                        signal_data = {
                            'instrument_id': instrument.id,
                            'signal_type': SignalType.LONG_CALL,
                            'signal_source': SignalSource.FUNDAMENTAL,
                            'status': SignalStatus.PENDING,
                            'entry_price': None,  # Will be set when executed
                            'target_price': current_price * 1.08,  # 8% profit target
                            'stop_loss': current_price * 0.96,  # 4% stop loss
                            'confidence_score': 0.7 + (min(most_recent.surprise_percentage, 30) / 100),  # Scale confidence based on surprise
                            'time_frame': '7d',
                            'option_id': atm_call.id,
                            'option_strike': atm_call.strike_price,
                            'option_expiration': atm_call.expiration_date,
                            'parameters': {
                                'indicator': 'earnings_surprise',
                                'days_after_earnings': -days_until_earnings,
                                'surprise_percentage': most_recent.surprise_percentage,
                                'eps_actual': most_recent.eps_actual,
                                'eps_estimate': most_recent.eps_estimate
                            },
                            'notes': f"Post-earnings momentum for {instrument.symbol}. Recent surprise: {most_recent.surprise_percentage:.2f}%"
                        }
                        
                        # Save signal
                        signal = self.save_signal(signal_data)
                        if signal:
                            # Save signal factors
                            self.save_signal_factor(signal.id, {
                                'factor_name': 'earnings_surprise',
                                'factor_value': most_recent.surprise_percentage,
                                'factor_weight': 0.7,
                                'factor_category': 'fundamental',
                                'factor_description': f"Earnings surprise: {most_recent.surprise_percentage:.2f}%"
                            })
                            
                            # Add days after earnings factor
                            self.save_signal_factor(signal.id, {
                                'factor_name': 'days_after_earnings',
                                'factor_value': -days_until_earnings,
                                'factor_weight': 0.3,
                                'factor_category': 'fundamental',
                                'factor_description': f"Days after earnings: {-days_until_earnings}"
                            })
                            
                            signals.append(signal)
                    
                    elif most_recent.surprise_percentage < -10:  # Strong negative surprise
                        # Find ATM put option
                        atm_put = self.find_atm_options(instrument.id, current_price, 'put')
                        if not atm_put:
                            return signals
                        
                        # Create signal
                        signal_data = {
                            'instrument_id': instrument.id,
                            'signal_type': SignalType.LONG_PUT,
                            'signal_source': SignalSource.FUNDAMENTAL,
                            'status': SignalStatus.PENDING,
                            'entry_price': None,  # Will be set when executed
                            'target_price': current_price * 0.92,  # 8% profit target
                            'stop_loss': current_price * 1.04,  # 4% stop loss
                            'confidence_score': 0.7 + (min(abs(most_recent.surprise_percentage), 30) / 100),  # Scale confidence based on surprise
                            'time_frame': '7d',
                            'option_id': atm_put.id,
                            'option_strike': atm_put.strike_price,
                            'option_expiration': atm_put.expiration_date,
                            'parameters': {
                                'indicator': 'earnings_surprise',
                                'days_after_earnings': -days_until_earnings,
                                'surprise_percentage': most_recent.surprise_percentage,
                                'eps_actual': most_recent.eps_actual,
                                'eps_estimate': most_recent.eps_estimate
                            },
                            'notes': f"Post-earnings decline for {instrument.symbol}. Recent surprise: {most_recent.surprise_percentage:.2f}%"
                        }
                        
                        # Save signal
                        signal = self.save_signal(signal_data)
                        if signal:
                            # Save signal factors
                            self.save_signal_factor(signal.id, {
                                'factor_name': 'earnings_surprise',
                                'factor_value': most_recent.surprise_percentage,
                                'factor_weight': 0.7,
                                'factor_category': 'fundamental',
                                'factor_description': f"Earnings surprise: {most_recent.surprise_percentage:.2f}%"
                            })
                            
                            # Add days after earnings factor
                            self.save_signal_factor(signal.id, {
                                'factor_name': 'days_after_earnings',
                                'factor_value': -days_until_earnings,
                                'factor_weight': 0.3,
                                'factor_category': 'fundamental',
                                'factor_description': f"Days after earnings: {-days_until_earnings}"
                            })
                            
                            signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error generating earnings signals for {instrument.symbol}: {e}")
        
        return signals

class ValuationStrategy(FundamentalStrategy):
    """Strategy based on valuation metrics."""
    
    def __init__(self, db: Session):
        super().__init__(db)
    
    def get_valuation_metrics(self, instrument: Instrument) -> Dict[str, float]:
        """
        Get valuation metrics for an instrument.
        """
        metrics = {}
        
        # Get latest financial metrics
        financial_metrics = self.db.query(FinancialMetric).filter(
            FinancialMetric.instrument_id == instrument.id
        ).order_by(FinancialMetric.date.desc()).all()
        
        # Group by metric type
        for metric in financial_metrics:
            if metric.metric_type not in metrics:
                metrics[metric.metric_type] = metric.value
        
        return metrics
    
    def get_sector_average_metrics(self, sector: str) -> Dict[str, float]:
        """
        Get average valuation metrics for a sector.
        """
        sector_metrics = {}
        
        # Get instruments in the same sector
        instruments = self.db.query(Instrument).filter(
            Instrument.sector == sector
        ).all()
        
        if not instruments:
            return sector_metrics
        
        # Collect metrics for each instrument
        all_metrics = {}
        for instrument in instruments:
            metrics = self.get_valuation_metrics(instrument)
            
            for metric_type, value in metrics.items():
                if metric_type not in all_metrics:
                    all_metrics[metric_type] = []
                
                all_metrics[metric_type].append(value)
        
        # Calculate averages
        for metric_type, values in all_metrics.items():
            if values:
                sector_metrics[metric_type] = sum(values) / len(values)
        
        return sector_metrics
    
    def generate_signals(self, instrument: Instrument) -> List[Signal]:
        """
        Generate signals based on valuation metrics.
        """
        signals = []
        
        try:
            # Get current price
            current_price = instrument.last_price
            if not current_price:
                return signals
            
            # Get valuation metrics
            metrics = self.get_valuation_metrics(instrument)
            
            # Get sector average metrics
            sector_metrics = {}
            if instrument.sector:
                sector_metrics = self.get_sector_average_metrics(instrument.sector)
            
            # Check for undervaluation (bullish)
            is_undervalued = False
            undervaluation_factors = []
            
            # Check P/E ratio
            if 'pe_ratio' in metrics and 'pe_ratio' in sector_metrics:
                pe_ratio = metrics['pe_ratio']
                sector_pe = sector_metrics['pe_ratio']
                
                if pe_ratio < sector_pe * 0.8:  # 20% below sector average
                    is_undervalued = True
                    undervaluation_factors.append({
                        'factor_name': 'pe_ratio',
                        'factor_value': pe_ratio,
                        'factor_weight': 0.3,
                        'factor_category': 'fundamental',
                        'factor_description': f"P/E ratio: {pe_ratio:.2f} (Sector avg: {sector_pe:.2f})"
                    })
            
            # Check PEG ratio
            if 'peg_ratio' in metrics and 'peg_ratio' in sector_metrics:
                peg_ratio = metrics['peg_ratio']
                sector_peg = sector_metrics['peg_ratio']
                
                if peg_ratio < sector_peg * 0.8:  # 20% below sector average
                    is_undervalued = True
                    undervaluation_factors.append({
                        'factor_name': 'peg_ratio',
                        'factor_value': peg_ratio,
                        'factor_weight': 0.25,
                        'factor_category': 'fundamental',
                        'factor_description': f"PEG ratio: {peg_ratio:.2f} (Sector avg: {sector_peg:.2f})"
                    })
            
            # Check price-to-book ratio
            if 'price_to_book' in metrics and 'price_to_book' in sector_metrics:
                p_b_ratio = metrics['price_to_book']
                sector_p_b = sector_metrics['price_to_book']
                
                if p_b_ratio < sector_p_b * 0.8:  # 20% below sector average
                    is_undervalued = True
                    undervaluation_factors.append({
                        'factor_name': 'price_to_book',
                        'factor_value': p_b_ratio,
                        'factor_weight': 0.25,
                        'factor_category': 'fundamental',
                        'factor_description': f"Price-to-book ratio: {p_b_ratio:.2f} (Sector avg: {sector_p_b:.2f})"
                    })
            
            # Check profit margin
            if 'profit_margin' in metrics and 'profit_margin' in sector_metrics:
                profit_margin = metrics['profit_margin']
                sector_margin = sector_metrics['profit_margin']
                
                if profit_margin > sector_margin * 1.2:  # 20% above sector average
                    is_undervalued = True
                    undervaluation_factors.append({
                        'factor_name': 'profit_margin',
                        'factor_value': profit_margin,
                        'factor_weight': 0.2,
                        'factor_category': 'fundamental',
                        'factor_description': f"Profit margin: {profit_margin:.2f} (Sector avg: {sector_margin:.2f})"
                    })
            
            # Generate signal if undervalued
            if is_undervalued and undervaluation_factors:
                # Find ATM call option
                atm_call = self.find_atm_options(instrument.id, current_price, 'call')
                if not atm_call:
                    return signals
                
                # Calculate confidence score
                confidence_score = 0.6  # Base confidence
                for factor in undervaluation_factors:
                    confidence_score += factor['factor_weight'] * 0.3  # Max additional 0.3
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_CALL,
                    'signal_source': SignalSource.FUNDAMENTAL,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 1.06,  # 6% profit target
                    'stop_loss': current_price * 0.96,  # 4% stop loss
                    'confidence_score': min(0.9, confidence_score),  # Cap at 0.9
                    'time_frame': '7d',
                    'option_id': atm_call.id,
                    'option_strike': atm_call.strike_price,
                    'option_expiration': atm_call.expiration_date,
                    'parameters': {
                        'indicator': 'valuation',
                        'metrics': metrics,
                        'sector_metrics': sector_metrics
                    },
                    'notes': f"Valuation play for {instrument.symbol}. Undervalued relative to sector."
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    for factor in undervaluation_factors:
                        self.save_signal_factor(signal.id, factor)
                    
                    signals.append(signal)
            
            # Check for overvaluation (bearish)
            is_overvalued = False
            overvaluation_factors = []
            
            # Check P/E ratio
            if 'pe_ratio' in metrics and 'pe_ratio' in sector_metrics:
                pe_ratio = metrics['pe_ratio']
                sector_pe = sector_metrics['pe_ratio']
                
                if pe_ratio > sector_pe * 1.2:  # 20% above sector average
                    is_overvalued = True
                    overvaluation_factors.append({
                        'factor_name': 'pe_ratio',
                        'factor_value': pe_ratio,
                        'factor_weight': 0.3,
                        'factor_category': 'fundamental',
                        'factor_description': f"P/E ratio: {pe_ratio:.2f} (Sector avg: {sector_pe:.2f})"
                    })
            
            # Check PEG ratio
            if 'peg_ratio' in metrics and 'peg_ratio' in sector_metrics:
                peg_ratio = metrics['peg_ratio']
                sector_peg = sector_metrics['peg_ratio']
                
                if peg_ratio > sector_peg * 1.2:  # 20% above sector average
                    is_overvalued = True
                    overvaluation_factors.append({
                        'factor_name': 'peg_ratio',
                        'factor_value': peg_ratio,
                        'factor_weight': 0.25,
                        'factor_category': 'fundamental',
                        'factor_description': f"PEG ratio: {peg_ratio:.2f} (Sector avg: {sector_peg:.2f})"
                    })
            
            # Check price-to-book ratio
            if 'price_to_book' in metrics and 'price_to_book' in sector_metrics:
                p_b_ratio = metrics['price_to_book']
                sector_p_b = sector_metrics['price_to_book']
                
                if p_b_ratio > sector_p_b * 1.2:  # 20% above sector average
                    is_overvalued = True
                    overvaluation_factors.append({
                        'factor_name': 'price_to_book',
                        'factor_value': p_b_ratio,
                        'factor_weight': 0.25,
                        'factor_category': 'fundamental',
                        'factor_description': f"Price-to-book ratio: {p_b_ratio:.2f} (Sector avg: {sector_p_b:.2f})"
                    })
            
            # Check profit margin
            if 'profit_margin' in metrics and 'profit_margin' in sector_metrics:
                profit_margin = metrics['profit_margin']
                sector_margin = sector_metrics['profit_margin']
                
                if profit_margin < sector_margin * 0.8:  # 20% below sector average
                    is_overvalued = True
                    overvaluation_factors.append({
                        'factor_name': 'profit_margin',
                        'factor_value': profit_margin,
                        'factor_weight': 0.2,
                        'factor_category': 'fundamental',
                        'factor_description': f"Profit margin: {profit_margin:.2f} (Sector avg: {sector_margin:.2f})"
                    })
            
            # Generate signal if overvalued
            if is_overvalued and overvaluation_factors:
                # Find ATM put option
                atm_put = self.find_atm_options(instrument.id, current_price, 'put')
                if not atm_put:
                    return signals
                
                # Calculate confidence score
                confidence_score = 0.6  # Base confidence
                for factor in overvaluation_factors:
                    confidence_score += factor['factor_weight'] * 0.3  # Max additional 0.3
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_PUT,
                    'signal_source': SignalSource.FUNDAMENTAL,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * 0.94,  # 6% profit target
                    'stop_loss': current_price * 1.04,  # 4% stop loss
                    'confidence_score': min(0.9, confidence_score),  # Cap at 0.9
                    'time_frame': '7d',
                    'option_id': atm_put.id,
                    'option_strike': atm_put.strike_price,
                    'option_expiration': atm_put.expiration_date,
                    'parameters': {
                        'indicator': 'valuation',
                        'metrics': metrics,
                        'sector_metrics': sector_metrics
                    },
                    'notes': f"Valuation play for {instrument.symbol}. Overvalued relative to sector."
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    for factor in overvaluation_factors:
                        self.save_signal_factor(signal.id, factor)
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error generating valuation signals for {instrument.symbol}: {e}")
        
        return signals

class AnalystRatingStrategy(FundamentalStrategy):
    """Strategy based on analyst ratings and price targets."""
    
    def __init__(self, db: Session, min_ratings: int = 3):
        super().__init__(db)
        self.min_ratings = min_ratings
    
    def get_recent_ratings(self, instrument: Instrument, days: int = 30) -> List[AnalystRating]:
        """
        Get recent analyst ratings for an instrument.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        ratings = self.db.query(AnalystRating).filter(
            AnalystRating.instrument_id == instrument.id,
            AnalystRating.rating_date >= cutoff_date
        ).order_by(AnalystRating.rating_date.desc()).all()
        
        return ratings
    
    def analyze_ratings(self, ratings: List[AnalystRating], current_price: float) -> Dict[str, Any]:
        """
        Analyze analyst ratings and price targets.
        """
        if not ratings or len(ratings) < self.min_ratings:
            return {}
        
        # Count ratings by category
        rating_counts = {
            'buy': 0,
            'hold': 0,
            'sell': 0
        }
        
        # Collect price targets
        price_targets = []
        
        for rating in ratings:
            # Categorize rating
            rating_text = rating.rating.lower()
            
            if 'buy' in rating_text or 'outperform' in rating_text or 'overweight' in rating_text:
                rating_counts['buy'] += 1
            elif 'sell' in rating_text or 'underperform' in rating_text or 'underweight' in rating_text:
                rating_counts['sell'] += 1
            else:
                rating_counts['hold'] += 1
            
            # Add price target
            if rating.price_target:
                price_targets.append(rating.price_target)
        
        # Calculate average price target
        avg_price_target = sum(price_targets) / len(price_targets) if price_targets else None
        
        # Calculate price target upside/downside
        price_target_change = None
        if avg_price_target and current_price:
            price_target_change = (avg_price_target / current_price) - 1
        
        # Calculate rating sentiment
        total_ratings = sum(rating_counts.values())
        buy_percentage = rating_counts['buy'] / total_ratings if total_ratings > 0 else 0
        sell_percentage = rating_counts['sell'] / total_ratings if total_ratings > 0 else 0
        
        # Calculate sentiment score (-1 to 1)
        sentiment_score = buy_percentage - sell_percentage
        
        return {
            'rating_counts': rating_counts,
            'avg_price_target': avg_price_target,
            'price_target_change': price_target_change,
            'sentiment_score': sentiment_score
        }
    
    def generate_signals(self, instrument: Instrument) -> List[Signal]:
        """
        Generate signals based on analyst ratings.
        """
        signals = []
        
        try:
            # Get current price
            current_price = instrument.last_price
            if not current_price:
                return signals
            
            # Get recent ratings
            ratings = self.get_recent_ratings(instrument)
            
            # Analyze ratings
            analysis = self.analyze_ratings(ratings, current_price)
            if not analysis:
                return signals
            
            # Check for bullish signal
            if analysis['sentiment_score'] > 0.5 and analysis.get('price_target_change', 0) > 0.1:
                # Find ATM call option
                atm_call = self.find_atm_options(instrument.id, current_price, 'call')
                if not atm_call:
                    return signals
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_CALL,
                    'signal_source': SignalSource.FUNDAMENTAL,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * (1 + min(0.1, analysis['price_target_change'] / 2)),  # Half of price target change, capped at 10%
                    'stop_loss': current_price * 0.95,  # 5% stop loss
                    'confidence_score': 0.5 + (analysis['sentiment_score'] * 0.4),  # Scale confidence based on sentiment
                    'time_frame': '7d',
                    'option_id': atm_call.id,
                    'option_strike': atm_call.strike_price,
                    'option_expiration': atm_call.expiration_date,
                    'parameters': {
                        'indicator': 'analyst_ratings',
                        'rating_counts': analysis['rating_counts'],
                        'avg_price_target': analysis['avg_price_target'],
                        'price_target_change': analysis['price_target_change'],
                        'sentiment_score': analysis['sentiment_score']
                    },
                    'notes': f"Analyst rating play for {instrument.symbol}. Sentiment: {analysis['sentiment_score']:.2f}, Price target upside: {analysis['price_target_change']*100:.1f}%"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'analyst_sentiment',
                        'factor_value': analysis['sentiment_score'],
                        'factor_weight': 0.5,
                        'factor_category': 'fundamental',
                        'factor_description': f"Analyst sentiment: {analysis['sentiment_score']:.2f}"
                    })
                    
                    # Add price target factor
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'price_target_upside',
                        'factor_value': analysis['price_target_change'],
                        'factor_weight': 0.5,
                        'factor_category': 'fundamental',
                        'factor_description': f"Price target upside: {analysis['price_target_change']*100:.1f}%"
                    })
                    
                    signals.append(signal)
            
            # Check for bearish signal
            elif analysis['sentiment_score'] < -0.3 and analysis.get('price_target_change', 0) < -0.1:
                # Find ATM put option
                atm_put = self.find_atm_options(instrument.id, current_price, 'put')
                if not atm_put:
                    return signals
                
                # Create signal
                signal_data = {
                    'instrument_id': instrument.id,
                    'signal_type': SignalType.LONG_PUT,
                    'signal_source': SignalSource.FUNDAMENTAL,
                    'status': SignalStatus.PENDING,
                    'entry_price': None,  # Will be set when executed
                    'target_price': current_price * (1 + max(-0.1, analysis['price_target_change'] / 2)),  # Half of price target change, capped at -10%
                    'stop_loss': current_price * 1.05,  # 5% stop loss
                    'confidence_score': 0.5 + (abs(analysis['sentiment_score']) * 0.4),  # Scale confidence based on sentiment
                    'time_frame': '7d',
                    'option_id': atm_put.id,
                    'option_strike': atm_put.strike_price,
                    'option_expiration': atm_put.expiration_date,
                    'parameters': {
                        'indicator': 'analyst_ratings',
                        'rating_counts': analysis['rating_counts'],
                        'avg_price_target': analysis['avg_price_target'],
                        'price_target_change': analysis['price_target_change'],
                        'sentiment_score': analysis['sentiment_score']
                    },
                    'notes': f"Analyst rating play for {instrument.symbol}. Sentiment: {analysis['sentiment_score']:.2f}, Price target downside: {analysis['price_target_change']*100:.1f}%"
                }
                
                # Save signal
                signal = self.save_signal(signal_data)
                if signal:
                    # Save signal factors
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'analyst_sentiment',
                        'factor_value': analysis['sentiment_score'],
                        'factor_weight': 0.5,
                        'factor_category': 'fundamental',
                        'factor_description': f"Analyst sentiment: {analysis['sentiment_score']:.2f}"
                    })
                    
                    # Add price target factor
                    self.save_signal_factor(signal.id, {
                        'factor_name': 'price_target_downside',
                        'factor_value': analysis['price_target_change'],
                        'factor_weight': 0.5,
                        'factor_category': 'fundamental',
                        'factor_description': f"Price target downside: {analysis['price_target_change']*100:.1f}%"
                    })
                    
                    signals.append(signal)
        
        except Exception as e:
            logger.error(f"Error generating analyst rating signals for {instrument.symbol}: {e}")
        
        return signals

