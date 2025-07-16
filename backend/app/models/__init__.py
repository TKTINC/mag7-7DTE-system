# Import all models to make them available when importing the models package
from app.models.market_data import (
    Base, Instrument, InstrumentType, Sector, MarketCapCategory,
    Option, OptionPriceData, EarningsData, FinancialMetric, AnalystRating,
    StockPrice, VolatilityData
)

from app.models.signal import (
    Signal, SignalType, SignalSource, SignalStatus,
    SignalFactor, Trade, Strategy
)

from app.models.portfolio import (
    Account, AccountType, Position, PositionStatus,
    PositionTrade, PortfolioSnapshot, RiskProfile, PerformanceMetric
)

from app.models.user import (
    User, UserRole, ApiKey, Notification, ActivityLog, UserPreference
)

# Define all models for easy access
__all__ = [
    # Base
    'Base',
    
    # Market data models
    'Instrument', 'InstrumentType', 'Sector', 'MarketCapCategory',
    'Option', 'OptionPriceData', 'EarningsData', 'FinancialMetric', 'AnalystRating',
    'StockPrice', 'VolatilityData',
    
    # Signal models
    'Signal', 'SignalType', 'SignalSource', 'SignalStatus',
    'SignalFactor', 'Trade', 'Strategy',
    
    # Portfolio models
    'Account', 'AccountType', 'Position', 'PositionStatus',
    'PositionTrade', 'PortfolioSnapshot', 'RiskProfile', 'PerformanceMetric',
    
    # User models
    'User', 'UserRole', 'ApiKey', 'Notification', 'ActivityLog', 'UserPreference'
]

