from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON, Text, Enum, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.models.market_data import Base

class AccountType(enum.Enum):
    LIVE = "live"
    PAPER = "paper"
    BACKTEST = "backtest"

class PositionStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    PARTIALLY_CLOSED = "partially_closed"

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # Foreign key to users table (if implemented)
    name = Column(String(100), nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)
    broker = Column(String(50), nullable=True)
    broker_account_id = Column(String(100), nullable=True)
    
    # Account balance
    initial_balance = Column(Float, nullable=False)
    current_balance = Column(Float, nullable=False)
    
    # Account settings
    max_position_size_percent = Column(Float, nullable=False, default=5.0)
    max_portfolio_risk_percent = Column(Float, nullable=False, default=20.0)
    max_sector_exposure_percent = Column(Float, nullable=False, default=30.0)
    
    # Account metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    positions = relationship("Position", back_populates="account")
    portfolio_snapshots = relationship("PortfolioSnapshot", back_populates="account")

class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    option_id = Column(Integer, ForeignKey("options.id"), nullable=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    
    # Position details
    position_type = Column(String(20), nullable=False)  # "long", "short"
    quantity = Column(Integer, nullable=False)
    average_entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    status = Column(Enum(PositionStatus), nullable=False, default=PositionStatus.OPEN)
    
    # Position metrics
    unrealized_pnl = Column(Float, nullable=True)
    unrealized_pnl_percent = Column(Float, nullable=True)
    realized_pnl = Column(Float, nullable=True)
    realized_pnl_percent = Column(Float, nullable=True)
    max_profit = Column(Float, nullable=True)
    max_loss = Column(Float, nullable=True)
    
    # Position dates
    open_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    close_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    
    # Position metadata
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # Array of tags for filtering
    
    # Relationships
    account = relationship("Account", back_populates="positions")
    instrument = relationship("Instrument")
    option = relationship("Option")
    signal = relationship("Signal")
    trades = relationship("PositionTrade", back_populates="position")

class PositionTrade(Base):
    __tablename__ = "position_trades"

    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    
    # Trade details
    trade_type = Column(String(20), nullable=False)  # "open", "close", "adjustment"
    direction = Column(String(10), nullable=False)  # "buy", "sell"
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    commission = Column(Float, nullable=True)
    execution_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Trade metadata
    broker_trade_id = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    position = relationship("Position", back_populates="trades")

class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    # Snapshot details
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    total_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    invested_value = Column(Float, nullable=False)
    
    # Portfolio metrics
    daily_pnl = Column(Float, nullable=True)
    daily_pnl_percent = Column(Float, nullable=True)
    total_pnl = Column(Float, nullable=True)
    total_pnl_percent = Column(Float, nullable=True)
    
    # Risk metrics
    portfolio_beta = Column(Float, nullable=True)
    portfolio_volatility = Column(Float, nullable=True)
    var_95 = Column(Float, nullable=True)  # Value at Risk (95% confidence)
    max_drawdown = Column(Float, nullable=True)
    
    # Exposure metrics
    sector_exposure = Column(JSON, nullable=True)  # JSON object with sector exposures
    stock_exposure = Column(JSON, nullable=True)  # JSON object with stock exposures
    
    # Relationships
    account = relationship("Account", back_populates="portfolio_snapshots")

class RiskProfile(Base):
    __tablename__ = "risk_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Risk parameters
    max_position_size_percent = Column(Float, nullable=False)
    max_portfolio_risk_percent = Column(Float, nullable=False)
    max_sector_exposure_percent = Column(Float, nullable=False)
    max_stock_exposure_percent = Column(Float, nullable=False)
    max_correlation = Column(Float, nullable=False)
    
    # Options-specific risk parameters
    max_delta = Column(Float, nullable=True)
    max_gamma = Column(Float, nullable=True)
    max_theta = Column(Float, nullable=True)
    max_vega = Column(Float, nullable=True)
    
    # Volatility parameters
    max_implied_volatility = Column(Float, nullable=True)
    min_implied_volatility = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    # Metric details
    metric_date = Column(DateTime, nullable=False)
    metric_type = Column(String(50), nullable=False)  # e.g., "daily", "weekly", "monthly"
    
    # Performance metrics
    return_value = Column(Float, nullable=True)
    return_percent = Column(Float, nullable=True)
    alpha = Column(Float, nullable=True)
    beta = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    
    # Benchmark comparison
    benchmark_return = Column(Float, nullable=True)
    benchmark_symbol = Column(String(10), nullable=True)
    excess_return = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

