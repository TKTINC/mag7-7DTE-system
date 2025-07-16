from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON, Text, Enum, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.models.market_data import Base

class SignalType(enum.Enum):
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

class SignalSource(enum.Enum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    VOLATILITY = "volatility"
    MOMENTUM = "momentum"
    EARNINGS = "earnings"
    SENTIMENT = "sentiment"
    CORRELATION = "correlation"
    ENSEMBLE = "ensemble"

class SignalStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    EXECUTED = "executed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    signal_type = Column(Enum(SignalType), nullable=False)
    signal_source = Column(Enum(SignalSource), nullable=False)
    status = Column(Enum(SignalStatus), nullable=False, default=SignalStatus.PENDING)
    
    # Signal parameters
    entry_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=False)  # 0.0 to 1.0
    time_frame = Column(String(20), nullable=False)  # e.g., "7d", "14d", etc.
    
    # Options-specific parameters
    option_id = Column(Integer, ForeignKey("options.id"), nullable=True)
    option_strike = Column(Float, nullable=True)
    option_expiration = Column(DateTime, nullable=True)
    implied_volatility = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)
    gamma = Column(Float, nullable=True)
    theta = Column(Float, nullable=True)
    vega = Column(Float, nullable=True)
    
    # Fundamental factors
    earnings_impact = Column(Float, nullable=True)  # -1.0 to 1.0, impact of earnings on signal
    valuation_impact = Column(Float, nullable=True)  # -1.0 to 1.0, impact of valuation on signal
    sentiment_impact = Column(Float, nullable=True)  # -1.0 to 1.0, impact of sentiment on signal
    
    # Signal metadata
    generation_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    expiration_time = Column(DateTime, nullable=True)
    execution_time = Column(DateTime, nullable=True)
    close_time = Column(DateTime, nullable=True)
    
    # Performance tracking
    profit_loss = Column(Float, nullable=True)
    profit_loss_percent = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    
    # Additional data
    parameters = Column(JSON, nullable=True)  # Additional strategy-specific parameters
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # Array of tags for filtering
    
    # Relationships
    instrument = relationship("Instrument", back_populates="signals")
    option = relationship("Option", back_populates="signals")
    trades = relationship("Trade", back_populates="signal")
    signal_factors = relationship("SignalFactor", back_populates="signal")

# Add relationship to Instrument model
from app.models.market_data import Instrument, Option
Instrument.signals = relationship("Signal", back_populates="instrument")
Option.signals = relationship("Signal", back_populates="option")

class SignalFactor(Base):
    __tablename__ = "signal_factors"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False)
    factor_name = Column(String(100), nullable=False)
    factor_value = Column(Float, nullable=False)
    factor_weight = Column(Float, nullable=False)
    factor_category = Column(String(50), nullable=False)  # e.g., "technical", "fundamental", etc.
    factor_description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    signal = relationship("Signal", back_populates="signal_factors")

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    option_id = Column(Integer, ForeignKey("options.id"), nullable=True)
    
    # Trade details
    trade_type = Column(String(20), nullable=False)  # "entry", "exit", "adjustment"
    direction = Column(String(10), nullable=False)  # "buy", "sell"
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, nullable=True)
    execution_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Trade metadata
    broker = Column(String(50), nullable=True)
    order_id = Column(String(100), nullable=True)
    execution_id = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    signal = relationship("Signal", back_populates="trades")
    instrument = relationship("Instrument")
    option = relationship("Option")

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    signal_type = Column(Enum(SignalType), nullable=False)
    time_frame = Column(String(20), nullable=False)  # e.g., "7d", "14d", etc.
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Strategy parameters
    parameters = Column(JSON, nullable=False)  # Strategy-specific parameters
    risk_score = Column(Float, nullable=False)  # 1.0 to 10.0, higher is riskier
    
    # Performance metrics
    win_rate = Column(Float, nullable=True)
    average_profit = Column(Float, nullable=True)
    average_loss = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    instruments = relationship("Instrument", secondary="strategy_instruments")
    
# Association table for many-to-many relationship between strategies and instruments
strategy_instruments = Table(
    "strategy_instruments",
    Base.metadata,
    Column("strategy_id", Integer, ForeignKey("strategies.id"), primary_key=True),
    Column("instrument_id", Integer, ForeignKey("instruments.id"), primary_key=True)
)

