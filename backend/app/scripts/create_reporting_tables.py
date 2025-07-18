import os
import sys
from datetime import datetime
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import engine, Base, SessionLocal
from app.models.reporting import Report, ReportSchedule, SignalFactor, MarketCondition, FundamentalData
from app.models.signal import Signal
from app.models.portfolio import Portfolio
from app.models.user import User
from app.models.market_data import Instrument

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    """Create reporting tables in the database."""
    logger.info("Creating reporting tables...")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    logger.info("Reporting tables created successfully.")

def add_relationships():
    """Add relationships to existing models."""
    logger.info("Adding relationships to existing models...")
    
    db = SessionLocal()
    try:
        # Add signal_factors relationship to Signal model
        if not hasattr(Signal, 'signal_factors'):
            Signal.signal_factors = relationship("SignalFactor", back_populates="signal")
            logger.info("Added signal_factors relationship to Signal model.")
        
        # Add reports relationship to Portfolio model
        if not hasattr(Portfolio, 'reports'):
            Portfolio.reports = relationship("Report", back_populates="portfolio")
            logger.info("Added reports relationship to Portfolio model.")
        
        # Add report_schedules relationship to User model
        if not hasattr(User, 'report_schedules'):
            User.report_schedules = relationship("ReportSchedule", back_populates="user")
            logger.info("Added report_schedules relationship to User model.")
        
        # Add fundamental_data relationship to Instrument model
        if not hasattr(Instrument, 'fundamental_data'):
            Instrument.fundamental_data = relationship("FundamentalData", back_populates="instrument")
            logger.info("Added fundamental_data relationship to Instrument model.")
        
        db.commit()
    except Exception as e:
        logger.error(f"Error adding relationships: {e}")
        db.rollback()
    finally:
        db.close()

def create_sample_data():
    """Create sample data for testing."""
    logger.info("Creating sample data...")
    
    db = SessionLocal()
    try:
        # Create sample market condition
        today = datetime.utcnow().date()
        market_condition = MarketCondition(
            date=today,
            vix_open=15.5,
            vix_high=16.2,
            vix_low=15.1,
            vix_close=15.8,
            spy_open=450.2,
            spy_high=452.1,
            spy_low=449.5,
            spy_close=451.3,
            spy_volume=75000000,
            condition_type="normal",
            is_unusual=False,
            notes="Normal trading day with low volatility."
        )
        db.add(market_condition)
        
        # Create sample fundamental data for Mag7 stocks
        mag7_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"]
        
        for symbol in mag7_symbols:
            # Get or create instrument
            instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
            if not instrument:
                instrument = Instrument(
                    symbol=symbol,
                    name=f"{symbol} Inc.",
                    type="stock",
                    exchange="NASDAQ",
                    is_active=True
                )
                db.add(instrument)
                db.flush()
            
            # Create fundamental data
            fundamental_data = FundamentalData(
                instrument_id=instrument.id,
                date=today,
                next_earnings_date=today + timedelta(days=30),
                earnings_time="AMC",
                estimated_eps=2.5,
                previous_eps=2.3,
                pe_ratio=25.5,
                forward_pe=22.8,
                peg_ratio=1.2,
                price_to_sales=8.5,
                price_to_book=12.3,
                revenue_growth_yoy=15.2,
                eps_growth_yoy=18.5,
                analyst_rating="Buy",
                price_target=200.0,
                price_target_high=250.0,
                price_target_low=180.0
            )
            db.add(fundamental_data)
        
        # Get first portfolio
        portfolio = db.query(Portfolio).first()
        if portfolio:
            # Create sample report
            report = Report(
                portfolio_id=portfolio.id,
                report_type="DAILY",
                start_date=today,
                end_date=today,
                title=f"Daily Trading Report - {today.strftime('%Y-%m-%d')}",
                description=f"Comprehensive trading report for {today.strftime('%Y-%m-%d')}",
                report_data={
                    "report_date": today.strftime("%Y-%m-%d"),
                    "generation_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "daily_summary": {
                        "portfolio_value": 100000.0,
                        "daily_pnl": 1500.0,
                        "daily_pnl_pct": 1.5,
                        "total_trades": 5,
                        "entry_trades": 3,
                        "exit_trades": 2,
                        "signals_generated": 8,
                        "signals_executed": 3,
                        "market_context": {
                            "spy_change_pct": 0.24,
                            "vix_level": 15.8,
                            "vix_change_pct": 1.94,
                            "market_condition": "normal"
                        },
                        "fundamental_context": {
                            "mag7_data": {
                                "AAPL": {
                                    "pe_ratio": 25.5,
                                    "price_target": 200.0,
                                    "analyst_rating": "Buy",
                                    "next_earnings_date": (today + timedelta(days=30)).strftime("%Y-%m-%d")
                                },
                                # Other stocks...
                            },
                            "earnings_this_week": []
                        }
                    }
                }
            )
            db.add(report)
        
        # Get first user
        user = db.query(User).first()
        if user:
            # Create sample report schedule
            report_schedule = ReportSchedule(
                user_id=user.id,
                report_type="DAILY",
                is_active=True,
                time_of_day="17:00",
                days_of_week=[0, 1, 2, 3, 4],  # Monday to Friday
                email_delivery=True,
                notification_delivery=True
            )
            db.add(report_schedule)
        
        # Get first signal
        signal = db.query(Signal).first()
        if signal:
            # Create sample signal factors
            signal_factors = [
                SignalFactor(
                    signal_id=signal.id,
                    factor_name="RSI",
                    factor_value=28.5,
                    factor_weight=0.2,
                    factor_category="technical",
                    factor_description="Relative Strength Index indicates oversold condition."
                ),
                SignalFactor(
                    signal_id=signal.id,
                    factor_name="MACD",
                    factor_value=0.15,
                    factor_weight=0.15,
                    factor_category="technical",
                    factor_description="Moving Average Convergence Divergence shows bullish crossover."
                ),
                SignalFactor(
                    signal_id=signal.id,
                    factor_name="Bollinger Bands",
                    factor_value=-1.8,
                    factor_weight=0.1,
                    factor_category="technical",
                    factor_description="Price below lower Bollinger Band indicates potential reversal."
                ),
                SignalFactor(
                    signal_id=signal.id,
                    factor_name="PE Ratio",
                    factor_value=0.8,
                    factor_weight=0.15,
                    factor_category="fundamental",
                    factor_description="PE ratio below sector average indicates potential value."
                ),
                SignalFactor(
                    signal_id=signal.id,
                    factor_name="Analyst Rating",
                    factor_value=0.7,
                    factor_weight=0.1,
                    factor_category="fundamental",
                    factor_description="Recent analyst upgrades indicate positive sentiment."
                ),
                SignalFactor(
                    signal_id=signal.id,
                    factor_name="Earnings Surprise",
                    factor_value=0.9,
                    factor_weight=0.15,
                    factor_category="fundamental",
                    factor_description="Recent earnings beat expectations by 15%."
                ),
                SignalFactor(
                    signal_id=signal.id,
                    factor_name="News Sentiment",
                    factor_value=0.65,
                    factor_weight=0.1,
                    factor_category="sentiment",
                    factor_description="Recent news articles show positive sentiment."
                ),
                SignalFactor(
                    signal_id=signal.id,
                    factor_name="Social Media Sentiment",
                    factor_value=0.55,
                    factor_weight=0.05,
                    factor_category="sentiment",
                    factor_description="Social media sentiment is moderately positive."
                )
            ]
            for factor in signal_factors:
                db.add(factor)
        
        db.commit()
        logger.info("Sample data created successfully.")
    except Exception as e:
        logger.error(f"Error creating sample data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_tables()
    add_relationships()
    
    # Create sample data if requested
    if len(sys.argv) > 1 and sys.argv[1] == "--with-sample-data":
        create_sample_data()

