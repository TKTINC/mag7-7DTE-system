from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class InstrumentType(str, Enum):
    ETF = "etf"
    STOCK = "stock"
    INDEX = "index"

class Sector(str, Enum):
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

class MarketCapCategory(str, Enum):
    MEGA = "mega"
    LARGE = "large"
    MID = "mid"
    SMALL = "small"
    MICRO = "micro"

class InstrumentBase(BaseModel):
    symbol: str
    name: str
    description: Optional[str] = None
    type: InstrumentType
    sector: Optional[Sector] = None
    market_cap_category: Optional[MarketCapCategory] = None
    is_active: bool = True

class InstrumentCreate(InstrumentBase):
    earnings_schedule: Optional[Dict[str, Any]] = None
    fundamental_data_enabled: bool = False
    analyst_coverage_enabled: bool = False

class InstrumentResponse(InstrumentBase):
    id: int
    earnings_schedule: Optional[Dict[str, Any]] = None
    fundamental_data_enabled: bool = False
    analyst_coverage_enabled: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class StockPriceBase(BaseModel):
    timestamp: datetime
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    vwap: Optional[float] = None

class StockPriceCreate(StockPriceBase):
    instrument_id: int

class StockPriceResponse(StockPriceBase):
    id: int
    instrument_id: int

    class Config:
        orm_mode = True

class OptionBase(BaseModel):
    symbol: str
    expiration_date: datetime
    strike_price: float
    option_type: str
    is_active: bool = True

class OptionCreate(OptionBase):
    instrument_id: int

class OptionResponse(OptionBase):
    id: int
    instrument_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class OptionPriceBase(BaseModel):
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None

class OptionPriceCreate(OptionPriceBase):
    option_id: int

class OptionPriceResponse(OptionPriceBase):
    id: int
    option_id: int

    class Config:
        orm_mode = True

class EarningsDataBase(BaseModel):
    earnings_date: datetime
    fiscal_quarter: str
    eps_estimate: Optional[float] = None
    eps_actual: Optional[float] = None
    revenue_estimate: Optional[float] = None
    revenue_actual: Optional[float] = None
    surprise_percentage: Optional[float] = None

class EarningsDataCreate(EarningsDataBase):
    instrument_id: int

class EarningsDataResponse(EarningsDataBase):
    id: int
    instrument_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class FinancialMetricBase(BaseModel):
    date: datetime
    metric_type: str
    value: float

class FinancialMetricCreate(FinancialMetricBase):
    instrument_id: int

class FinancialMetricResponse(FinancialMetricBase):
    id: int
    instrument_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class AnalystRatingBase(BaseModel):
    analyst_firm: str
    rating_date: datetime
    rating: str
    price_target: Optional[float] = None
    previous_rating: Optional[str] = None
    previous_price_target: Optional[float] = None

class AnalystRatingCreate(AnalystRatingBase):
    instrument_id: int

class AnalystRatingResponse(AnalystRatingBase):
    id: int
    instrument_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class RealTimeQuote(BaseModel):
    symbol: str
    last_price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None
    timestamp: datetime
    change: Optional[float] = None
    change_percent: Optional[float] = None

