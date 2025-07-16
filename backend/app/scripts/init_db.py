import os
import sys
from datetime import datetime, timedelta
import random

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.market_data import Base, Instrument, InstrumentType, Sector, MarketCapCategory
from app.config import settings

def init_db():
    """Initialize the database with required tables and seed data."""
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if we already have instruments
        existing_instruments = db.query(Instrument).count()
        if existing_instruments > 0:
            print(f"Database already contains {existing_instruments} instruments. Skipping seed data.")
            return
        
        # Seed Magnificent 7 stocks
        mag7_stocks = [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.",
                "type": InstrumentType.STOCK,
                "sector": Sector.TECHNOLOGY,
                "market_cap_category": MarketCapCategory.MEGA,
                "earnings_schedule": {
                    "next_date": (datetime.utcnow() + timedelta(days=random.randint(10, 60))).isoformat(),
                    "frequency": "quarterly"
                },
                "fundamental_data_enabled": True,
                "analyst_coverage_enabled": True
            },
            {
                "symbol": "MSFT",
                "name": "Microsoft Corporation",
                "description": "Microsoft Corporation develops, licenses, and supports software, services, devices, and solutions worldwide.",
                "type": InstrumentType.STOCK,
                "sector": Sector.TECHNOLOGY,
                "market_cap_category": MarketCapCategory.MEGA,
                "earnings_schedule": {
                    "next_date": (datetime.utcnow() + timedelta(days=random.randint(10, 60))).isoformat(),
                    "frequency": "quarterly"
                },
                "fundamental_data_enabled": True,
                "analyst_coverage_enabled": True
            },
            {
                "symbol": "GOOGL",
                "name": "Alphabet Inc.",
                "description": "Alphabet Inc. provides various products and platforms in the United States, Europe, the Middle East, Africa, the Asia-Pacific, Canada, and Latin America.",
                "type": InstrumentType.STOCK,
                "sector": Sector.COMMUNICATION_SERVICES,
                "market_cap_category": MarketCapCategory.MEGA,
                "earnings_schedule": {
                    "next_date": (datetime.utcnow() + timedelta(days=random.randint(10, 60))).isoformat(),
                    "frequency": "quarterly"
                },
                "fundamental_data_enabled": True,
                "analyst_coverage_enabled": True
            },
            {
                "symbol": "AMZN",
                "name": "Amazon.com, Inc.",
                "description": "Amazon.com, Inc. engages in the retail sale of consumer products and subscriptions through online and physical stores in North America and internationally.",
                "type": InstrumentType.STOCK,
                "sector": Sector.CONSUMER_DISCRETIONARY,
                "market_cap_category": MarketCapCategory.MEGA,
                "earnings_schedule": {
                    "next_date": (datetime.utcnow() + timedelta(days=random.randint(10, 60))).isoformat(),
                    "frequency": "quarterly"
                },
                "fundamental_data_enabled": True,
                "analyst_coverage_enabled": True
            },
            {
                "symbol": "NVDA",
                "name": "NVIDIA Corporation",
                "description": "NVIDIA Corporation provides graphics, and compute and networking solutions in the United States, Taiwan, China, and internationally.",
                "type": InstrumentType.STOCK,
                "sector": Sector.TECHNOLOGY,
                "market_cap_category": MarketCapCategory.MEGA,
                "earnings_schedule": {
                    "next_date": (datetime.utcnow() + timedelta(days=random.randint(10, 60))).isoformat(),
                    "frequency": "quarterly"
                },
                "fundamental_data_enabled": True,
                "analyst_coverage_enabled": True
            },
            {
                "symbol": "TSLA",
                "name": "Tesla, Inc.",
                "description": "Tesla, Inc. designs, develops, manufactures, leases, and sells electric vehicles, and energy generation and storage systems in the United States, China, and internationally.",
                "type": InstrumentType.STOCK,
                "sector": Sector.CONSUMER_DISCRETIONARY,
                "market_cap_category": MarketCapCategory.MEGA,
                "earnings_schedule": {
                    "next_date": (datetime.utcnow() + timedelta(days=random.randint(10, 60))).isoformat(),
                    "frequency": "quarterly"
                },
                "fundamental_data_enabled": True,
                "analyst_coverage_enabled": True
            },
            {
                "symbol": "META",
                "name": "Meta Platforms, Inc.",
                "description": "Meta Platforms, Inc. develops products that enable people to connect and share with friends and family through mobile devices, personal computers, virtual reality headsets, and wearables worldwide.",
                "type": InstrumentType.STOCK,
                "sector": Sector.COMMUNICATION_SERVICES,
                "market_cap_category": MarketCapCategory.MEGA,
                "earnings_schedule": {
                    "next_date": (datetime.utcnow() + timedelta(days=random.randint(10, 60))).isoformat(),
                    "frequency": "quarterly"
                },
                "fundamental_data_enabled": True,
                "analyst_coverage_enabled": True
            }
        ]
        
        # Add ETFs for market comparison
        etfs = [
            {
                "symbol": "SPY",
                "name": "SPDR S&P 500 ETF Trust",
                "description": "The SPDR S&P 500 ETF Trust seeks to provide investment results that correspond generally to the price and yield performance of the S&P 500 Index.",
                "type": InstrumentType.ETF,
                "sector": None,
                "market_cap_category": None,
                "earnings_schedule": None,
                "fundamental_data_enabled": False,
                "analyst_coverage_enabled": False
            },
            {
                "symbol": "QQQ",
                "name": "Invesco QQQ Trust",
                "description": "The Invesco QQQ Trust is an exchange-traded fund based on the Nasdaq-100 Index, which includes 100 of the largest domestic and international non-financial companies listed on the Nasdaq Stock Market.",
                "type": InstrumentType.ETF,
                "sector": None,
                "market_cap_category": None,
                "earnings_schedule": None,
                "fundamental_data_enabled": False,
                "analyst_coverage_enabled": False
            },
            {
                "symbol": "IWM",
                "name": "iShares Russell 2000 ETF",
                "description": "The iShares Russell 2000 ETF seeks to track the investment results of an index composed of small-capitalization U.S. equities.",
                "type": InstrumentType.ETF,
                "sector": None,
                "market_cap_category": None,
                "earnings_schedule": None,
                "fundamental_data_enabled": False,
                "analyst_coverage_enabled": False
            }
        ]
        
        # Add VIX for volatility reference
        vix = {
            "symbol": "VIX",
            "name": "CBOE Volatility Index",
            "description": "The CBOE Volatility Index, known by its ticker symbol VIX, is a popular measure of the stock market's expectation of volatility implied by S&P 500 index options.",
            "type": InstrumentType.INDEX,
            "sector": None,
            "market_cap_category": None,
            "earnings_schedule": None,
            "fundamental_data_enabled": False,
            "analyst_coverage_enabled": False
        }
        
        # Insert all instruments
        all_instruments = mag7_stocks + etfs + [vix]
        for instrument_data in all_instruments:
            instrument = Instrument(**instrument_data)
            db.add(instrument)
        
        db.commit()
        print(f"Successfully initialized database with {len(all_instruments)} instruments.")
        
    except Exception as e:
        db.rollback()
        print(f"Error initializing database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialization complete.")

