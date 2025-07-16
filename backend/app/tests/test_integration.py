import os
import sys
import unittest
import json
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.market_data import Instrument, StockPrice, OptionChain, OptionContract
from app.models.user import User, RiskProfile
from app.models.portfolio import Portfolio, Position, Trade
from app.models.signal import Signal

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create the database tables
        Base.metadata.create_all(bind=engine)
        
        # Create a session
        cls.db = TestingSessionLocal()
        
        # Create test data
        cls.create_test_data()
    
    @classmethod
    def tearDownClass(cls):
        # Close the session
        cls.db.close()
        
        # Drop the database tables
        Base.metadata.drop_all(bind=engine)
    
    @classmethod
    def create_test_data(cls):
        """Create test data for integration tests."""
        # Create instruments
        instruments = []
        for symbol in ["AAPL", "MSFT", "GOOGL"]:
            instrument = Instrument(
                symbol=symbol,
                name=f"{symbol} Inc.",
                type="STOCK",
                sector="Technology",
                is_active=True,
                description=f"{symbol} stock"
            )
            cls.db.add(instrument)
            instruments.append(instrument)
        
        cls.db.commit()
        
        # Create stock prices
        today = datetime.utcnow().date()
        for instrument in instruments:
            for i in range(30):
                date = today - timedelta(days=i)
                price = 100.0 + (i % 10)
                
                stock_price = StockPrice(
                    instrument_id=instrument.id,
                    date=date,
                    open_price=price,
                    high_price=price * 1.02,
                    low_price=price * 0.98,
                    close_price=price,
                    volume=1000000
                )
                cls.db.add(stock_price)
        
        cls.db.commit()
        
        # Create option chains
        for instrument in instruments:
            option_chain = OptionChain(
                instrument_id=instrument.id,
                date=today,
                expiration_date=today + timedelta(days=7),
                is_complete=True
            )
            cls.db.add(option_chain)
            cls.db.flush()
            
            # Create option contracts
            for strike in [90, 95, 100, 105, 110]:
                for contract_type in ["CALL", "PUT"]:
                    option_contract = OptionContract(
                        option_chain_id=option_chain.id,
                        contract_type=contract_type,
                        strike_price=strike,
                        bid_price=2.0,
                        ask_price=2.2,
                        last_price=2.1,
                        volume=1000,
                        open_interest=5000,
                        implied_volatility=0.3
                    )
                    cls.db.add(option_contract)
        
        cls.db.commit()
        
        # Create users
        user = User(
            username="testuser",
            email="test@example.com",
            is_active=True,
            is_superuser=False,
            hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # "password"
        )
        cls.db.add(user)
        cls.db.commit()
        
        # Create risk profile
        risk_profile = RiskProfile(
            user_id=user.id,
            max_portfolio_risk=2.0,
            max_portfolio_exposure=50.0,
            max_stock_allocation=10.0,
            max_loss_per_trade=25.0,
            risk_reward_ratio=2.0
        )
        cls.db.add(risk_profile)
        cls.db.commit()
        
        # Create portfolio
        portfolio = Portfolio(
            user_id=user.id,
            name="Test Portfolio",
            description="Test portfolio for integration tests",
            initial_capital=100000.0,
            cash_balance=50000.0,
            total_value=100000.0
        )
        cls.db.add(portfolio)
        cls.db.commit()
        
        # Create positions
        for i, instrument in enumerate(instruments[:2]):
            position = Position(
                portfolio_id=portfolio.id,
                instrument_id=instrument.id,
                position_type="LONG_CALL" if i % 2 == 0 else "LONG_PUT",
                entry_date=today - timedelta(days=3),
                expiration_date=today + timedelta(days=4),
                strike_price=100,
                contracts=2,
                entry_price=2.0,
                current_price=2.5,
                cost=400.0,
                current_value=500.0,
                pnl=100.0,
                pnl_percentage=25.0,
                status="ACTIVE"
            )
            cls.db.add(position)
        
        cls.db.commit()
        
        # Create trades
        for i, instrument in enumerate(instruments):
            trade = Trade(
                portfolio_id=portfolio.id,
                instrument_id=instrument.id,
                position_type="LONG_CALL" if i % 2 == 0 else "LONG_PUT",
                entry_date=today - timedelta(days=10),
                exit_date=today - timedelta(days=5),
                expiration_date=today - timedelta(days=3),
                strike_price=100,
                contracts=2,
                entry_price=2.0,
                exit_price=2.5 if i % 2 == 0 else 1.5,
                cost=400.0,
                proceeds=500.0 if i % 2 == 0 else 300.0,
                pnl=100.0 if i % 2 == 0 else -100.0,
                pnl_percentage=25.0 if i % 2 == 0 else -25.0,
                status="CLOSED",
                exit_reason="TARGET" if i % 2 == 0 else "STOP_LOSS"
            )
            cls.db.add(trade)
        
        cls.db.commit()
        
        # Create signals
        for i, instrument in enumerate(instruments):
            signal = Signal(
                instrument_id=instrument.id,
                signal_date=today,
                signal_type="LONG_CALL" if i % 2 == 0 else "LONG_PUT",
                expiration_date=today + timedelta(days=7),
                strike_price=100,
                option_price=2.1,
                confidence=0.8,
                factors={
                    "technical": {"rsi": 65, "macd": 0.5},
                    "fundamental": {"pe_ratio": 25},
                    "volatility": {"iv_percentile": 60}
                },
                status="ACTIVE",
                source="ENSEMBLE"
            )
            cls.db.add(signal)
        
        cls.db.commit()
    
    def test_market_data_endpoints(self):
        """Test market data API endpoints."""
        # Test get instruments
        response = client.get("/api/v1/market-data/instruments")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["symbol"], "AAPL")
        
        # Test get stock prices
        instrument_id = data[0]["id"]
        response = client.get(f"/api/v1/market-data/prices/{instrument_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data) > 0)
        
        # Test get option chains
        response = client.get(f"/api/v1/market-data/option-chains/{instrument_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data) > 0)
        
        # Test get option contracts
        chain_id = data[0]["id"]
        response = client.get(f"/api/v1/market-data/option-contracts/{chain_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data) > 0)
    
    def test_signal_endpoints(self):
        """Test signal API endpoints."""
        # Test get signals
        response = client.get("/api/v1/signals")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 3)
        
        # Test get signal by ID
        signal_id = data[0]["id"]
        response = client.get(f"/api/v1/signals/{signal_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], signal_id)
        
        # Test filter signals by instrument
        instrument_id = data[0]["instrument_id"]
        response = client.get(f"/api/v1/signals?instrument_id={instrument_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data) > 0)
        self.assertEqual(data[0]["instrument_id"], instrument_id)
    
    def test_portfolio_endpoints(self):
        """Test portfolio API endpoints."""
        # Test get portfolios
        response = client.get("/api/v1/portfolios")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        
        # Test get portfolio by ID
        portfolio_id = data[0]["id"]
        response = client.get(f"/api/v1/portfolios/{portfolio_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], portfolio_id)
        
        # Test get positions
        response = client.get(f"/api/v1/portfolios/{portfolio_id}/positions")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        
        # Test get trades
        response = client.get(f"/api/v1/portfolios/{portfolio_id}/trades")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 3)
    
    def test_risk_management_endpoints(self):
        """Test risk management API endpoints."""
        # Get user and portfolio IDs
        response = client.get("/api/v1/portfolios")
        portfolio_data = response.json()[0]
        user_id = portfolio_data["user_id"]
        portfolio_id = portfolio_data["id"]
        
        # Get instrument ID
        response = client.get("/api/v1/market-data/instruments")
        instrument_id = response.json()[0]["id"]
        
        # Test position size calculation
        position_size_data = {
            "user_id": user_id,
            "instrument_id": instrument_id,
            "signal_confidence": 0.8,
            "option_price": 2.1
        }
        response = client.post("/api/v1/risk-management/position-size", json=position_size_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue("contracts" in data)
        self.assertTrue("max_capital" in data)
        
        # Test portfolio exposure
        response = client.get(f"/api/v1/risk-management/portfolio-exposure/{user_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue("total_exposure" in data)
        self.assertTrue("exposure_percentage" in data)
        
        # Get position ID
        response = client.get(f"/api/v1/portfolios/{portfolio_id}/positions")
        position_id = response.json()[0]["id"]
        
        # Test stop-loss/take-profit calculation
        sl_tp_data = {
            "position_id": position_id,
            "risk_reward_ratio": 2.0
        }
        response = client.post("/api/v1/risk-management/stop-loss-take-profit", json=sl_tp_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue("stop_loss_price" in data)
        self.assertTrue("take_profit_price" in data)
        
        # Test stop-loss/take-profit check
        response = client.get(f"/api/v1/risk-management/stop-loss-take-profit/check/{position_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue("stop_loss_hit" in data)
        self.assertTrue("take_profit_hit" in data)
        
        # Test portfolio metrics
        response = client.get(f"/api/v1/risk-management/portfolio-metrics/{user_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue("metrics" in data)
        
        # Test risk profile recommendations
        response = client.get(f"/api/v1/risk-management/risk-profile-recommendations/{user_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue("recommendations" in data)
        
        # Test correlation matrix
        response = client.get("/api/v1/risk-management/correlation-matrix?lookback_days=30")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(isinstance(data, dict))

if __name__ == "__main__":
    unittest.main()

