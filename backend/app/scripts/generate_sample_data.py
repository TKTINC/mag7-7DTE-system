import os
import sys
import random
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.database import SessionLocal, engine, Base
from app.models.market_data import Instrument, StockPrice, OptionChain, OptionContract
from app.models.user import User, RiskProfile
from app.models.portfolio import Portfolio, Position, Trade
from app.models.signal import Signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Magnificent 7 stock data
MAG7_STOCKS = [
    {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology", "base_price": 175.25},
    {"symbol": "MSFT", "name": "Microsoft Corp.", "sector": "Technology", "base_price": 325.50},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology", "base_price": 142.75},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Cyclical", "base_price": 132.30},
    {"symbol": "NVDA", "name": "NVIDIA Corp.", "sector": "Technology", "base_price": 425.80},
    {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Cyclical", "base_price": 245.60},
    {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Technology", "base_price": 315.40},
]

def create_instruments(db):
    """Create Magnificent 7 stock instruments."""
    logger.info("Creating instruments...")
    
    instruments = []
    for stock in MAG7_STOCKS:
        instrument = Instrument(
            symbol=stock["symbol"],
            name=stock["name"],
            type="STOCK",
            sector=stock["sector"],
            is_active=True,
            description=f"{stock['name']} stock"
        )
        db.add(instrument)
        instruments.append(instrument)
    
    db.commit()
    logger.info(f"Created {len(instruments)} instruments")
    return instruments

def generate_stock_prices(db, instruments, days=90):
    """Generate historical stock prices for the instruments."""
    logger.info(f"Generating stock prices for {days} days...")
    
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    # Generate dates
    dates = [start_date + timedelta(days=i) for i in range(days)]
    
    # Filter out weekends
    dates = [date for date in dates if date.weekday() < 5]
    
    stock_prices = []
    for instrument in instruments:
        # Get base price from MAG7_STOCKS
        base_price = next((s["base_price"] for s in MAG7_STOCKS if s["symbol"] == instrument.symbol), 100.0)
        
        # Generate price series with random walk
        price = base_price
        volatility = random.uniform(0.01, 0.03)  # Daily volatility
        
        for date in dates:
            # Random daily return
            daily_return = np.random.normal(0.0005, volatility)  # Slight upward bias
            price = price * (1 + daily_return)
            
            # Generate OHLCV data
            open_price = price
            high_price = price * (1 + random.uniform(0, 0.015))
            low_price = price * (1 - random.uniform(0, 0.015))
            close_price = price
            volume = int(random.uniform(5000000, 50000000))
            
            stock_price = StockPrice(
                instrument_id=instrument.id,
                date=date,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume
            )
            db.add(stock_price)
            stock_prices.append(stock_price)
    
    db.commit()
    logger.info(f"Generated {len(stock_prices)} stock price records")
    return stock_prices

def generate_option_chains(db, instruments, days=30):
    """Generate option chain data for the instruments."""
    logger.info(f"Generating option chains for {days} days...")
    
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    # Generate dates
    dates = [start_date + timedelta(days=i) for i in range(days)]
    
    # Filter out weekends
    dates = [date for date in dates if date.weekday() < 5]
    
    option_chains = []
    option_contracts = []
    
    for instrument in instruments:
        for date in dates:
            # Get stock price for this date
            stock_price = db.query(StockPrice).filter(
                StockPrice.instrument_id == instrument.id,
                StockPrice.date == date
            ).first()
            
            if not stock_price:
                continue
            
            # Create option chain
            option_chain = OptionChain(
                instrument_id=instrument.id,
                date=date,
                expiration_date=date + timedelta(days=7),  # 7DTE
                is_complete=True
            )
            db.add(option_chain)
            db.flush()  # Get ID without committing
            option_chains.append(option_chain)
            
            # Generate option contracts
            stock_price_value = stock_price.close_price
            
            # Generate strikes around current price
            atm_strike = round(stock_price_value / 5) * 5  # Round to nearest $5
            strikes = [atm_strike + (i * 5) for i in range(-4, 5)]  # 9 strikes
            
            for strike in strikes:
                # Calculate call price
                call_itm = max(0, stock_price_value - strike)
                call_time_value = stock_price_value * 0.03 * (1 - abs(strike - stock_price_value) / stock_price_value)
                call_price = max(0.05, call_itm + call_time_value)
                
                # Calculate put price
                put_itm = max(0, strike - stock_price_value)
                put_time_value = stock_price_value * 0.03 * (1 - abs(strike - stock_price_value) / stock_price_value)
                put_price = max(0.05, put_itm + put_time_value)
                
                # Create call contract
                call_contract = OptionContract(
                    option_chain_id=option_chain.id,
                    contract_type="CALL",
                    strike_price=strike,
                    bid_price=call_price * 0.95,
                    ask_price=call_price * 1.05,
                    last_price=call_price,
                    volume=int(random.uniform(100, 5000)),
                    open_interest=int(random.uniform(500, 10000)),
                    implied_volatility=random.uniform(0.2, 0.6)
                )
                db.add(call_contract)
                option_contracts.append(call_contract)
                
                # Create put contract
                put_contract = OptionContract(
                    option_chain_id=option_chain.id,
                    contract_type="PUT",
                    strike_price=strike,
                    bid_price=put_price * 0.95,
                    ask_price=put_price * 1.05,
                    last_price=put_price,
                    volume=int(random.uniform(100, 5000)),
                    open_interest=int(random.uniform(500, 10000)),
                    implied_volatility=random.uniform(0.2, 0.6)
                )
                db.add(put_contract)
                option_contracts.append(put_contract)
    
    db.commit()
    logger.info(f"Generated {len(option_chains)} option chains with {len(option_contracts)} option contracts")
    return option_chains, option_contracts

def create_users(db):
    """Create sample users with risk profiles."""
    logger.info("Creating users...")
    
    users = []
    
    # Create admin user
    admin = User(
        username="admin",
        email="admin@example.com",
        is_active=True,
        is_superuser=True,
        hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "password"
    )
    db.add(admin)
    users.append(admin)
    
    # Create regular user
    user = User(
        username="user",
        email="user@example.com",
        is_active=True,
        is_superuser=False,
        hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "password"
    )
    db.add(user)
    users.append(user)
    
    db.commit()
    
    # Create risk profiles
    for user in users:
        risk_profile = RiskProfile(
            user_id=user.id,
            max_portfolio_risk=2.0,
            max_portfolio_exposure=50.0,
            max_stock_allocation=10.0,
            max_loss_per_trade=25.0,
            risk_reward_ratio=2.0
        )
        db.add(risk_profile)
    
    db.commit()
    logger.info(f"Created {len(users)} users with risk profiles")
    return users

def create_portfolios(db, users, instruments):
    """Create portfolios for users."""
    logger.info("Creating portfolios...")
    
    portfolios = []
    
    for user in users:
        portfolio = Portfolio(
            user_id=user.id,
            name=f"{user.username}'s Portfolio",
            description="Magnificent 7 stocks with 7DTE options",
            initial_capital=100000.0,
            cash_balance=50000.0,
            total_value=100000.0
        )
        db.add(portfolio)
        portfolios.append(portfolio)
    
    db.commit()
    
    # Create positions for the first user
    positions = []
    user_portfolio = portfolios[0]
    
    # Get latest date
    latest_date = db.query(StockPrice.date).order_by(StockPrice.date.desc()).first()[0]
    
    # Create 5 random positions
    for _ in range(5):
        instrument = random.choice(instruments)
        
        # Get latest stock price
        stock_price = db.query(StockPrice).filter(
            StockPrice.instrument_id == instrument.id,
            StockPrice.date == latest_date
        ).first()
        
        if not stock_price:
            continue
        
        # Get option chain
        option_chain = db.query(OptionChain).filter(
            OptionChain.instrument_id == instrument.id,
            OptionChain.date == latest_date
        ).first()
        
        if not option_chain:
            continue
        
        # Get ATM option contract
        atm_strike = round(stock_price.close_price / 5) * 5
        contract_type = random.choice(["CALL", "PUT"])
        
        option_contract = db.query(OptionContract).filter(
            OptionContract.option_chain_id == option_chain.id,
            OptionContract.contract_type == contract_type,
            OptionContract.strike_price == atm_strike
        ).first()
        
        if not option_contract:
            continue
        
        # Create position
        entry_date = latest_date - timedelta(days=random.randint(1, 5))
        contracts = random.randint(1, 5)
        entry_price = option_contract.last_price * 0.9  # Assume we got a better price
        current_price = option_contract.last_price
        
        position = Position(
            portfolio_id=user_portfolio.id,
            instrument_id=instrument.id,
            position_type=f"LONG_{contract_type}",
            entry_date=entry_date,
            expiration_date=option_chain.expiration_date,
            strike_price=atm_strike,
            contracts=contracts,
            entry_price=entry_price,
            current_price=current_price,
            cost=entry_price * contracts * 100,
            current_value=current_price * contracts * 100,
            pnl=(current_price - entry_price) * contracts * 100,
            pnl_percentage=((current_price - entry_price) / entry_price) * 100,
            status="ACTIVE"
        )
        db.add(position)
        positions.append(position)
    
    # Create trades for the first user
    trades = []
    
    for _ in range(20):
        instrument = random.choice(instruments)
        
        # Random dates in the past
        exit_date = latest_date - timedelta(days=random.randint(1, 30))
        entry_date = exit_date - timedelta(days=random.randint(1, 6))
        expiration_date = entry_date + timedelta(days=7)
        
        # Get stock price at entry
        stock_price = db.query(StockPrice).filter(
            StockPrice.instrument_id == instrument.id,
            StockPrice.date <= entry_date
        ).order_by(StockPrice.date.desc()).first()
        
        if not stock_price:
            continue
        
        # Random trade details
        contract_type = random.choice(["CALL", "PUT"])
        atm_strike = round(stock_price.close_price / 5) * 5
        contracts = random.randint(1, 5)
        
        # Random prices
        entry_price = random.uniform(1.0, 5.0)
        exit_price = entry_price * random.uniform(0.5, 1.5)
        
        # Calculate P&L
        cost = entry_price * contracts * 100
        proceeds = exit_price * contracts * 100
        pnl = proceeds - cost
        pnl_percentage = (pnl / cost) * 100
        
        trade = Trade(
            portfolio_id=user_portfolio.id,
            instrument_id=instrument.id,
            position_type=f"LONG_{contract_type}",
            entry_date=entry_date,
            exit_date=exit_date,
            expiration_date=expiration_date,
            strike_price=atm_strike,
            contracts=contracts,
            entry_price=entry_price,
            exit_price=exit_price,
            cost=cost,
            proceeds=proceeds,
            pnl=pnl,
            pnl_percentage=pnl_percentage,
            status="CLOSED",
            exit_reason="TARGET" if pnl > 0 else "STOP_LOSS"
        )
        db.add(trade)
        trades.append(trade)
    
    db.commit()
    logger.info(f"Created {len(portfolios)} portfolios with {len(positions)} positions and {len(trades)} trades")
    return portfolios, positions, trades

def generate_signals(db, instruments):
    """Generate trading signals for the instruments."""
    logger.info("Generating trading signals...")
    
    signals = []
    
    # Get latest date
    latest_date = db.query(StockPrice.date).order_by(StockPrice.date.desc()).first()[0]
    
    # Generate signals for each instrument
    for instrument in instruments:
        # Get latest stock price
        stock_price = db.query(StockPrice).filter(
            StockPrice.instrument_id == instrument.id,
            StockPrice.date == latest_date
        ).first()
        
        if not stock_price:
            continue
        
        # Get option chain
        option_chain = db.query(OptionChain).filter(
            OptionChain.instrument_id == instrument.id,
            OptionChain.date == latest_date
        ).first()
        
        if not option_chain:
            continue
        
        # Generate 2-3 signals per instrument
        for _ in range(random.randint(2, 3)):
            # Random signal details
            signal_type = random.choice(["LONG_CALL", "LONG_PUT"])
            
            # Get ATM option contract
            atm_strike = round(stock_price.close_price / 5) * 5
            strike_offset = random.choice([-10, -5, 0, 5, 10])
            strike_price = atm_strike + strike_offset
            
            contract_type = "CALL" if signal_type == "LONG_CALL" else "PUT"
            
            option_contract = db.query(OptionContract).filter(
                OptionContract.option_chain_id == option_chain.id,
                OptionContract.contract_type == contract_type,
                OptionContract.strike_price == strike_price
            ).first()
            
            if not option_contract:
                continue
            
            # Generate signal
            confidence = random.uniform(0.6, 0.95)
            
            # Generate factors
            factors = {
                "technical": {
                    "rsi": random.uniform(0, 100),
                    "macd": random.uniform(-2, 2),
                    "bollinger": random.uniform(-2, 2)
                },
                "fundamental": {
                    "pe_ratio": random.uniform(10, 40),
                    "growth_rate": random.uniform(-5, 20),
                    "analyst_rating": random.uniform(1, 5)
                },
                "volatility": {
                    "iv_percentile": random.uniform(0, 100),
                    "iv_skew": random.uniform(-2, 2),
                    "historical_vol": random.uniform(10, 60)
                }
            }
            
            signal = Signal(
                instrument_id=instrument.id,
                signal_date=latest_date,
                signal_type=signal_type,
                expiration_date=option_chain.expiration_date,
                strike_price=strike_price,
                option_price=option_contract.last_price,
                confidence=confidence,
                factors=factors,
                status="ACTIVE",
                source="ENSEMBLE"
            )
            db.add(signal)
            signals.append(signal)
    
    db.commit()
    logger.info(f"Generated {len(signals)} trading signals")
    return signals

def main():
    """Main function to generate sample data."""
    logger.info("Starting sample data generation...")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
        
        # Create instruments
        instruments = create_instruments(db)
        
        # Generate stock prices
        stock_prices = generate_stock_prices(db, instruments)
        
        # Generate option chains
        option_chains, option_contracts = generate_option_chains(db, instruments)
        
        # Create users
        users = create_users(db)
        
        # Create portfolios
        portfolios, positions, trades = create_portfolios(db, users, instruments)
        
        # Generate signals
        signals = generate_signals(db, instruments)
        
        logger.info("Sample data generation completed successfully!")
        
    except Exception as e:
        logger.error(f"Error generating sample data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()

