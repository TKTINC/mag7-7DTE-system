import os
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, List

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Mag7-7DTE-System"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://mag7user:mag7password@localhost:5432/mag7db")
    
    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # InfluxDB settings
    INFLUXDB_URL: str = os.getenv("INFLUXDB_URL", "http://localhost:8086")
    INFLUXDB_TOKEN: str = os.getenv("INFLUXDB_TOKEN", "mag7token")
    INFLUXDB_ORG: str = os.getenv("INFLUXDB_ORG", "mag7org")
    INFLUXDB_BUCKET: str = os.getenv("INFLUXDB_BUCKET", "market_data")
    
    # API keys
    POLYGON_API_KEY: str = os.getenv("POLYGON_API_KEY", "")
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "mag7secretkey")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]
    
    # Market data settings
    MAG7_SYMBOLS: List[str] = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"]
    ETF_SYMBOLS: List[str] = ["SPY", "QQQ", "IWM"]
    INDEX_SYMBOLS: List[str] = ["VIX"]
    
    # Trading settings
    DEFAULT_DTE: int = 7  # Default days to expiration
    TRADING_HOURS_START: str = "09:30"  # Eastern Time
    TRADING_HOURS_END: str = "16:00"  # Eastern Time
    
    # Signal generation settings
    SIGNAL_GENERATION_INTERVAL: int = 5  # minutes
    
    # Risk management settings
    MAX_POSITION_SIZE_PERCENT: float = 5.0  # Maximum position size as percentage of portfolio
    MAX_SECTOR_EXPOSURE_PERCENT: float = 30.0  # Maximum sector exposure as percentage of portfolio
    
    # Conversational AI settings
    AI_MODEL: str = "gpt-4"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 1000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

