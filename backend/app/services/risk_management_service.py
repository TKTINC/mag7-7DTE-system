import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session

from app.models.market_data import Instrument, StockPrice
from app.models.portfolio import Portfolio, Position, Trade
from app.models.user import User, RiskProfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class RiskManagementService:
    """
    Service for managing risk in the Mag7-7DTE-System.
    
    This service provides risk management capabilities including:
    - Position sizing
    - Portfolio exposure limits
    - Correlation-based risk management
    - Stop-loss and take-profit management
    - Risk metrics calculation
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_position_size(self, 
                               user_id: int, 
                               instrument_id: int, 
                               signal_confidence: float,
                               option_price: float) -> Dict[str, Any]:
        """
        Calculate the recommended position size based on user's risk profile,
        portfolio value, and signal confidence.
        
        Args:
            user_id: ID of the user
            instrument_id: ID of the instrument (stock)
            signal_confidence: Confidence score of the signal (0.0 to 1.0)
            option_price: Current price of the option contract
            
        Returns:
            Dictionary containing recommended position size information
        """
        try:
            # Get user's risk profile
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.risk_profile:
                logger.warning(f"User {user_id} not found or has no risk profile")
                return {
                    "contracts": 0,
                    "max_capital": 0,
                    "risk_per_trade": 0,
                    "error": "User not found or has no risk profile"
                }
            
            # Get user's portfolio
            portfolio = self.db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
            if not portfolio:
                logger.warning(f"Portfolio not found for user {user_id}")
                return {
                    "contracts": 0,
                    "max_capital": 0,
                    "risk_per_trade": 0,
                    "error": "Portfolio not found"
                }
            
            # Get instrument
            instrument = self.db.query(Instrument).filter(Instrument.id == instrument_id).first()
            if not instrument:
                logger.warning(f"Instrument {instrument_id} not found")
                return {
                    "contracts": 0,
                    "max_capital": 0,
                    "risk_per_trade": 0,
                    "error": "Instrument not found"
                }
            
            # Calculate risk per trade based on risk profile
            # Risk profile contains max_portfolio_risk (e.g., 2% of portfolio per trade)
            max_portfolio_risk = user.risk_profile.max_portfolio_risk
            portfolio_value = portfolio.total_value
            
            # Base risk per trade
            risk_per_trade = portfolio_value * (max_portfolio_risk / 100)
            
            # Adjust risk based on signal confidence
            # Higher confidence = higher allocation, up to 1.5x base risk
            confidence_multiplier = 0.5 + signal_confidence
            adjusted_risk = risk_per_trade * confidence_multiplier
            
            # Calculate max capital to allocate (assuming max loss of 100%)
            max_capital = adjusted_risk
            
            # Calculate number of contracts
            # Each contract is 100 shares
            contract_value = option_price * 100
            contracts = int(max_capital / contract_value)
            
            # Ensure at least 1 contract if capital allows
            if contracts < 1 and max_capital >= contract_value:
                contracts = 1
            
            # Check if this exceeds max allocation per stock
            max_stock_allocation = user.risk_profile.max_stock_allocation
            max_stock_capital = portfolio_value * (max_stock_allocation / 100)
            
            # Get current allocation to this stock
            current_positions = self.db.query(Position).filter(
                Position.portfolio_id == portfolio.id,
                Position.instrument_id == instrument_id,
                Position.status == 'ACTIVE'
            ).all()
            
            current_allocation = sum(p.current_value for p in current_positions)
            
            # Adjust if needed
            available_allocation = max_stock_capital - current_allocation
            if available_allocation <= 0:
                logger.warning(f"Maximum allocation reached for instrument {instrument.symbol}")
                return {
                    "contracts": 0,
                    "max_capital": 0,
                    "risk_per_trade": 0,
                    "error": f"Maximum allocation reached for {instrument.symbol}"
                }
            
            if max_capital > available_allocation:
                max_capital = available_allocation
                contracts = int(max_capital / contract_value)
            
            return {
                "contracts": contracts,
                "max_capital": max_capital,
                "risk_per_trade": adjusted_risk,
                "contract_value": contract_value,
                "portfolio_value": portfolio_value,
                "current_allocation": current_allocation,
                "available_allocation": available_allocation,
                "confidence_multiplier": confidence_multiplier
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {
                "contracts": 0,
                "max_capital": 0,
                "risk_per_trade": 0,
                "error": str(e)
            }
    
    def calculate_correlation_matrix(self, lookback_days: int = 30) -> Optional[pd.DataFrame]:
        """
        Calculate correlation matrix between Magnificent 7 stocks.
        
        Args:
            lookback_days: Number of days to look back for correlation calculation
            
        Returns:
            Pandas DataFrame containing correlation matrix
        """
        try:
            # Get all Mag7 instruments
            instruments = self.db.query(Instrument).filter(
                Instrument.type == 'STOCK',
                Instrument.is_active == True
            ).all()
            
            if not instruments:
                logger.warning("No active instruments found")
                return None
            
            # Calculate date range
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=lookback_days)
            
            # Get price data for all instruments
            price_data = {}
            
            for instrument in instruments:
                prices = self.db.query(StockPrice).filter(
                    StockPrice.instrument_id == instrument.id,
                    StockPrice.date >= start_date,
                    StockPrice.date <= end_date
                ).order_by(StockPrice.date).all()
                
                if prices:
                    price_data[instrument.symbol] = {
                        'dates': [p.date for p in prices],
                        'prices': [p.close_price for p in prices]
                    }
            
            if not price_data:
                logger.warning("No price data found for the specified date range")
                return None
            
            # Create DataFrame with daily returns
            all_dates = sorted(set(date for symbol_data in price_data.values() for date in symbol_data['dates']))
            returns_df = pd.DataFrame(index=all_dates)
            
            for symbol, data in price_data.items():
                # Create series with dates as index
                prices_series = pd.Series(data['prices'], index=data['dates'])
                # Reindex to all dates
                prices_series = prices_series.reindex(all_dates)
                # Calculate daily returns
                returns = prices_series.pct_change().dropna()
                returns_df[symbol] = returns
            
            # Calculate correlation matrix
            correlation_matrix = returns_df.corr()
            
            return correlation_matrix
            
        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return None
    
    def check_portfolio_exposure(self, user_id: int) -> Dict[str, Any]:
        """
        Check portfolio exposure against risk limits.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing exposure metrics and alerts
        """
        try:
            # Get user's risk profile
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.risk_profile:
                logger.warning(f"User {user_id} not found or has no risk profile")
                return {
                    "status": "error",
                    "message": "User not found or has no risk profile"
                }
            
            # Get user's portfolio
            portfolio = self.db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
            if not portfolio:
                logger.warning(f"Portfolio not found for user {user_id}")
                return {
                    "status": "error",
                    "message": "Portfolio not found"
                }
            
            # Get active positions
            positions = self.db.query(Position).filter(
                Position.portfolio_id == portfolio.id,
                Position.status == 'ACTIVE'
            ).all()
            
            if not positions:
                return {
                    "status": "ok",
                    "total_exposure": 0,
                    "max_exposure": 0,
                    "exposure_percentage": 0,
                    "stock_exposures": {},
                    "alerts": []
                }
            
            # Calculate total exposure
            total_exposure = sum(p.current_value for p in positions)
            portfolio_value = portfolio.total_value
            
            # Calculate max allowed exposure
            max_portfolio_exposure = user.risk_profile.max_portfolio_exposure
            max_exposure = portfolio_value * (max_portfolio_exposure / 100)
            
            # Calculate exposure percentage
            exposure_percentage = (total_exposure / portfolio_value) * 100 if portfolio_value > 0 else 0
            
            # Calculate exposure by stock
            stock_exposures = {}
            for position in positions:
                instrument = self.db.query(Instrument).filter(Instrument.id == position.instrument_id).first()
                if instrument:
                    if instrument.symbol not in stock_exposures:
                        stock_exposures[instrument.symbol] = 0
                    stock_exposures[instrument.symbol] += position.current_value
            
            # Calculate exposure percentages by stock
            stock_exposure_percentages = {
                symbol: (value / portfolio_value) * 100 if portfolio_value > 0 else 0
                for symbol, value in stock_exposures.items()
            }
            
            # Check for alerts
            alerts = []
            
            # Check total exposure
            if exposure_percentage > max_portfolio_exposure:
                alerts.append({
                    "type": "total_exposure",
                    "level": "high",
                    "message": f"Total portfolio exposure ({exposure_percentage:.2f}%) exceeds maximum allowed ({max_portfolio_exposure:.2f}%)"
                })
            elif exposure_percentage > max_portfolio_exposure * 0.8:
                alerts.append({
                    "type": "total_exposure",
                    "level": "medium",
                    "message": f"Total portfolio exposure ({exposure_percentage:.2f}%) is approaching maximum allowed ({max_portfolio_exposure:.2f}%)"
                })
            
            # Check stock exposures
            max_stock_allocation = user.risk_profile.max_stock_allocation
            for symbol, percentage in stock_exposure_percentages.items():
                if percentage > max_stock_allocation:
                    alerts.append({
                        "type": "stock_exposure",
                        "level": "high",
                        "symbol": symbol,
                        "message": f"Exposure to {symbol} ({percentage:.2f}%) exceeds maximum allowed ({max_stock_allocation:.2f}%)"
                    })
                elif percentage > max_stock_allocation * 0.8:
                    alerts.append({
                        "type": "stock_exposure",
                        "level": "medium",
                        "symbol": symbol,
                        "message": f"Exposure to {symbol} ({percentage:.2f}%) is approaching maximum allowed ({max_stock_allocation:.2f}%)"
                    })
            
            # Check for correlation risk if we have multiple positions
            if len(stock_exposures) > 1:
                correlation_matrix = self.calculate_correlation_matrix()
                if correlation_matrix is not None:
                    # Check for high correlations between stocks in portfolio
                    high_correlations = []
                    portfolio_symbols = list(stock_exposures.keys())
                    
                    for i in range(len(portfolio_symbols)):
                        for j in range(i+1, len(portfolio_symbols)):
                            symbol1 = portfolio_symbols[i]
                            symbol2 = portfolio_symbols[j]
                            
                            if symbol1 in correlation_matrix.index and symbol2 in correlation_matrix.columns:
                                correlation = correlation_matrix.loc[symbol1, symbol2]
                                
                                if correlation > 0.8:
                                    high_correlations.append({
                                        "symbol1": symbol1,
                                        "symbol2": symbol2,
                                        "correlation": correlation
                                    })
                    
                    if high_correlations:
                        alerts.append({
                            "type": "correlation",
                            "level": "medium",
                            "correlations": high_correlations,
                            "message": f"High correlation detected between stocks in portfolio"
                        })
            
            return {
                "status": "ok",
                "total_exposure": total_exposure,
                "max_exposure": max_exposure,
                "exposure_percentage": exposure_percentage,
                "stock_exposures": {
                    symbol: {
                        "value": value,
                        "percentage": stock_exposure_percentages[symbol]
                    }
                    for symbol, value in stock_exposures.items()
                },
                "alerts": alerts
            }
            
        except Exception as e:
            logger.error(f"Error checking portfolio exposure: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def calculate_stop_loss_take_profit(self, 
                                       position_id: int, 
                                       risk_reward_ratio: float = 2.0) -> Dict[str, Any]:
        """
        Calculate recommended stop-loss and take-profit levels for a position.
        
        Args:
            position_id: ID of the position
            risk_reward_ratio: Target risk-reward ratio (default: 2.0)
            
        Returns:
            Dictionary containing stop-loss and take-profit recommendations
        """
        try:
            # Get position
            position = self.db.query(Position).filter(Position.id == position_id).first()
            if not position:
                logger.warning(f"Position {position_id} not found")
                return {
                    "status": "error",
                    "message": "Position not found"
                }
            
            # Get instrument
            instrument = self.db.query(Instrument).filter(Instrument.id == position.instrument_id).first()
            if not instrument:
                logger.warning(f"Instrument for position {position_id} not found")
                return {
                    "status": "error",
                    "message": "Instrument not found"
                }
            
            # Get user's risk profile
            portfolio = self.db.query(Portfolio).filter(Portfolio.id == position.portfolio_id).first()
            if not portfolio:
                logger.warning(f"Portfolio for position {position_id} not found")
                return {
                    "status": "error",
                    "message": "Portfolio not found"
                }
            
            user = self.db.query(User).filter(User.id == portfolio.user_id).first()
            if not user or not user.risk_profile:
                logger.warning(f"User for position {position_id} not found or has no risk profile")
                return {
                    "status": "error",
                    "message": "User not found or has no risk profile"
                }
            
            # Get position details
            entry_price = position.entry_price
            current_price = position.current_price
            position_type = position.position_type  # 'LONG_CALL' or 'LONG_PUT'
            
            # Calculate stop-loss percentage based on risk profile
            max_loss_percentage = user.risk_profile.max_loss_per_trade
            
            # For options, we need to consider time decay and volatility
            # This is a simplified approach - in reality, options pricing is more complex
            days_to_expiration = (position.expiration_date - datetime.utcnow().date()).days
            
            # Adjust stop-loss based on days to expiration
            # Shorter time to expiration = tighter stop-loss
            dte_factor = min(1.0, days_to_expiration / 7.0)  # Scale based on 7 DTE
            adjusted_max_loss = max_loss_percentage * dte_factor
            
            # Calculate stop-loss price
            if position_type == 'LONG_CALL':
                stop_loss_price = entry_price * (1 - adjusted_max_loss / 100)
            else:  # LONG_PUT
                stop_loss_price = entry_price * (1 - adjusted_max_loss / 100)
            
            # Ensure stop-loss is not below zero
            stop_loss_price = max(0.01, stop_loss_price)
            
            # Calculate take-profit based on risk-reward ratio
            risk = entry_price - stop_loss_price
            reward = risk * risk_reward_ratio
            
            if position_type == 'LONG_CALL':
                take_profit_price = entry_price + reward
            else:  # LONG_PUT
                take_profit_price = entry_price + reward
            
            # Calculate current risk-reward status
            if current_price > entry_price:
                current_reward = current_price - entry_price
                current_risk_reward = current_reward / risk if risk > 0 else 0
            else:
                current_loss = entry_price - current_price
                current_risk_reward = -current_loss / risk if risk > 0 else 0
            
            # Calculate percentage to stop-loss and take-profit
            pct_to_stop_loss = ((stop_loss_price - current_price) / current_price) * 100
            pct_to_take_profit = ((take_profit_price - current_price) / current_price) * 100
            
            return {
                "status": "ok",
                "position_id": position_id,
                "symbol": instrument.symbol,
                "position_type": position_type,
                "entry_price": entry_price,
                "current_price": current_price,
                "stop_loss_price": stop_loss_price,
                "take_profit_price": take_profit_price,
                "risk_reward_ratio": risk_reward_ratio,
                "current_risk_reward": current_risk_reward,
                "max_loss_percentage": adjusted_max_loss,
                "pct_to_stop_loss": pct_to_stop_loss,
                "pct_to_take_profit": pct_to_take_profit,
                "days_to_expiration": days_to_expiration
            }
            
        except Exception as e:
            logger.error(f"Error calculating stop-loss and take-profit: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def check_stop_loss_take_profit(self, position_id: int) -> Dict[str, Any]:
        """
        Check if a position has hit stop-loss or take-profit levels.
        
        Args:
            position_id: ID of the position
            
        Returns:
            Dictionary containing check results and recommendations
        """
        try:
            # Get position
            position = self.db.query(Position).filter(Position.id == position_id).first()
            if not position:
                logger.warning(f"Position {position_id} not found")
                return {
                    "status": "error",
                    "message": "Position not found"
                }
            
            # Get instrument
            instrument = self.db.query(Instrument).filter(Instrument.id == position.instrument_id).first()
            if not instrument:
                logger.warning(f"Instrument for position {position_id} not found")
                return {
                    "status": "error",
                    "message": "Instrument not found"
                }
            
            # Check if stop-loss or take-profit is set
            if not position.stop_loss_price and not position.take_profit_price:
                # Calculate recommended levels
                sl_tp = self.calculate_stop_loss_take_profit(position_id)
                if sl_tp["status"] == "error":
                    return sl_tp
                
                return {
                    "status": "ok",
                    "position_id": position_id,
                    "symbol": instrument.symbol,
                    "current_price": position.current_price,
                    "stop_loss_hit": False,
                    "take_profit_hit": False,
                    "message": "No stop-loss or take-profit levels set",
                    "recommendations": {
                        "set_stop_loss": sl_tp["stop_loss_price"],
                        "set_take_profit": sl_tp["take_profit_price"]
                    }
                }
            
            # Check if stop-loss is hit
            stop_loss_hit = False
            if position.stop_loss_price:
                if position.position_type == 'LONG_CALL' or position.position_type == 'LONG_PUT':
                    stop_loss_hit = position.current_price <= position.stop_loss_price
            
            # Check if take-profit is hit
            take_profit_hit = False
            if position.take_profit_price:
                if position.position_type == 'LONG_CALL' or position.position_type == 'LONG_PUT':
                    take_profit_hit = position.current_price >= position.take_profit_price
            
            # Calculate percentage to stop-loss and take-profit
            pct_to_stop_loss = None
            if position.stop_loss_price:
                pct_to_stop_loss = ((position.stop_loss_price - position.current_price) / position.current_price) * 100
            
            pct_to_take_profit = None
            if position.take_profit_price:
                pct_to_take_profit = ((position.take_profit_price - position.current_price) / position.current_price) * 100
            
            # Generate message
            message = ""
            if stop_loss_hit:
                message = "Stop-loss level has been hit. Consider closing the position."
            elif take_profit_hit:
                message = "Take-profit level has been hit. Consider closing the position or raising stop-loss to lock in profits."
            else:
                if pct_to_stop_loss is not None and pct_to_stop_loss > -5:  # Within 5% of stop-loss
                    message = "Position is approaching stop-loss level."
                elif pct_to_take_profit is not None and pct_to_take_profit < 5:  # Within 5% of take-profit
                    message = "Position is approaching take-profit level."
                else:
                    message = "Position is within acceptable range."
            
            return {
                "status": "ok",
                "position_id": position_id,
                "symbol": instrument.symbol,
                "position_type": position.position_type,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "stop_loss_price": position.stop_loss_price,
                "take_profit_price": position.take_profit_price,
                "stop_loss_hit": stop_loss_hit,
                "take_profit_hit": take_profit_hit,
                "pct_to_stop_loss": pct_to_stop_loss,
                "pct_to_take_profit": pct_to_take_profit,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Error checking stop-loss and take-profit: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def calculate_portfolio_metrics(self, user_id: int) -> Dict[str, Any]:
        """
        Calculate risk metrics for a user's portfolio.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing portfolio risk metrics
        """
        try:
            # Get user's portfolio
            portfolio = self.db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
            if not portfolio:
                logger.warning(f"Portfolio not found for user {user_id}")
                return {
                    "status": "error",
                    "message": "Portfolio not found"
                }
            
            # Get completed trades
            trades = self.db.query(Trade).filter(
                Trade.portfolio_id == portfolio.id,
                Trade.status == 'CLOSED'
            ).order_by(Trade.exit_date).all()
            
            if not trades:
                return {
                    "status": "ok",
                    "message": "No completed trades found",
                    "metrics": {
                        "win_rate": None,
                        "profit_factor": None,
                        "average_win": None,
                        "average_loss": None,
                        "largest_win": None,
                        "largest_loss": None,
                        "average_holding_period": None,
                        "sharpe_ratio": None,
                        "max_drawdown": None,
                        "max_drawdown_percentage": None
                    }
                }
            
            # Calculate win rate
            winning_trades = [t for t in trades if t.pnl > 0]
            losing_trades = [t for t in trades if t.pnl <= 0]
            
            win_rate = len(winning_trades) / len(trades) if trades else 0
            
            # Calculate profit factor
            gross_profit = sum(t.pnl for t in winning_trades)
            gross_loss = abs(sum(t.pnl for t in losing_trades))
            
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Calculate average win and loss
            average_win = gross_profit / len(winning_trades) if winning_trades else 0
            average_loss = gross_loss / len(losing_trades) if losing_trades else 0
            
            # Calculate largest win and loss
            largest_win = max(t.pnl for t in winning_trades) if winning_trades else 0
            largest_loss = min(t.pnl for t in losing_trades) if losing_trades else 0
            
            # Calculate average holding period
            holding_periods = [(t.exit_date - t.entry_date).days for t in trades]
            average_holding_period = sum(holding_periods) / len(holding_periods) if holding_periods else 0
            
            # Calculate equity curve
            equity_curve = []
            initial_equity = portfolio.initial_capital
            current_equity = initial_equity
            
            for trade in trades:
                current_equity += trade.pnl
                equity_curve.append({
                    'date': trade.exit_date,
                    'equity': current_equity
                })
            
            # Calculate daily returns
            if len(equity_curve) > 1:
                equity_df = pd.DataFrame(equity_curve)
                equity_df.set_index('date', inplace=True)
                equity_df = equity_df.resample('D').last().fillna(method='ffill')
                
                daily_returns = equity_df['equity'].pct_change().dropna()
                
                # Calculate Sharpe ratio (assuming risk-free rate of 0)
                sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if len(daily_returns) > 0 else 0
                
                # Calculate maximum drawdown
                equity_series = equity_df['equity']
                rolling_max = equity_series.cummax()
                drawdown = (equity_series - rolling_max) / rolling_max
                max_drawdown_percentage = drawdown.min() * 100
                max_drawdown = (equity_series - rolling_max).min()
            else:
                sharpe_ratio = 0
                max_drawdown = 0
                max_drawdown_percentage = 0
            
            return {
                "status": "ok",
                "metrics": {
                    "win_rate": win_rate,
                    "profit_factor": profit_factor,
                    "average_win": average_win,
                    "average_loss": average_loss,
                    "largest_win": largest_win,
                    "largest_loss": largest_loss,
                    "average_holding_period": average_holding_period,
                    "sharpe_ratio": sharpe_ratio,
                    "max_drawdown": max_drawdown,
                    "max_drawdown_percentage": max_drawdown_percentage
                },
                "equity_curve": equity_curve
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_risk_profile_recommendations(self, user_id: int) -> Dict[str, Any]:
        """
        Generate risk profile recommendations based on trading history.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing risk profile recommendations
        """
        try:
            # Get user's risk profile
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found")
                return {
                    "status": "error",
                    "message": "User not found"
                }
            
            # Get portfolio metrics
            metrics = self.calculate_portfolio_metrics(user_id)
            if metrics["status"] == "error":
                return metrics
            
            # If no trades, return default recommendations
            if "message" in metrics and metrics["message"] == "No completed trades found":
                return {
                    "status": "ok",
                    "message": "No trading history found. Using default recommendations.",
                    "current_profile": user.risk_profile.to_dict() if user.risk_profile else None,
                    "recommendations": {
                        "max_portfolio_risk": 2.0,  # 2% risk per trade
                        "max_portfolio_exposure": 50.0,  # 50% max exposure
                        "max_stock_allocation": 10.0,  # 10% per stock
                        "max_loss_per_trade": 25.0,  # 25% max loss per trade
                        "risk_reward_ratio": 2.0  # 2:1 risk-reward ratio
                    }
                }
            
            # Extract metrics
            win_rate = metrics["metrics"]["win_rate"]
            profit_factor = metrics["metrics"]["profit_factor"]
            average_holding_period = metrics["metrics"]["average_holding_period"]
            sharpe_ratio = metrics["metrics"]["sharpe_ratio"]
            max_drawdown_percentage = abs(metrics["metrics"]["max_drawdown_percentage"])
            
            # Generate recommendations based on metrics
            recommendations = {}
            
            # Max portfolio risk (risk per trade)
            if win_rate > 0.7 and profit_factor > 2.0:
                # High win rate and profit factor - can take more risk
                recommendations["max_portfolio_risk"] = min(3.0, user.risk_profile.max_portfolio_risk * 1.2 if user.risk_profile else 3.0)
            elif win_rate < 0.4 or profit_factor < 1.0:
                # Low win rate or losing - reduce risk
                recommendations["max_portfolio_risk"] = max(0.5, user.risk_profile.max_portfolio_risk * 0.8 if user.risk_profile else 1.0)
            else:
                # Moderate performance - maintain or slightly adjust
                recommendations["max_portfolio_risk"] = user.risk_profile.max_portfolio_risk if user.risk_profile else 2.0
            
            # Max portfolio exposure
            if sharpe_ratio > 1.5 and max_drawdown_percentage < 10:
                # Good risk-adjusted returns - can increase exposure
                recommendations["max_portfolio_exposure"] = min(70.0, user.risk_profile.max_portfolio_exposure * 1.2 if user.risk_profile else 60.0)
            elif sharpe_ratio < 0.5 or max_drawdown_percentage > 20:
                # Poor risk-adjusted returns - reduce exposure
                recommendations["max_portfolio_exposure"] = max(30.0, user.risk_profile.max_portfolio_exposure * 0.8 if user.risk_profile else 40.0)
            else:
                # Moderate performance - maintain or slightly adjust
                recommendations["max_portfolio_exposure"] = user.risk_profile.max_portfolio_exposure if user.risk_profile else 50.0
            
            # Max stock allocation
            # For Mag7 stocks, we want to ensure diversification
            recommendations["max_stock_allocation"] = min(15.0, user.risk_profile.max_stock_allocation if user.risk_profile else 10.0)
            
            # Max loss per trade
            # For 7DTE options, we need to consider time decay
            if average_holding_period < 3:
                # Short holding period - tighter stop-loss
                recommendations["max_loss_per_trade"] = min(20.0, user.risk_profile.max_loss_per_trade * 0.9 if user.risk_profile else 20.0)
            elif average_holding_period > 5:
                # Longer holding period - wider stop-loss
                recommendations["max_loss_per_trade"] = max(30.0, user.risk_profile.max_loss_per_trade * 1.1 if user.risk_profile else 30.0)
            else:
                # Moderate holding period - maintain
                recommendations["max_loss_per_trade"] = user.risk_profile.max_loss_per_trade if user.risk_profile else 25.0
            
            # Risk-reward ratio
            if win_rate < 0.5:
                # Lower win rate - need higher reward
                recommendations["risk_reward_ratio"] = max(2.5, user.risk_profile.risk_reward_ratio * 1.2 if user.risk_profile else 2.5)
            else:
                # Higher win rate - can accept lower reward
                recommendations["risk_reward_ratio"] = min(2.0, user.risk_profile.risk_reward_ratio * 0.9 if user.risk_profile else 2.0)
            
            return {
                "status": "ok",
                "current_profile": user.risk_profile.to_dict() if user.risk_profile else None,
                "recommendations": recommendations,
                "metrics_summary": {
                    "win_rate": win_rate,
                    "profit_factor": profit_factor,
                    "average_holding_period": average_holding_period,
                    "sharpe_ratio": sharpe_ratio,
                    "max_drawdown_percentage": max_drawdown_percentage
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating risk profile recommendations: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

