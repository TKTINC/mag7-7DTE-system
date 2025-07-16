from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class SignalType(str, Enum):
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"
    SHORT_CALL = "short_call"
    SHORT_PUT = "short_put"
    CALL_SPREAD = "call_spread"
    PUT_SPREAD = "put_spread"
    IRON_CONDOR = "iron_condor"
    BUTTERFLY = "butterfly"
    CALENDAR_SPREAD = "calendar_spread"
    DIAGONAL_SPREAD = "diagonal_spread"

class SignalSource(str, Enum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    VOLATILITY = "volatility"
    MOMENTUM = "momentum"
    EARNINGS = "earnings"
    SENTIMENT = "sentiment"
    CORRELATION = "correlation"
    ENSEMBLE = "ensemble"

class SignalStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    EXECUTED = "executed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class SignalFactorBase(BaseModel):
    factor_name: str
    factor_value: float
    factor_weight: float
    factor_category: str
    factor_description: Optional[str] = None

class SignalFactorCreate(SignalFactorBase):
    signal_id: int

class SignalFactorResponse(SignalFactorBase):
    id: int
    signal_id: int
    created_at: datetime

    class Config:
        orm_mode = True

class SignalBase(BaseModel):
    instrument_id: int
    signal_type: SignalType
    signal_source: SignalSource
    status: SignalStatus = SignalStatus.PENDING
    
    # Signal parameters
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    confidence_score: float
    time_frame: str
    
    # Options-specific parameters
    option_id: Optional[int] = None
    option_strike: Optional[float] = None
    option_expiration: Optional[datetime] = None
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    
    # Fundamental factors
    earnings_impact: Optional[float] = None
    valuation_impact: Optional[float] = None
    sentiment_impact: Optional[float] = None
    
    # Signal metadata
    expiration_time: Optional[datetime] = None
    
    # Additional data
    parameters: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

class SignalCreate(SignalBase):
    pass

class SignalUpdate(BaseModel):
    status: Optional[SignalStatus] = None
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    confidence_score: Optional[float] = None
    
    # Performance tracking
    profit_loss: Optional[float] = None
    profit_loss_percent: Optional[float] = None
    max_drawdown: Optional[float] = None
    
    # Signal metadata
    execution_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    
    # Additional data
    parameters: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

class SignalResponse(SignalBase):
    id: int
    generation_time: datetime
    execution_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    
    # Performance tracking
    profit_loss: Optional[float] = None
    profit_loss_percent: Optional[float] = None
    max_drawdown: Optional[float] = None
    
    # Relationships
    signal_factors: Optional[List[SignalFactorResponse]] = None

    class Config:
        orm_mode = True

class SignalPerformanceSummary(BaseModel):
    total_signals: int
    profitable_signals: int
    win_rate: float
    profit_factor: float
    average_profit: float
    average_loss: float
    total_profit_loss: float

