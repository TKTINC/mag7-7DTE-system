# Import all schemas to make them available when importing the schemas package
from app.schemas.market_data import (
    InstrumentBase, InstrumentCreate, InstrumentResponse,
    StockPriceBase, StockPriceCreate, StockPriceResponse,
    OptionBase, OptionCreate, OptionResponse,
    OptionPriceBase, OptionPriceCreate, OptionPriceResponse,
    EarningsDataBase, EarningsDataCreate, EarningsDataResponse,
    FinancialMetricBase, FinancialMetricCreate, FinancialMetricResponse,
    AnalystRatingBase, AnalystRatingCreate, AnalystRatingResponse,
    RealTimeQuote
)

# Define all schemas for easy access
__all__ = [
    # Market data schemas
    'InstrumentBase', 'InstrumentCreate', 'InstrumentResponse',
    'StockPriceBase', 'StockPriceCreate', 'StockPriceResponse',
    'OptionBase', 'OptionCreate', 'OptionResponse',
    'OptionPriceBase', 'OptionPriceCreate', 'OptionPriceResponse',
    'EarningsDataBase', 'EarningsDataCreate', 'EarningsDataResponse',
    'FinancialMetricBase', 'FinancialMetricCreate', 'FinancialMetricResponse',
    'AnalystRatingBase', 'AnalystRatingCreate', 'AnalystRatingResponse',
    'RealTimeQuote'
]

