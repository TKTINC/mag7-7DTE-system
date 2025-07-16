from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

Base = declarative_base()

class InstrumentType(enum.Enum):
    ETF = "etf"
    STOCK = "stock"
    INDEX = "index"

class Sector(enum.Enum):
    TECHNOLOGY = "technology"
    COMMUNICATION_SERVICES = "communication_services"
    CONSUMER_DISCRETIONARY = "consumer_discretionary"
    CONSUMER_STAPLES = "consumer_staples"
    ENERGY = "energy"
    FINANCIALS = "financials"
    HEALTH_CARE = "health_care"
    INDUSTRIALS = "industrials"
    MATERIALS = "materials"
    REAL_ESTATE = "real_estate"
    UTILITIES = "utilities"

class MarketCapCategory(enum.Enum):
    MEGA = "mega"  # > $200B
    LARGE = "large"  # $10B - $200B
    MID = "mid"  # $2B - $10B
    SMALL = "small"  # $300M - $2B
    MICRO = "micro"  # < $300M

class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(Enum(InstrumentType), nullable=False)
    sector = Column(Enum(Sector), nullable=True)
    market_cap_category = Column(Enum(MarketCapCategory), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional fields for individual stocks
    earnings_schedule = Column(JSON, nullable=True)  # Store upcoming earnings dates
    fundamental_data_enabled = Column(Boolean, default=False)
    analyst_coverage_enabled = Column(Boolean, default=False)
    
    # Relationships
    options = relationship("Option", back_populates="instrument")
    earnings_data = relationship("EarningsData", back_populates="instrument")
    financial_metrics = relationship("FinancialMetric", back_populates="instrument")
    analyst_ratings = relationship("AnalystRating", back_populates="instrument")

class Option(Base):
    __tablename__ = "options"

    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    symbol = Column(String(50), unique=True, index=True, nullable=False)
    expiration_date = Column(DateTime, nullable=False, index=True)
    strike_price = Column(Float, nullable=False)
    option_type = Column(String(4), nullable=False)  # 'call' or 'put'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    instrument = relationship("Instrument", back_populates="options")
    price_data = relationship("OptionPriceData", back_populates="option")

class OptionPriceData(Base):
    __tablename__ = "option_price_data"

    id = Column(Integer, primary_key=True, index=True)
    option_id = Column(Integer, ForeignKey("options.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    bid = Column(Float, nullable=True)
    ask = Column(Float, nullable=True)
    last = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    open_interest = Column(Integer, nullable=True)
    implied_volatility = Column(Float, nullable=True)
    delta = Column(Float, nullable=True)
    gamma = Column(Float, nullable=True)
    theta = Column(Float, nullable=True)
    vega = Column(Float, nullable=True)
    
    # Relationships
    option = relationship("Option", back_populates="price_data")

class EarningsData(Base):
    __tablename__ = "earnings_data"

    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    earnings_date = Column(DateTime, nullable=False, index=True)
    fiscal_quarter = Column(String(10), nullable=False)  # e.g., "Q1 2023"
    eps_estimate = Column(Float, nullable=True)
    eps_actual = Column(Float, nullable=True)
    revenue_estimate = Column(Float, nullable=True)
    revenue_actual = Column(Float, nullable=True)
    surprise_percentage = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    instrument = relationship("Instrument", back_populates="earnings_data")

class FinancialMetric(Base):
    __tablename__ = "financial_metrics"

    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    metric_type = Column(String(50), nullable=False)  # e.g., "pe_ratio", "revenue", etc.
    value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    instrument = relationship("Instrument", back_populates="financial_metrics")

class AnalystRating(Base):
    __tablename__ = "analyst_ratings"

    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    analyst_firm = Column(String(100), nullable=False)
    rating_date = Column(DateTime, nullable=False, index=True)
    rating = Column(String(20), nullable=False)  # e.g., "Buy", "Sell", "Hold"
    price_target = Column(Float, nullable=True)
    previous_rating = Column(String(20), nullable=True)
    previous_price_target = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    instrument = relationship("Instrument", back_populates="analyst_ratings")

class StockPrice(Base):
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    vwap = Column(Float, nullable=True)  # Volume-weighted average price
    
    # Relationships
    instrument = relationship("Instrument")

class VolatilityData(Base):
    __tablename__ = "volatility_data"

    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    historical_volatility_10d = Column(Float, nullable=True)
    historical_volatility_20d = Column(Float, nullable=True)
    historical_volatility_30d = Column(Float, nullable=True)
    implied_volatility_avg = Column(Float, nullable=True)
    iv_percentile = Column(Float, nullable=True)  # Percentile of current IV vs historical
    iv_rank = Column(Float, nullable=True)  # Rank of current IV vs 52-week range
    
    # Relationships
    instrument = relationship("Instrument")

