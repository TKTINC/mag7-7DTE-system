from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import date, datetime

class PositionSizeRequest(BaseModel):
    user_id: int
    instrument_id: int
    signal_confidence: float = Field(..., ge=0.0, le=1.0)
    option_price: float = Field(..., gt=0.0)

class PositionSizeResponse(BaseModel):
    contracts: int
    max_capital: float
    risk_per_trade: float
    contract_value: Optional[float] = None
    portfolio_value: Optional[float] = None
    current_allocation: Optional[float] = None
    available_allocation: Optional[float] = None
    confidence_multiplier: Optional[float] = None
    error: Optional[str] = None

class StockExposure(BaseModel):
    value: float
    percentage: float

class Alert(BaseModel):
    type: str
    level: str
    message: str
    symbol: Optional[str] = None
    correlations: Optional[List[Dict[str, Any]]] = None

class PortfolioExposureResponse(BaseModel):
    status: str
    total_exposure: Optional[float] = None
    max_exposure: Optional[float] = None
    exposure_percentage: Optional[float] = None
    stock_exposures: Optional[Dict[str, StockExposure]] = None
    alerts: Optional[List[Alert]] = None
    message: Optional[str] = None

class StopLossTakeProfitRequest(BaseModel):
    position_id: int
    risk_reward_ratio: float = Field(2.0, gt=0.0)

class StopLossTakeProfitResponse(BaseModel):
    status: str
    position_id: Optional[int] = None
    symbol: Optional[str] = None
    position_type: Optional[str] = None
    entry_price: Optional[float] = None
    current_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    current_risk_reward: Optional[float] = None
    max_loss_percentage: Optional[float] = None
    pct_to_stop_loss: Optional[float] = None
    pct_to_take_profit: Optional[float] = None
    days_to_expiration: Optional[int] = None
    message: Optional[str] = None

class StopLossTakeProfitCheckResponse(BaseModel):
    status: str
    position_id: Optional[int] = None
    symbol: Optional[str] = None
    position_type: Optional[str] = None
    entry_price: Optional[float] = None
    current_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    stop_loss_hit: Optional[bool] = None
    take_profit_hit: Optional[bool] = None
    pct_to_stop_loss: Optional[float] = None
    pct_to_take_profit: Optional[float] = None
    message: Optional[str] = None
    recommendations: Optional[Dict[str, float]] = None

class EquityPoint(BaseModel):
    date: date
    equity: float

class PortfolioMetrics(BaseModel):
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    average_win: Optional[float] = None
    average_loss: Optional[float] = None
    largest_win: Optional[float] = None
    largest_loss: Optional[float] = None
    average_holding_period: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    max_drawdown_percentage: Optional[float] = None

class PortfolioMetricsResponse(BaseModel):
    status: str
    metrics: Optional[PortfolioMetrics] = None
    equity_curve: Optional[List[EquityPoint]] = None
    message: Optional[str] = None

class RiskProfile(BaseModel):
    max_portfolio_risk: float
    max_portfolio_exposure: float
    max_stock_allocation: float
    max_loss_per_trade: float
    risk_reward_ratio: float

class MetricsSummary(BaseModel):
    win_rate: float
    profit_factor: float
    average_holding_period: float
    sharpe_ratio: float
    max_drawdown_percentage: float

class RiskProfileRecommendationsResponse(BaseModel):
    status: str
    current_profile: Optional[RiskProfile] = None
    recommendations: Optional[RiskProfile] = None
    metrics_summary: Optional[MetricsSummary] = None
    message: Optional[str] = None

