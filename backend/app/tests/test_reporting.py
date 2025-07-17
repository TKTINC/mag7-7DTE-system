import unittest
import asyncio
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models.reporting import Report, ReportType, ReportSchedule, FundamentalData
from app.services.sevendte_reporting_service import SevenDTEReportingService
from app.services.email_service import EmailService
from app.services.scheduler_service import SchedulerService

# Create test client
client = TestClient(app)

# Mock database session
mock_db = MagicMock(spec=Session)

# Override get_db dependency
def override_get_db():
    return mock_db

app.dependency_overrides[get_db] = override_get_db

class TestReporting(unittest.TestCase):
    """Test cases for reporting system."""
    
    def setUp(self):
        """Set up test environment."""
        # Reset mock
        mock_db.reset_mock()
        
        # Create mock report
        self.mock_report = MagicMock()
        self.mock_report.id = 1
        self.mock_report.portfolio_id = 1
        self.mock_report.report_type = ReportType.DAILY
        self.mock_report.start_date = date.today()
        self.mock_report.end_date = date.today()
        self.mock_report.title = "Daily Report"
        self.mock_report.description = "Daily trading report"
        self.mock_report.report_data = {
            "daily_summary": {
                "portfolio_value": 100000,
                "daily_pnl": 1000,
                "daily_pnl_pct": 1.0,
                "signals_generated": 10,
                "signals_executed": 5,
                "total_trades": 8,
                "market_context": {
                    "market_condition": "Normal"
                },
                "fundamental_context": {
                    "mag7_data": {
                        "AAPL": {
                            "pe_ratio": 25.5,
                            "price_target": 200.0,
                            "analyst_rating": "Buy",
                            "next_earnings_date": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
                        }
                    },
                    "earnings_this_week": [
                        {
                            "symbol": "MSFT",
                            "date": (date.today() + timedelta(days=2)).strftime("%Y-%m-%d"),
                            "time": "AMC",
                            "estimated_eps": 2.5,
                            "previous_eps": 2.3
                        }
                    ]
                }
            },
            "next_day_outlook": {
                "market_outlook": "Neutral",
                "expected_volatility": "Normal"
            }
        }
        self.mock_report.pdf_path = "/path/to/report.pdf"
        self.mock_report.created_at = datetime.utcnow()
    
    def test_get_daily_report(self):
        """Test get daily report endpoint."""
        # Mock query
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_report
        
        # Make request
        response = client.get("/reporting/daily/2023-01-01")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], 1)
        self.assertEqual(response.json()["portfolio_id"], 1)
        self.assertEqual(response.json()["report_type"], "DAILY")
    
    def test_list_reports(self):
        """Test list reports endpoint."""
        # Mock query
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [self.mock_report]
        
        # Make request
        response = client.get("/reporting/list")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["id"], 1)
    
    def test_create_report_schedule(self):
        """Test create report schedule endpoint."""
        # Mock add, commit, refresh
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        
        # Create mock schedule
        mock_schedule = MagicMock()
        mock_schedule.id = 1
        mock_schedule.user_id = 1
        mock_schedule.report_type = ReportType.DAILY
        mock_schedule.is_active = True
        mock_schedule.time_of_day = "18:00"
        mock_schedule.days_of_week = [0, 1, 2, 3, 4]
        mock_schedule.email_delivery = True
        mock_schedule.notification_delivery = False
        mock_schedule.created_at = datetime.utcnow()
        
        # Set mock_db.refresh to update the mock_schedule
        def mock_refresh(obj):
            obj.id = 1
            obj.created_at = datetime.utcnow()
        
        mock_db.refresh.side_effect = mock_refresh
        
        # Make request
        response = client.post(
            "/reporting/schedule",
            json={
                "user_id": 1,
                "report_type": "DAILY",
                "is_active": True,
                "time_of_day": "18:00",
                "days_of_week": [0, 1, 2, 3, 4],
                "email_delivery": True,
                "notification_delivery": False
            }
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], 1)
        self.assertEqual(response.json()["report_type"], "DAILY")
        
        # Check mock calls
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    def test_get_fundamental_data(self):
        """Test get fundamental data endpoint."""
        # Create mock instrument
        mock_instrument = MagicMock()
        mock_instrument.id = 1
        mock_instrument.symbol = "AAPL"
        
        # Create mock fundamental data
        mock_fundamental_data = MagicMock()
        mock_fundamental_data.instrument_id = 1
        mock_fundamental_data.date = date.today()
        mock_fundamental_data.next_earnings_date = date.today() + timedelta(days=30)
        mock_fundamental_data.earnings_time = "AMC"
        mock_fundamental_data.estimated_eps = 2.5
        mock_fundamental_data.previous_eps = 2.3
        mock_fundamental_data.pe_ratio = 25.5
        mock_fundamental_data.forward_pe = 24.0
        mock_fundamental_data.peg_ratio = 1.5
        mock_fundamental_data.price_to_sales = 5.0
        mock_fundamental_data.price_to_book = 10.0
        mock_fundamental_data.revenue_growth_yoy = 15.0
        mock_fundamental_data.eps_growth_yoy = 10.0
        mock_fundamental_data.analyst_rating = "Buy"
        mock_fundamental_data.price_target = 200.0
        mock_fundamental_data.price_target_high = 250.0
        mock_fundamental_data.price_target_low = 180.0
        
        # Mock queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_instrument, mock_fundamental_data]
        
        # Make request
        response = client.get("/reporting/fundamental/AAPL")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["symbol"], "AAPL")
        self.assertEqual(response.json()["pe_ratio"], 25.5)
        self.assertEqual(response.json()["analyst_rating"], "Buy")
    
    def test_get_correlation_matrix(self):
        """Test get correlation matrix endpoint."""
        # Mock market data
        mock_market_data = MagicMock()
        mock_market_data.close = 100.0
        
        # Mock query
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_market_data]
        
        # Make request
        response = client.get("/reporting/correlation-matrix")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["symbols"]), 7)  # Magnificent 7 stocks
        self.assertEqual(len(response.json()["data"]), 7)  # 7x7 correlation matrix

class TestSevenDTEReportingService(unittest.TestCase):
    """Test cases for SevenDTE reporting service."""
    
    def setUp(self):
        """Set up test environment."""
        # Reset mock
        mock_db.reset_mock()
        
        # Create reporting service
        self.reporting_service = SevenDTEReportingService(mock_db)
    
    @patch.object(SevenDTEReportingService, '_generate_report_data')
    @patch.object(SevenDTEReportingService, '_generate_pdf')
    def test_generate_daily_report(self, mock_generate_pdf, mock_generate_report_data):
        """Test generate daily report."""
        # Mock report data
        mock_report_data = {
            "daily_summary": {
                "portfolio_value": 100000,
                "daily_pnl": 1000,
                "daily_pnl_pct": 1.0,
                "signals_generated": 10,
                "signals_executed": 5,
                "total_trades": 8,
                "market_context": {
                    "market_condition": "Normal"
                },
                "fundamental_context": {
                    "mag7_data": {
                        "AAPL": {
                            "pe_ratio": 25.5,
                            "price_target": 200.0,
                            "analyst_rating": "Buy",
                            "next_earnings_date": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
                        }
                    }
                }
            },
            "next_day_outlook": {
                "market_outlook": "Neutral",
                "expected_volatility": "Normal"
            }
        }
        
        # Mock PDF path
        mock_pdf_path = "/path/to/report.pdf"
        
        # Set mock return values
        mock_generate_report_data.return_value = mock_report_data
        mock_generate_pdf.return_value = mock_pdf_path
        
        # Mock query
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Mock add, commit, refresh
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        
        # Create mock report
        mock_report = MagicMock()
        mock_report.id = 1
        
        # Set mock_db.refresh to update the mock_report
        def mock_refresh(obj):
            obj.id = 1
        
        mock_db.refresh.side_effect = mock_refresh
        
        # Call method
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            self.reporting_service.generate_daily_report(date.today(), 1)
        )
        
        # Check result
        self.assertEqual(result, mock_report_data)
        
        # Check mock calls
        mock_generate_report_data.assert_called_once()
        mock_generate_pdf.assert_called_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @patch.object(SevenDTEReportingService, '_generate_daily_summary')
    @patch.object(SevenDTEReportingService, '_generate_signal_analysis')
    @patch.object(SevenDTEReportingService, '_generate_trade_execution')
    @patch.object(SevenDTEReportingService, '_generate_position_management')
    @patch.object(SevenDTEReportingService, '_generate_risk_analysis')
    @patch.object(SevenDTEReportingService, '_generate_system_performance')
    @patch.object(SevenDTEReportingService, '_generate_next_day_outlook')
    def test_generate_report_data(
        self,
        mock_generate_next_day_outlook,
        mock_generate_system_performance,
        mock_generate_risk_analysis,
        mock_generate_position_management,
        mock_generate_trade_execution,
        mock_generate_signal_analysis,
        mock_generate_daily_summary
    ):
        """Test generate report data."""
        # Mock section data
        mock_daily_summary = {"portfolio_value": 100000}
        mock_signal_analysis = {"signal_count": 10}
        mock_trade_execution = {"total_trades": 8}
        mock_position_management = {"open_position_count": 5}
        mock_risk_analysis = {"portfolio_beta": 1.0}
        mock_system_performance = {"signal_accuracy": 80.0}
        mock_next_day_outlook = {"market_outlook": "Neutral"}
        
        # Set mock return values
        mock_generate_daily_summary.return_value = mock_daily_summary
        mock_generate_signal_analysis.return_value = mock_signal_analysis
        mock_generate_trade_execution.return_value = mock_trade_execution
        mock_generate_position_management.return_value = mock_position_management
        mock_generate_risk_analysis.return_value = mock_risk_analysis
        mock_generate_system_performance.return_value = mock_system_performance
        mock_generate_next_day_outlook.return_value = mock_next_day_outlook
        
        # Call method
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            self.reporting_service._generate_report_data(date.today(), 1)
        )
        
        # Check result
        self.assertEqual(result["daily_summary"], mock_daily_summary)
        self.assertEqual(result["signal_analysis"], mock_signal_analysis)
        self.assertEqual(result["trade_execution"], mock_trade_execution)
        self.assertEqual(result["position_management"], mock_position_management)
        self.assertEqual(result["risk_analysis"], mock_risk_analysis)
        self.assertEqual(result["system_performance"], mock_system_performance)
        self.assertEqual(result["next_day_outlook"], mock_next_day_outlook)
        
        # Check mock calls
        mock_generate_daily_summary.assert_called_once()
        mock_generate_signal_analysis.assert_called_once()
        mock_generate_trade_execution.assert_called_once()
        mock_generate_position_management.assert_called_once()
        mock_generate_risk_analysis.assert_called_once()
        mock_generate_system_performance.assert_called_once()
        mock_generate_next_day_outlook.assert_called_once()

class TestEmailService(unittest.TestCase):
    """Test cases for email service."""
    
    def setUp(self):
        """Set up test environment."""
        # Create email service
        self.email_service = EmailService()
    
    @patch('smtplib.SMTP')
    def test_send_email(self, mock_smtp):
        """Test send email."""
        # Mock SMTP instance
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
        
        # Set environment variables
        import os
        os.environ["SMTP_USERNAME"] = "test@example.com"
        os.environ["SMTP_PASSWORD"] = "password"
        
        # Call method
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            self.email_service.send_email(
                to_email="user@example.com",
                subject="Test Subject",
                html_content="<p>Test Content</p>",
                text_content="Test Content"
            )
        )
        
        # Check result
        self.assertTrue(result)
        
        # Check mock calls
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("test@example.com", "password")
        mock_smtp_instance.send_message.assert_called_once()
    
    @patch.object(EmailService, 'send_email')
    def test_send_daily_report_email(self, mock_send_email):
        """Test send daily report email."""
        # Mock send_email
        mock_send_email.return_value = True
        
        # Mock report data
        mock_report_data = {
            "daily_summary": {
                "portfolio_value": 100000,
                "daily_pnl": 1000,
                "daily_pnl_pct": 1.0,
                "signals_generated": 10,
                "signals_executed": 5,
                "total_trades": 8,
                "market_context": {
                    "market_condition": "Normal"
                },
                "fundamental_context": {
                    "mag7_data": {
                        "AAPL": {
                            "pe_ratio": 25.5,
                            "price_target": 200.0,
                            "analyst_rating": "Buy",
                            "next_earnings_date": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
                        }
                    }
                }
            },
            "next_day_outlook": {
                "market_outlook": "Neutral",
                "expected_volatility": "Normal"
            }
        }
        
        # Call method
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            self.email_service.send_daily_report_email(
                to_email="user@example.com",
                report_date=date.today(),
                report_data=mock_report_data,
                pdf_path="/path/to/report.pdf"
            )
        )
        
        # Check result
        self.assertTrue(result)
        
        # Check mock calls
        mock_send_email.assert_called_once()
    
    @patch.object(EmailService, 'send_email')
    def test_send_earnings_alert_email(self, mock_send_email):
        """Test send earnings alert email."""
        # Mock send_email
        mock_send_email.return_value = True
        
        # Call method
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            self.email_service.send_earnings_alert_email(
                to_email="user@example.com",
                symbol="AAPL",
                earnings_date=date.today() + timedelta(days=1),
                earnings_time="AMC",
                estimated_eps=2.5,
                previous_eps=2.3,
                price_target=200.0,
                analyst_rating="Buy"
            )
        )
        
        # Check result
        self.assertTrue(result)
        
        # Check mock calls
        mock_send_email.assert_called_once()

class TestSchedulerService(unittest.TestCase):
    """Test cases for scheduler service."""
    
    def setUp(self):
        """Set up test environment."""
        # Create scheduler service
        self.scheduler_service = SchedulerService()
    
    def test_should_run_schedule(self):
        """Test should run schedule."""
        # Create mock schedule
        mock_schedule = MagicMock()
        mock_schedule.days_of_week = [0, 1, 2, 3, 4]  # Monday to Friday
        mock_schedule.time_of_day = "18:00"
        
        # Test with matching day and time
        now = datetime(2023, 1, 2, 18, 0, 0)  # Monday, 18:00
        self.assertTrue(self.scheduler_service._should_run_schedule(mock_schedule, now))
        
        # Test with matching day but different time
        now = datetime(2023, 1, 2, 19, 0, 0)  # Monday, 19:00
        self.assertFalse(self.scheduler_service._should_run_schedule(mock_schedule, now))
        
        # Test with different day
        now = datetime(2023, 1, 7, 18, 0, 0)  # Saturday, 18:00
        self.assertFalse(self.scheduler_service._should_run_schedule(mock_schedule, now))
    
    @patch.object(SchedulerService, '_execute_schedule')
    def test_check_scheduled_tasks(self, mock_execute_schedule):
        """Test check scheduled tasks."""
        # Mock query
        mock_schedule = MagicMock()
        mock_schedule.is_active = True
        mock_schedule.days_of_week = [0, 1, 2, 3, 4]  # Monday to Friday
        mock_schedule.time_of_day = "18:00"
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_schedule]
        
        # Mock should_run_schedule
        self.scheduler_service._should_run_schedule = MagicMock(return_value=True)
        
        # Call method
        now = datetime(2023, 1, 2, 18, 0, 0)  # Monday, 18:00
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            self.scheduler_service._check_scheduled_tasks(now)
        )
        
        # Check mock calls
        mock_execute_schedule.assert_called_once_with(mock_schedule)
    
    @patch.object(SchedulerService, '_check_earnings_alerts')
    @patch.object(SchedulerService, '_check_scheduled_tasks')
    def test_run_scheduler(self, mock_check_scheduled_tasks, mock_check_earnings_alerts):
        """Test run scheduler."""
        # Set running flag
        self.scheduler_service.running = True
        
        # Mock asyncio.sleep to stop after one iteration
        async def mock_sleep(seconds):
            self.scheduler_service.running = False
        
        # Call method with mocked sleep
        with patch('asyncio.sleep', side_effect=mock_sleep):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                self.scheduler_service._run_scheduler()
            )
        
        # Check mock calls
        mock_check_scheduled_tasks.assert_called_once()
        mock_check_earnings_alerts.assert_called_once()

if __name__ == '__main__':
    unittest.main()

