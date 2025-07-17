import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.services.reporting_service import ReportingService
from app.models.reporting import Report, ReportType, MarketCondition, SignalFactor, FundamentalData
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalStatus
from app.models.trade import Trade
from app.models.position import Position
from app.models.market_data import MarketData, Instrument
from app.models.user import User

logger = logging.getLogger(__name__)

class SevenDTEReportingService(ReportingService):
    """Reporting service for 7DTE system."""
    
    async def _generate_report_data(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate report data for 7DTE system."""
        return {
            "report_date": date.strftime("%Y-%m-%d"),
            "generation_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "daily_summary": await self._generate_daily_summary(date, portfolio_id),
            "signal_analysis": await self._generate_signal_analysis(date, portfolio_id),
            "trade_execution": await self._generate_trade_execution(date, portfolio_id),
            "position_management": await self._generate_position_management(date, portfolio_id),
            "risk_analysis": await self._generate_risk_analysis(date, portfolio_id),
            "system_performance": await self._generate_system_performance(date, portfolio_id),
            "next_day_outlook": await self._generate_next_day_outlook(date, portfolio_id)
        }
    
    async def _generate_daily_summary(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate daily summary section for 7DTE system."""
        # Get portfolio data
        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        
        # Get daily performance
        previous_day = date - timedelta(days=1)
        previous_portfolio = self.db.query(Portfolio).filter(
            Portfolio.id == portfolio_id,
            Portfolio.as_of_date == previous_day
        ).first()
        
        start_value = previous_portfolio.total_value if previous_portfolio else portfolio.initial_value
        end_value = portfolio.total_value
        daily_pnl = end_value - start_value
        daily_pnl_pct = (daily_pnl / start_value) * 100 if start_value > 0 else 0
        
        # Get trade counts
        trades = self.db.query(Trade).filter(
            Trade.portfolio_id == portfolio_id,
            Trade.execution_time >= datetime.combine(date, datetime.min.time()),
            Trade.execution_time < datetime.combine(date + timedelta(days=1), datetime.min.time())
        ).all()
        
        entry_trades = [t for t in trades if t.trade_type == "entry"]
        exit_trades = [t for t in trades if t.trade_type == "exit"]
        
        # Get signal counts
        signals = self.db.query(Signal).filter(
            Signal.generation_time >= datetime.combine(date, datetime.min.time()),
            Signal.generation_time < datetime.combine(date + timedelta(days=1), datetime.min.time())
        ).all()
        
        # Market context
        market_data = self.db.query(MarketData).filter(
            MarketData.symbol == "SPY",
            MarketData.date == date
        ).first()
        
        vix_data = self.db.query(MarketData).filter(
            MarketData.symbol == "VIX",
            MarketData.date == date
        ).first()
        
        # Get market condition
        market_condition = self.db.query(MarketCondition).filter(
            MarketCondition.date == date
        ).first()
        
        # Get fundamental data for Mag7 stocks
        mag7_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"]
        
        mag7_data = {}
        for symbol in mag7_symbols:
            # Get instrument
            instrument = self.db.query(Instrument).filter(Instrument.symbol == symbol).first()
            
            if instrument:
                # Get fundamental data
                fundamental_data = self.db.query(FundamentalData).filter(
                    FundamentalData.instrument_id == instrument.id,
                    FundamentalData.date == date
                ).first()
                
                if fundamental_data:
                    mag7_data[symbol] = {
                        "pe_ratio": fundamental_data.pe_ratio,
                        "price_target": fundamental_data.price_target,
                        "analyst_rating": fundamental_data.analyst_rating,
                        "next_earnings_date": fundamental_data.next_earnings_date.strftime("%Y-%m-%d") if fundamental_data.next_earnings_date else None
                    }
        
        # Get earnings this week
        next_week = date + timedelta(days=7)
        earnings_this_week = []
        
        fundamental_data_this_week = self.db.query(FundamentalData).filter(
            FundamentalData.next_earnings_date >= date,
            FundamentalData.next_earnings_date <= next_week
        ).all()
        
        for data in fundamental_data_this_week:
            instrument = self.db.query(Instrument).filter(Instrument.id == data.instrument_id).first()
            
            if instrument:
                earnings_this_week.append({
                    "symbol": instrument.symbol,
                    "date": data.next_earnings_date.strftime("%Y-%m-%d"),
                    "time": data.earnings_time,
                    "estimated_eps": data.estimated_eps,
                    "previous_eps": data.previous_eps
                })
        
        return {
            "date": date.strftime("%Y-%m-%d"),
            "portfolio_value": end_value,
            "daily_pnl": daily_pnl,
            "daily_pnl_pct": daily_pnl_pct,
            "total_trades": len(trades),
            "entry_trades": len(entry_trades),
            "exit_trades": len(exit_trades),
            "signals_generated": len(signals),
            "signals_executed": len([s for s in signals if s.status == SignalStatus.EXECUTED]),
            "market_context": {
                "spy_change_pct": market_data.change_percent if market_data else None,
                "vix_level": vix_data.close if vix_data else None,
                "vix_change_pct": vix_data.change_percent if vix_data else None,
                "market_condition": market_condition.condition_type if market_condition else "Unknown"
            },
            "fundamental_context": {
                "mag7_data": mag7_data,
                "earnings_this_week": earnings_this_week
            }
        }
    
    async def _generate_signal_analysis(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate signal analysis section for 7DTE system."""
        # Get signals for the day
        signals = self.db.query(Signal).filter(
            Signal.generation_time >= datetime.combine(date, datetime.min.time()),
            Signal.generation_time < datetime.combine(date + timedelta(days=1), datetime.min.time())
        ).all()
        
        # Get signal factors
        signal_ids = [s.id for s in signals]
        signal_factors = []
        
        if signal_ids:
            signal_factors = self.db.query(SignalFactor).filter(
                SignalFactor.signal_id.in_(signal_ids)
            ).all()
        
        # Group signals by source
        signal_by_source = {}
        for signal in signals:
            if signal.source not in signal_by_source:
                signal_by_source[signal.source] = []
            signal_by_source[signal.source].append(signal)
        
        # Calculate source performance
        source_performance = {}
        for source, source_signals in signal_by_source.items():
            executed_signals = [s for s in source_signals if s.status == SignalStatus.EXECUTED]
            winning_signals = [s for s in executed_signals if s.result == "win"]
            
            source_performance[source] = {
                "total_signals": len(source_signals),
                "executed_signals": len(executed_signals),
                "win_rate": len(winning_signals) / len(executed_signals) if executed_signals else 0,
                "avg_confidence": sum(s.confidence for s in source_signals) / len(source_signals) if source_signals else 0
            }
        
        # Group factors by category
        factor_by_category = {}
        for factor in signal_factors:
            if factor.factor_category not in factor_by_category:
                factor_by_category[factor.factor_category] = []
            factor_by_category[factor.factor_category].append(factor)
        
        # Calculate category importance
        category_importance = {}
        for category, factors in factor_by_category.items():
            category_importance[category] = sum(f.factor_weight for f in factors) / len(factors) if factors else 0
        
        # Get detailed signal data
        signal_details = []
        for signal in signals:
            # Get factors for this signal
            factors = [f for f in signal_factors if f.signal_id == signal.id]
            
            # Get instrument
            instrument = self.db.query(Instrument).filter(Instrument.symbol == signal.symbol).first()
            
            # Get fundamental data if available
            fundamental_data = None
            if instrument:
                fundamental_data = self.db.query(FundamentalData).filter(
                    FundamentalData.instrument_id == instrument.id,
                    FundamentalData.date == date
                ).first()
            
            signal_detail = {
                "id": signal.id,
                "symbol": signal.symbol,
                "direction": signal.direction,
                "confidence": signal.confidence,
                "status": signal.status,
                "result": signal.result,
                "generation_time": signal.generation_time.strftime("%Y-%m-%d %H:%M:%S"),
                "factors": [
                    {
                        "name": f.factor_name,
                        "value": f.factor_value,
                        "weight": f.factor_weight,
                        "category": f.factor_category,
                        "description": f.factor_description
                    }
                    for f in factors
                ]
            }
            
            # Add fundamental data if available
            if fundamental_data:
                signal_detail["fundamental_data"] = {
                    "pe_ratio": fundamental_data.pe_ratio,
                    "price_target": fundamental_data.price_target,
                    "analyst_rating": fundamental_data.analyst_rating,
                    "next_earnings_date": fundamental_data.next_earnings_date.strftime("%Y-%m-%d") if fundamental_data.next_earnings_date else None
                }
            
            signal_details.append(signal_detail)
        
        return {
            "signal_count": len(signals),
            "executed_count": len([s for s in signals if s.status == SignalStatus.EXECUTED]),
            "win_rate": len([s for s in signals if s.result == "win"]) / len([s for s in signals if s.status == SignalStatus.EXECUTED]) if [s for s in signals if s.status == SignalStatus.EXECUTED] else 0,
            "source_performance": source_performance,
            "category_importance": category_importance,
            "signal_details": signal_details
        }
    
    async def _generate_trade_execution(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate trade execution section for 7DTE system."""
        # Get trades for the day
        trades = self.db.query(Trade).filter(
            Trade.portfolio_id == portfolio_id,
            Trade.execution_time >= datetime.combine(date, datetime.min.time()),
            Trade.execution_time < datetime.combine(date + timedelta(days=1), datetime.min.time())
        ).all()
        
        # Calculate execution metrics
        entry_trades = [t for t in trades if t.trade_type == "entry"]
        exit_trades = [t for t in trades if t.trade_type == "exit"]
        
        # Calculate slippage
        avg_slippage = sum(t.slippage for t in trades if t.slippage is not None) / len([t for t in trades if t.slippage is not None]) if [t for t in trades if t.slippage is not None] else 0
        
        # Calculate execution time
        avg_execution_time = sum((t.execution_time - t.signal_time).total_seconds() for t in trades if t.signal_time is not None) / len([t for t in trades if t.signal_time is not None]) if [t for t in trades if t.signal_time is not None] else 0
        
        # Get trade details
        trade_details = []
        for trade in trades:
            trade_details.append({
                "id": trade.id,
                "symbol": trade.symbol,
                "trade_type": trade.trade_type,
                "direction": trade.direction,
                "price": trade.price,
                "quantity": trade.quantity,
                "value": trade.price * trade.quantity,
                "execution_time": trade.execution_time.strftime("%Y-%m-%d %H:%M:%S"),
                "slippage": trade.slippage,
                "commission": trade.commission
            })
        
        return {
            "total_trades": len(trades),
            "entry_trades": len(entry_trades),
            "exit_trades": len(exit_trades),
            "avg_slippage": avg_slippage,
            "avg_execution_time": avg_execution_time,
            "total_commission": sum(t.commission for t in trades if t.commission is not None),
            "trades": trade_details
        }
    
    async def _generate_position_management(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate position management section for 7DTE system."""
        # Get open positions
        open_positions = self.db.query(Position).filter(
            Position.portfolio_id == portfolio_id,
            Position.is_open == True
        ).all()
        
        # Get positions closed today
        closed_positions = self.db.query(Position).filter(
            Position.portfolio_id == portfolio_id,
            Position.is_open == False,
            Position.exit_time >= datetime.combine(date, datetime.min.time()),
            Position.exit_time < datetime.combine(date + timedelta(days=1), datetime.min.time())
        ).all()
        
        # Calculate position metrics
        avg_holding_time = sum((p.exit_time - p.entry_time).total_seconds() / 3600 for p in closed_positions) / len(closed_positions) if closed_positions else 0
        
        # Get open position details
        open_position_details = []
        for position in open_positions:
            # Get current price
            market_data = self.db.query(MarketData).filter(
                MarketData.symbol == position.symbol,
                MarketData.date == date
            ).first()
            
            current_price = market_data.close if market_data else position.entry_price
            
            # Calculate unrealized P&L
            unrealized_pnl = (current_price - position.entry_price) * position.quantity * (1 if position.direction == "long" else -1)
            unrealized_pnl_pct = (unrealized_pnl / (position.entry_price * position.quantity)) * 100 if position.entry_price * position.quantity != 0 else 0
            
            # Calculate days held
            days_held = (date - position.entry_time.date()).days
            
            # Get instrument
            instrument = self.db.query(Instrument).filter(Instrument.symbol == position.symbol).first()
            
            # Get fundamental data if available
            fundamental_data = None
            if instrument:
                fundamental_data = self.db.query(FundamentalData).filter(
                    FundamentalData.instrument_id == instrument.id,
                    FundamentalData.date == date
                ).first()
            
            position_detail = {
                "id": position.id,
                "symbol": position.symbol,
                "direction": position.direction,
                "entry_price": position.entry_price,
                "current_price": current_price,
                "quantity": position.quantity,
                "entry_date": position.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct,
                "days_held": days_held
            }
            
            # Add fundamental data if available
            if fundamental_data:
                position_detail["fundamental_data"] = {
                    "pe_ratio": fundamental_data.pe_ratio,
                    "price_target": fundamental_data.price_target,
                    "analyst_rating": fundamental_data.analyst_rating,
                    "next_earnings_date": fundamental_data.next_earnings_date.strftime("%Y-%m-%d") if fundamental_data.next_earnings_date else None
                }
            
            open_position_details.append(position_detail)
        
        # Get closed position details
        closed_position_details = []
        for position in closed_positions:
            # Calculate realized P&L
            realized_pnl = position.exit_price * position.quantity - position.entry_price * position.quantity
            if position.direction == "short":
                realized_pnl = -realized_pnl
            
            realized_pnl_pct = (realized_pnl / (position.entry_price * position.quantity)) * 100 if position.entry_price * position.quantity != 0 else 0
            
            # Calculate days held
            days_held = (position.exit_time.date() - position.entry_time.date()).days
            
            closed_position_details.append({
                "id": position.id,
                "symbol": position.symbol,
                "direction": position.direction,
                "entry_price": position.entry_price,
                "exit_price": position.exit_price,
                "quantity": position.quantity,
                "entry_date": position.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                "exit_date": position.exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                "days_held": days_held,
                "realized_pnl": realized_pnl,
                "realized_pnl_pct": realized_pnl_pct
            })
        
        return {
            "open_position_count": len(open_positions),
            "closed_position_count": len(closed_positions),
            "avg_holding_time_days": avg_holding_time / 24 if avg_holding_time else 0,
            "total_realized_pnl": sum(p.exit_price * p.quantity - p.entry_price * p.quantity for p in closed_positions),
            "open_positions": open_position_details,
            "closed_positions": closed_position_details
        }
    
    async def _generate_risk_analysis(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate risk analysis section for 7DTE system."""
        # Get portfolio
        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        
        # Get open positions
        open_positions = self.db.query(Position).filter(
            Position.portfolio_id == portfolio_id,
            Position.is_open == True
        ).all()
        
        # Get market data
        market_data = self.db.query(MarketData).filter(
            MarketData.symbol == "SPY",
            MarketData.date == date
        ).first()
        
        vix_data = self.db.query(MarketData).filter(
            MarketData.symbol == "VIX",
            MarketData.date == date
        ).first()
        
        # Calculate portfolio beta
        portfolio_beta = 1.0  # Default to market beta
        
        # Calculate value at risk (VaR)
        # Simple VaR calculation: portfolio value * volatility * sqrt(time) * confidence factor
        portfolio_value = portfolio.total_value
        volatility = vix_data.close / 100 if vix_data else 0.2  # Convert VIX to decimal or use default
        confidence_factor = 1.65  # 95% confidence level
        value_at_risk = portfolio_value * volatility * confidence_factor
        
        # Calculate position concentration
        position_values = {}
        total_position_value = 0
        
        for position in open_positions:
            # Get current price
            position_market_data = self.db.query(MarketData).filter(
                MarketData.symbol == position.symbol,
                MarketData.date == date
            ).first()
            
            current_price = position_market_data.close if position_market_data else position.entry_price
            position_value = current_price * position.quantity
            
            if position.symbol not in position_values:
                position_values[position.symbol] = 0
            
            position_values[position.symbol] += position_value
            total_position_value += position_value
        
        # Calculate concentration percentages
        concentration = {}
        for symbol, value in position_values.items():
            concentration[symbol] = (value / total_position_value) * 100 if total_position_value > 0 else 0
        
        # Calculate Greeks (simplified)
        total_delta = sum(p.delta for p in open_positions if p.delta is not None)
        total_gamma = sum(p.gamma for p in open_positions if p.gamma is not None)
        total_theta = sum(p.theta for p in open_positions if p.theta is not None)
        total_vega = sum(p.vega for p in open_positions if p.vega is not None)
        
        # Calculate correlation matrix for Mag7 stocks
        mag7_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"]
        
        # Get historical prices for correlation calculation
        start_date = date - timedelta(days=30)
        
        correlation_matrix = {
            "symbols": mag7_symbols,
            "data": []
        }
        
        # Get price data for each symbol
        price_data = {}
        for symbol in mag7_symbols:
            prices = self.db.query(MarketData).filter(
                MarketData.symbol == symbol,
                MarketData.date >= start_date,
                MarketData.date <= date
            ).order_by(MarketData.date).all()
            
            if prices:
                price_data[symbol] = [p.close for p in prices]
        
        # Calculate correlation matrix
        for symbol1 in mag7_symbols:
            row = []
            for symbol2 in mag7_symbols:
                if symbol1 in price_data and symbol2 in price_data:
                    # Ensure both price series have the same length
                    min_length = min(len(price_data[symbol1]), len(price_data[symbol2]))
                    
                    if min_length > 1:
                        # Calculate correlation
                        corr = np.corrcoef(price_data[symbol1][:min_length], price_data[symbol2][:min_length])[0, 1]
                        row.append(corr)
                    else:
                        row.append(1.0 if symbol1 == symbol2 else 0.0)
                else:
                    row.append(1.0 if symbol1 == symbol2 else 0.0)
            
            correlation_matrix["data"].append(row)
        
        return {
            "portfolio_beta": portfolio_beta,
            "value_at_risk": value_at_risk,
            "concentration": concentration,
            "greeks": {
                "delta": total_delta,
                "gamma": total_gamma,
                "theta": total_theta,
                "vega": total_vega
            },
            "vix_level": vix_data.close if vix_data else None,
            "correlation_matrix": correlation_matrix
        }
    
    async def _generate_system_performance(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate system performance section for 7DTE system."""
        # Get signals for the last 30 days
        start_date = date - timedelta(days=30)
        signals = self.db.query(Signal).filter(
            Signal.generation_time >= datetime.combine(start_date, datetime.min.time()),
            Signal.generation_time < datetime.combine(date + timedelta(days=1), datetime.min.time())
        ).all()
        
        # Calculate signal accuracy
        executed_signals = [s for s in signals if s.status == SignalStatus.EXECUTED]
        winning_signals = [s for s in executed_signals if s.result == "win"]
        
        signal_accuracy = (len(winning_signals) / len(executed_signals)) * 100 if executed_signals else 0
        
        # Calculate execution efficiency
        execution_efficiency = (len(executed_signals) / len(signals)) * 100 if signals else 0
        
        # Calculate system uptime
        # This would typically come from a system monitoring service
        system_uptime = 99.9  # Placeholder
        
        # Calculate average response time
        # This would typically come from a system monitoring service
        avg_response_time = 0.5  # Placeholder in seconds
        
        # Calculate performance by signal category
        signal_factors = []
        signal_ids = [s.id for s in signals]
        
        if signal_ids:
            signal_factors = self.db.query(SignalFactor).filter(
                SignalFactor.signal_id.in_(signal_ids)
            ).all()
        
        # Group factors by category
        factor_by_category = {}
        for factor in signal_factors:
            if factor.factor_category not in factor_by_category:
                factor_by_category[factor.factor_category] = []
            factor_by_category[factor.factor_category].append(factor)
        
        # Calculate performance by category
        category_performance = {}
        for category, factors in factor_by_category.items():
            # Get signals with this category
            signal_ids_with_category = set(f.signal_id for f in factors)
            signals_with_category = [s for s in signals if s.id in signal_ids_with_category]
            
            executed_signals_with_category = [s for s in signals_with_category if s.status == SignalStatus.EXECUTED]
            winning_signals_with_category = [s for s in executed_signals_with_category if s.result == "win"]
            
            category_performance[category] = {
                "signal_count": len(signals_with_category),
                "executed_count": len(executed_signals_with_category),
                "win_rate": (len(winning_signals_with_category) / len(executed_signals_with_category)) * 100 if executed_signals_with_category else 0,
                "avg_confidence": sum(s.confidence for s in signals_with_category) / len(signals_with_category) if signals_with_category else 0
            }
        
        return {
            "signal_accuracy": signal_accuracy,
            "execution_efficiency": execution_efficiency,
            "system_uptime": system_uptime,
            "avg_response_time": avg_response_time,
            "signal_count_30d": len(signals),
            "win_rate_30d": (len(winning_signals) / len(executed_signals)) * 100 if executed_signals else 0,
            "category_performance": category_performance
        }
    
    async def _generate_next_day_outlook(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate next day outlook section for 7DTE system."""
        # Get market data
        market_data = self.db.query(MarketData).filter(
            MarketData.symbol == "SPY",
            MarketData.date == date
        ).first()
        
        vix_data = self.db.query(MarketData).filter(
            MarketData.symbol == "VIX",
            MarketData.date == date
        ).first()
        
        # Get market condition
        market_condition = self.db.query(MarketCondition).filter(
            MarketCondition.date == date
        ).first()
        
        # Determine next trading day
        next_day = date + timedelta(days=1)
        while next_day.weekday() >= 5:  # Skip weekends
            next_day += timedelta(days=1)
        
        # Determine market outlook
        market_outlook = "Neutral"
        if market_data and market_data.change_percent > 1.0:
            market_outlook = "Bullish"
        elif market_data and market_data.change_percent < -1.0:
            market_outlook = "Bearish"
        
        # Determine expected volatility
        expected_volatility = "Normal"
        if vix_data:
            if vix_data.close > 25:
                expected_volatility = "High"
            elif vix_data.close < 15:
                expected_volatility = "Low"
        
        # Get upcoming earnings
        next_week = date + timedelta(days=7)
        upcoming_earnings = []
        
        fundamental_data_upcoming = self.db.query(FundamentalData).filter(
            FundamentalData.next_earnings_date >= next_day,
            FundamentalData.next_earnings_date <= next_week
        ).all()
        
        for data in fundamental_data_upcoming:
            instrument = self.db.query(Instrument).filter(Instrument.id == data.instrument_id).first()
            
            if instrument:
                upcoming_earnings.append({
                    "symbol": instrument.symbol,
                    "date": data.next_earnings_date.strftime("%Y-%m-%d"),
                    "time": data.earnings_time,
                    "estimated_eps": data.estimated_eps
                })
        
        # Get expiring options
        # This would typically come from a separate options data service
        expiring_options = []
        
        # Get positions approaching expiration
        positions_approaching_expiration = []
        for position in self.db.query(Position).filter(
            Position.portfolio_id == portfolio_id,
            Position.is_open == True
        ).all():
            # Calculate days to expiration
            if position.expiration_date:
                days_to_expiration = (position.expiration_date - date).days
                
                if days_to_expiration <= 3:  # Approaching expiration
                    positions_approaching_expiration.append({
                        "id": position.id,
                        "symbol": position.symbol,
                        "direction": position.direction,
                        "entry_price": position.entry_price,
                        "days_to_expiration": days_to_expiration
                    })
        
        return {
            "next_trading_day": next_day.strftime("%Y-%m-%d"),
            "market_outlook": market_outlook,
            "expected_volatility": expected_volatility,
            "upcoming_earnings": upcoming_earnings,
            "positions_approaching_expiration": positions_approaching_expiration
        }

