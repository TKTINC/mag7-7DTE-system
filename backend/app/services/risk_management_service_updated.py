"""
Risk Management Service for Mag7-7DTE-System
Implements comprehensive risk management with enhanced bet sizing requirements.

Account Size: $100,000+
Minimum Bet Size: $33,000 (33% of account)
Maximum Bet Size: Variable based on signal strength, up to $66,000 (66% of account)
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PartialProfitTaking:
    """Model for tracking partial profit taking events."""
    def __init__(self, position_id: int, percentage_closed: float, price: float, 
                profit_percentage: float, timestamp: datetime):
        self.position_id = position_id
        self.percentage_closed = percentage_closed
        self.price = price
        self.profit_percentage = profit_percentage
        self.timestamp = timestamp


class RiskManagementService:
    """
    Service for managing risk in the Mag7-7DTE-System.
    """
    
    def __init__(self, db: Session):
        self.db = db
        logger.info("Risk Management Service initialized")
    
    def calculate_position_size(self, 
                               user_id: int, 
                               instrument_id: int, 
                               signal_confidence: float,
                               option_price: float) -> Dict[str, Any]:
        """
        Calculate the recommended position size based on user's risk profile,
        portfolio value, and signal confidence.
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
            max_portfolio_risk = user.risk_profile.max_portfolio_risk
            portfolio_value = portfolio.total_value
            
            # Base risk per trade
            risk_per_trade = portfolio_value * (max_portfolio_risk / 100)
            
            # Adjust risk based on signal confidence
            confidence_multiplier = 0.5 + signal_confidence
            adjusted_risk = risk_per_trade * confidence_multiplier
            
            # Calculate max capital to allocate
            max_capital = adjusted_risk
            
            # Enforce minimum position size of $33,000 or 33% of portfolio
            min_position_size = max(33000.0, portfolio_value * 0.33)
            
            # Calculate number of contracts
            contract_value = option_price * 100
            min_contracts = math.ceil(min_position_size / contract_value)
            
            # Apply confidence-based scaling
            if signal_confidence >= 0.9:
                # Very high confidence - up to 200% of minimum
                max_scaling = 2.0
            elif signal_confidence >= 0.8:
                # High confidence - up to 150% of minimum
                max_scaling = 1.5
            elif signal_confidence >= 0.7:
                # Good confidence - up to 125% of minimum
                max_scaling = 1.25
            else:
                # Base confidence - minimum bet size
                max_scaling = 1.0
            
            # Calculate scaled contracts
            scaled_contracts = min(
                int(min_contracts * max_scaling),
                int(max_capital / contract_value)
            )
            
            # Ensure we never go below minimum
            contracts = max(min_contracts, scaled_contracts)
            
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
            
            # Final position size calculation
            position_value = contracts * contract_value
            
            # If position value exceeds available allocation, adjust
            if position_value > available_allocation:
                contracts = int(available_allocation / contract_value)
                position_value = contracts * contract_value
            
            # Final check to ensure minimum position size
            if position_value < min_position_size and available_allocation >= min_position_size:
                contracts = math.ceil(min_position_size / contract_value)
                position_value = contracts * contract_value
            
            # Apply fundamental adjustment
            fundamental_adjustment = self.calculate_fundamental_adjustment(
                instrument_id, signal_confidence
            )
            
            # Apply correlation adjustment
            correlation_adjustment = self.calculate_correlation_adjustment(
                instrument_id, portfolio.id
            )
            
            # Combine adjustments
            combined_adjustment = fundamental_adjustment * correlation_adjustment
            
            # Apply combined adjustment to contracts
            adjusted_contracts = int(contracts * combined_adjustment)
            
            # Ensure we never go below minimum
            final_contracts = max(min_contracts, adjusted_contracts)
            
            # Calculate final position value
            final_position_value = final_contracts * contract_value
            
            return {
                "contracts": final_contracts,
                "min_contracts": min_contracts,
                "max_contracts": scaled_contracts,
                "position_value": final_position_value,
                "min_position_size": min_position_size,
                "max_capital": max_capital,
                "risk_per_trade": adjusted_risk,
                "contract_value": contract_value,
                "portfolio_value": portfolio_value,
                "current_allocation": current_allocation,
                "available_allocation": available_allocation,
                "confidence_multiplier": confidence_multiplier,
                "max_scaling": max_scaling,
                "fundamental_adjustment": fundamental_adjustment,
                "correlation_adjustment": correlation_adjustment,
                "combined_adjustment": combined_adjustment
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {
                "contracts": 0,
                "max_capital": 0,
                "risk_per_trade": 0,
                "error": str(e)
            }
    
    def calculate_fundamental_adjustment(self, 
                                        instrument_id: int, 
                                        signal_confidence: float) -> float:
        """
        Calculate position size adjustment based on fundamental factors.
        """
        try:
            # Get instrument
            instrument = self.db.query(Instrument).filter(Instrument.id == instrument_id).first()
            if not instrument:
                return 1.0  # Default to no adjustment
            
            # Get fundamental data
            fundamental_data = self.db.query(FundamentalData).filter(
                FundamentalData.instrument_id == instrument_id
            ).order_by(FundamentalData.date.desc()).first()
            
            if not fundamental_data:
                return 1.0  # Default to no adjustment
            
            # Calculate fundamental score (0.0 to 1.0)
            fundamental_score = 0.5  # Default neutral score
            
            # Earnings surprise factor
            if fundamental_data.earnings_surprise_pct > 10:
                fundamental_score += 0.2  # Significant positive surprise
            elif fundamental_data.earnings_surprise_pct > 5:
                fundamental_score += 0.1  # Moderate positive surprise
            elif fundamental_data.earnings_surprise_pct < -10:
                fundamental_score -= 0.2  # Significant negative surprise
            elif fundamental_data.earnings_surprise_pct < -5:
                fundamental_score -= 0.1  # Moderate negative surprise
            
            # Analyst rating factor
            if fundamental_data.analyst_rating_buy > 70:
                fundamental_score += 0.1  # Strong buy consensus
            elif fundamental_data.analyst_rating_sell > 50:
                fundamental_score -= 0.1  # Strong sell consensus
            
            # Valuation factor
            if fundamental_data.pe_ratio < fundamental_data.sector_avg_pe * 0.7:
                fundamental_score += 0.1  # Significantly undervalued
            elif fundamental_data.pe_ratio > fundamental_data.sector_avg_pe * 1.5:
                fundamental_score -= 0.1  # Significantly overvalued
            
            # Clamp score between 0.0 and 1.0
            fundamental_score = max(0.0, min(1.0, fundamental_score))
            
            # Calculate adjustment factor (0.5 to 1.5)
            adjustment_factor = 0.5 + fundamental_score
            
            # Combine with signal confidence
            combined_factor = (adjustment_factor + signal_confidence) / 2
            
            # Scale to desired range (1.0 to 2.0)
            scaling_factor = 1.0 + combined_factor
            
            return scaling_factor
            
        except Exception as e:
            logger.error(f"Error calculating fundamental adjustment: {e}")
            return 1.0  # Default to no adjustment
    
    def calculate_correlation_adjustment(self, 
                                        instrument_id: int, 
                                        portfolio_id: int) -> float:
        """
        Calculate position size adjustment based on correlation with existing positions.
        """
        try:
            # Get active positions in portfolio
            active_positions = self.db.query(Position).filter(
                Position.portfolio_id == portfolio_id,
                Position.status == 'ACTIVE'
            ).all()
            
            if not active_positions:
                return 1.0  # No existing positions, no correlation
            
            # Get correlation matrix
            correlation_matrix = self.calculate_correlation_matrix()
            if correlation_matrix is None:
                return 0.8  # Conservative default if no correlation data
            
            # Get instrument symbol
            instrument = self.db.query(Instrument).filter(Instrument.id == instrument_id).first()
            if not instrument:
                return 0.8  # Conservative default if instrument not found
            
            # Calculate average correlation with existing positions
            correlations = []
            for position in active_positions:
                position_instrument = self.db.query(Instrument).filter(
                    Instrument.id == position.instrument_id
                ).first()
                
                if position_instrument and position_instrument.symbol in correlation_matrix.index:
                    if instrument.symbol in correlation_matrix.columns:
                        correlation = correlation_matrix.loc[position_instrument.symbol, instrument.symbol]
                        correlations.append(abs(correlation))
            
            if not correlations:
                return 1.0  # No correlation data found
            
            avg_correlation = sum(correlations) / len(correlations)
            
            # Adjust position size based on correlation
            if avg_correlation > 0.8:
                return 0.5  # High correlation, reduce position size
            elif avg_correlation > 0.6:
                return 0.75  # Moderate correlation, slightly reduce position
            elif avg_correlation < 0.3:
                return 1.2  # Low correlation, increase position size
            else:
                return 1.0  # Normal correlation, no adjustment
            
        except Exception as e:
            logger.error(f"Error calculating correlation adjustment: {e}")
            return 0.8  # Conservative default
    
    def calculate_correlation_matrix(self) -> Optional[pd.DataFrame]:
        """
        Calculate correlation matrix for Magnificent 7 stocks.
        """
        try:
            # In a real implementation, this would fetch actual price data
            # and calculate correlations. For this example, we'll return a
            # simulated correlation matrix.
            
            # Magnificent 7 stocks
            symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META']
            
            # Create a simulated correlation matrix
            np.random.seed(42)  # For reproducibility
            corr_matrix = np.random.rand(7, 7) * 0.5 + 0.3  # Random values between 0.3 and 0.8
            
            # Make the matrix symmetric
            corr_matrix = (corr_matrix + corr_matrix.T) / 2
            
            # Set diagonal to 1.0
            np.fill_diagonal(corr_matrix, 1.0)
            
            # Convert to DataFrame
            df = pd.DataFrame(corr_matrix, index=symbols, columns=symbols)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return None
    
    def calculate_stop_loss_take_profit(self, 
                                       position_id: int, 
                                       entry_price: float, 
                                       days_to_expiration: int,
                                       risk_level: str = "normal") -> Dict[str, Any]:
        """
        Calculate stop-loss and take-profit levels for a position.
        """
        try:
            # Define risk levels
            risk_levels = {
                "low": 0.10,      # 10% loss
                "normal": 0.15,   # 15% loss
                "high": 0.20      # 20% loss
            }
            
            # Get risk percentage
            risk_pct = risk_levels.get(risk_level, 0.15)
            
            # Adjust risk based on days to expiration
            dte_factor = min(1.0, days_to_expiration / 7.0)  # Scale based on 7 DTE
            adjusted_risk_pct = risk_pct * dte_factor
            
            # Calculate stop-loss price for long positions
            stop_loss_price = entry_price * (1 - adjusted_risk_pct)
            
            # Calculate take-profit based on risk-reward ratio
            risk = entry_price - stop_loss_price
            risk_reward_ratio = 2.0  # 2:1 risk-reward ratio
            
            # Calculate take-profit price
            take_profit_price = entry_price + (risk * risk_reward_ratio)
            
            return {
                "position_id": position_id,
                "entry_price": entry_price,
                "stop_loss_price": stop_loss_price,
                "take_profit_price": take_profit_price,
                "risk_percentage": adjusted_risk_pct,
                "risk_reward_ratio": risk_reward_ratio,
                "days_to_expiration": days_to_expiration
            }
            
        except Exception as e:
            logger.error(f"Error calculating stop-loss and take-profit: {e}")
            return {"error": str(e)}
    
    def calculate_dynamic_take_profit(self, 
                                     position_id: int, 
                                     current_profit_pct: float = 0.0) -> Dict[str, Any]:
        """
        Calculate dynamic take-profit levels based on current profit and risk-reward.
        
        As a position moves into profit, the risk-reward ratio is adjusted to
        allow for greater upside potential while protecting gains.
        """
        try:
            # Get position
            position = self.db.query(Position).filter(Position.id == position_id).first()
            if not position:
                return {"error": "Position not found"}
            
            # Get initial stop-loss
            initial_stop_loss = position.stop_loss_price
            if not initial_stop_loss:
                # Calculate default stop-loss if not set
                initial_stop_loss = position.entry_price * 0.8  # 20% stop-loss
            
            # Calculate initial risk
            initial_risk = abs(position.entry_price - initial_stop_loss)
            
            # Base risk-reward ratios
            if current_profit_pct < 0.15:
                # Initial stage: 1:1.5 risk-reward
                risk_reward_ratio = 1.5
            elif current_profit_pct < 0.30:
                # Intermediate stage: 1:2 risk-reward
                risk_reward_ratio = 2.0
            else:
                # Advanced stage: 1:3 risk-reward
                risk_reward_ratio = 3.0
            
            # Calculate take-profit price
            take_profit_price = position.entry_price + (initial_risk * risk_reward_ratio)
            
            # Calculate trailing stop based on current profit
            if current_profit_pct > 0.30:
                # Lock in 50% of gains
                trailing_stop = position.entry_price + (position.current_price - position.entry_price) * 0.5
            elif current_profit_pct > 0.15:
                # Lock in 25% of gains
                trailing_stop = position.entry_price + (position.current_price - position.entry_price) * 0.25
            else:
                # Use initial stop-loss
                trailing_stop = initial_stop_loss
            
            # Use the higher of initial stop-loss or trailing stop
            adjusted_stop_loss = max(initial_stop_loss, trailing_stop)
            
            return {
                "position_id": position_id,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "current_profit_pct": current_profit_pct,
                "initial_stop_loss": initial_stop_loss,
                "adjusted_stop_loss": adjusted_stop_loss,
                "take_profit_price": take_profit_price,
                "risk_reward_ratio": risk_reward_ratio,
                "initial_risk": initial_risk
            }
            
        except Exception as e:
            logger.error(f"Error calculating dynamic take-profit: {e}")
            return {"error": str(e)}
    
    def implement_partial_profit_taking(self, 
                                       position_id: int, 
                                       current_profit_pct: float) -> Dict[str, Any]:
        """
        Implement partial profit taking strategy based on profit thresholds.
        
        Returns the percentage of position to close and updates position tracking.
        """
        try:
            # Get position
            position = self.db.query(Position).filter(Position.id == position_id).first()
            if not position:
                return {"error": "Position not found"}
            
            # Get partial profit taking history
            profit_taking_history = self.db.query(PartialProfitTaking).filter(
                PartialProfitTaking.position_id == position_id
            ).all()
            
            # Calculate total percentage already taken
            total_pct_taken = sum(ppt.percentage_closed for ppt in profit_taking_history)
            
            # Define profit taking thresholds
            thresholds = [
                {"profit_pct": 0.20, "take_pct": 0.25},  # At 20% profit, take 25% off
                {"profit_pct": 0.35, "take_pct": 0.25},  # At 35% profit, take another 25% off
                {"profit_pct": 0.50, "take_pct": 0.25}   # At 50% profit, take another 25% off
            ]
            
            # Check if any threshold is triggered
            for threshold in thresholds:
                # Check if we've hit this profit level and haven't taken this much off yet
                if current_profit_pct >= threshold["profit_pct"] and total_pct_taken < sum(t["take_pct"] for t in thresholds if t["profit_pct"] <= threshold["profit_pct"]):
                    # Calculate how much to take off now
                    target_total_pct = sum(t["take_pct"] for t in thresholds if t["profit_pct"] <= threshold["profit_pct"])
                    pct_to_take_now = target_total_pct - total_pct_taken
                    
                    # Ensure we don't take more than what's left
                    pct_to_take_now = min(pct_to_take_now, 1.0 - total_pct_taken)
                    
                    if pct_to_take_now > 0:
                        # Record this partial profit taking
                        new_profit_taking = PartialProfitTaking(
                            position_id=position_id,
                            percentage_closed=pct_to_take_now,
                            price=position.current_price,
                            profit_percentage=current_profit_pct,
                            timestamp=datetime.utcnow()
                        )
                        self.db.add(new_profit_taking)
                        self.db.commit()
                        
                        return {
                            "action": "partial_close",
                            "position_id": position_id,
                            "percentage_to_close": pct_to_take_now,
                            "contracts_to_close": int(position.quantity * pct_to_take_now),
                            "profit_percentage": current_profit_pct,
                            "threshold_triggered": threshold["profit_pct"],
                            "total_percentage_closed": total_pct_taken + pct_to_take_now
                        }
            
            return {
                "action": "hold",
                "position_id": position_id,
                "profit_percentage": current_profit_pct,
                "total_percentage_closed": total_pct_taken
            }
            
        except Exception as e:
            logger.error(f"Error implementing partial profit taking: {e}")
            return {"error": str(e)}
    
    def adjust_take_profit_for_dte(self, 
                                  position_id: int) -> Dict[str, Any]:
        """
        Adjust take-profit levels based on days to expiration.
        
        As expiration approaches, take-profit levels are adjusted to account
        for accelerating theta decay and reduced time for price movement.
        """
        try:
            # Get position
            position = self.db.query(Position).filter(Position.id == position_id).first()
            if not position:
                return {"error": "Position not found"}
            
            # Calculate days to expiration
            days_to_expiration = (position.expiration_date - datetime.utcnow().date()).days
            
            # Base profit taking thresholds
            base_thresholds = [
                {"profit_pct": 0.20, "take_pct": 0.25},
                {"profit_pct": 0.35, "take_pct": 0.25},
                {"profit_pct": 0.50, "take_pct": 0.25}
            ]
            
            # Adjust thresholds based on DTE
            adjusted_thresholds = []
            
            for threshold in base_thresholds:
                adjusted_threshold = threshold.copy()
                
                if days_to_expiration <= 1:
                    # 1 DTE: Reduce profit targets by 60%
                    adjusted_threshold["profit_pct"] = threshold["profit_pct"] * 0.4
                elif days_to_expiration <= 2:
                    # 2 DTE: Reduce profit targets by 40%
                    adjusted_threshold["profit_pct"] = threshold["profit_pct"] * 0.6
                elif days_to_expiration <= 3:
                    # 3 DTE: Reduce profit targets by 25%
                    adjusted_threshold["profit_pct"] = threshold["profit_pct"] * 0.75
                elif days_to_expiration <= 5:
                    # 4-5 DTE: Reduce profit targets by 10%
                    adjusted_threshold["profit_pct"] = threshold["profit_pct"] * 0.9
                
                adjusted_thresholds.append(adjusted_threshold)
            
            return {
                "position_id": position_id,
                "days_to_expiration": days_to_expiration,
                "base_thresholds": base_thresholds,
                "adjusted_thresholds": adjusted_thresholds
            }
            
        except Exception as e:
            logger.error(f"Error adjusting take-profit for DTE: {e}")
            return {"error": str(e)}
    
    def calculate_portfolio_risk_metrics(self, portfolio_id: int) -> Dict[str, Any]:
        """
        Calculate comprehensive risk metrics for a portfolio.
        """
        try:
            # Get portfolio
            portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio:
                return {"error": "Portfolio not found"}
            
            # Get active positions
            active_positions = self.db.query(Position).filter(
                Position.portfolio_id == portfolio_id,
                Position.status == 'ACTIVE'
            ).all()
            
            # Calculate total exposure
            total_exposure = sum(p.current_value for p in active_positions)
            
            # Calculate exposure percentage
            exposure_pct = total_exposure / portfolio.total_value if portfolio.total_value > 0 else 0
            
            # Calculate exposure by stock
            exposure_by_stock = {}
            for position in active_positions:
                instrument = self.db.query(Instrument).filter(Instrument.id == position.instrument_id).first()
                if instrument:
                    symbol = instrument.symbol
                    if symbol not in exposure_by_stock:
                        exposure_by_stock[symbol] = 0
                    exposure_by_stock[symbol] += position.current_value
            
            # Calculate exposure percentages by stock
            exposure_pct_by_stock = {
                symbol: value / portfolio.total_value
                for symbol, value in exposure_by_stock.items()
            }
            
            # Calculate correlation risk
            correlation_matrix = self.calculate_correlation_matrix()
            correlation_risk = 0.5  # Default moderate risk
            
            if correlation_matrix is not None and len(active_positions) > 1:
                # Get symbols of active positions
                position_symbols = []
                for position in active_positions:
                    instrument = self.db.query(Instrument).filter(Instrument.id == position.instrument_id).first()
                    if instrument and instrument.symbol in correlation_matrix.index:
                        position_symbols.append(instrument.symbol)
                
                if len(position_symbols) > 1:
                    # Extract correlation submatrix for active positions
                    submatrix = correlation_matrix.loc[position_symbols, position_symbols]
                    
                    # Calculate average correlation
                    corr_values = []
                    for i in range(len(position_symbols)):
                        for j in range(i+1, len(position_symbols)):
                            corr_values.append(submatrix.iloc[i, j])
                    
                    correlation_risk = sum(corr_values) / len(corr_values) if corr_values else 0.5
            
            return {
                "portfolio_id": portfolio_id,
                "total_value": portfolio.total_value,
                "total_exposure": total_exposure,
                "exposure_percentage": exposure_pct,
                "exposure_by_stock": exposure_by_stock,
                "exposure_percentage_by_stock": exposure_pct_by_stock,
                "correlation_risk": correlation_risk,
                "active_positions_count": len(active_positions)
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio risk metrics: {e}")
            return {"error": str(e)}
    
    def monitor_overnight_risk(self, portfolio_id: int) -> Dict[str, Any]:
        """
        Monitor overnight risk for positions in a portfolio.
        
        This includes checking for upcoming events, news sentiment,
        and other factors that could impact positions overnight.
        """
        try:
            # Get active positions
            active_positions = self.db.query(Position).filter(
                Position.portfolio_id == portfolio_id,
                Position.status == 'ACTIVE'
            ).all()
            
            if not active_positions:
                return {"message": "No active positions to monitor"}
            
            # Check for upcoming earnings
            positions_with_earnings = []
            for position in active_positions:
                instrument = self.db.query(Instrument).filter(Instrument.id == position.instrument_id).first()
                if not instrument:
                    continue
                
                # Get fundamental data
                fundamental_data = self.db.query(FundamentalData).filter(
                    FundamentalData.instrument_id == instrument.id
                ).order_by(FundamentalData.date.desc()).first()
                
                if fundamental_data and fundamental_data.next_earnings_date:
                    days_to_earnings = (fundamental_data.next_earnings_date - datetime.utcnow().date()).days
                    
                    if days_to_earnings <= 7:  # Within our 7DTE window
                        positions_with_earnings.append({
                            "position_id": position.id,
                            "symbol": instrument.symbol,
                            "days_to_earnings": days_to_earnings,
                            "current_value": position.current_value
                        })
            
            # Check for recent news sentiment
            positions_with_news = []
            for position in active_positions:
                instrument = self.db.query(Instrument).filter(Instrument.id == position.instrument_id).first()
                if not instrument:
                    continue
                
                # Get news sentiment
                news_sentiment = self.db.query(NewsSentiment).filter(
                    NewsSentiment.instrument_id == instrument.id
                ).order_by(NewsSentiment.timestamp.desc()).first()
                
                if news_sentiment:
                    hours_since_news = (datetime.utcnow() - news_sentiment.timestamp).total_seconds() / 3600
                    
                    if hours_since_news <= 24:  # News within last 24 hours
                        positions_with_news.append({
                            "position_id": position.id,
                            "symbol": instrument.symbol,
                            "sentiment_score": news_sentiment.sentiment_score,
                            "hours_since_news": hours_since_news,
                            "current_value": position.current_value
                        })
            
            # Calculate overall overnight risk
            overnight_risk = 0.0
            
            # Earnings risk
            earnings_risk = len(positions_with_earnings) / len(active_positions) if active_positions else 0
            
            # News risk
            news_risk = 0.0
            if positions_with_news:
                # Average sentiment score (0 = negative, 0.5 = neutral, 1 = positive)
                avg_sentiment = sum(p["sentiment_score"] for p in positions_with_news) / len(positions_with_news)
                
                # Convert to risk (higher for negative sentiment)
                news_risk = 1.0 - avg_sentiment
            
            # Combine risks
            overnight_risk = 0.4 * earnings_risk + 0.6 * news_risk
            
            return {
                "portfolio_id": portfolio_id,
                "overnight_risk": overnight_risk,
                "earnings_risk": earnings_risk,
                "news_risk": news_risk,
                "positions_with_earnings": positions_with_earnings,
                "positions_with_news": positions_with_news,
                "total_positions": len(active_positions)
            }
            
        except Exception as e:
            logger.error(f"Error monitoring overnight risk: {e}")
            return {"error": str(e)}


# Mock classes for testing
class User:
    def __init__(self, id, risk_profile=None):
        self.id = id
        self.risk_profile = risk_profile

class RiskProfile:
    def __init__(self, max_portfolio_risk=2.0, max_stock_allocation=20.0):
        self.max_portfolio_risk = max_portfolio_risk
        self.max_stock_allocation = max_stock_allocation

class Portfolio:
    def __init__(self, id, user_id, total_value):
        self.id = id
        self.user_id = user_id
        self.total_value = total_value

class Instrument:
    def __init__(self, id, symbol):
        self.id = id
        self.symbol = symbol

class Position:
    def __init__(self, id, portfolio_id, instrument_id, entry_price, current_price, quantity, status):
        self.id = id
        self.portfolio_id = portfolio_id
        self.instrument_id = instrument_id
        self.entry_price = entry_price
        self.current_price = current_price
        self.quantity = quantity
        self.status = status
        self.current_value = current_price * quantity * 100  # Assuming options contracts
        self.stop_loss_price = entry_price * 0.8  # Default 20% stop-loss
        self.expiration_date = (datetime.utcnow() + timedelta(days=7)).date()  # Default 7 DTE

class FundamentalData:
    def __init__(self, instrument_id, date, earnings_surprise_pct, analyst_rating_buy, analyst_rating_sell, pe_ratio, sector_avg_pe, next_earnings_date=None):
        self.instrument_id = instrument_id
        self.date = date
        self.earnings_surprise_pct = earnings_surprise_pct
        self.analyst_rating_buy = analyst_rating_buy
        self.analyst_rating_sell = analyst_rating_sell
        self.pe_ratio = pe_ratio
        self.sector_avg_pe = sector_avg_pe
        self.next_earnings_date = next_earnings_date

class NewsSentiment:
    def __init__(self, instrument_id, timestamp, sentiment_score):
        self.instrument_id = instrument_id
        self.timestamp = timestamp
        self.sentiment_score = sentiment_score

