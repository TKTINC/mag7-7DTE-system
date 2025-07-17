import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

from app.models.reporting import Report, ReportType, MarketCondition, FundamentalData
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalStatus
from app.models.trade import Trade
from app.models.position import Position
from app.models.market_data import MarketData, Instrument
from app.models.user import User

logger = logging.getLogger(__name__)

class ReportingService:
    """Base reporting service with common functionality."""
    
    def __init__(self, db: Session):
        self.db = db
        self.report_dir = os.environ.get("REPORT_DIR", "/app/reports")
        
        # Create report directory if it doesn't exist
        os.makedirs(self.report_dir, exist_ok=True)
    
    async def generate_daily_report(self, date: datetime.date = None, portfolio_id: int = 1) -> Dict[str, Any]:
        """Generate daily report for a specific date."""
        if date is None:
            date = datetime.utcnow().date()
        
        # Check if report already exists
        existing_report = self.db.query(Report).filter(
            Report.portfolio_id == portfolio_id,
            Report.report_type == ReportType.DAILY,
            Report.start_date == date,
            Report.end_date == date
        ).first()
        
        if existing_report:
            logger.info(f"Daily report for {date} already exists, returning existing report")
            return existing_report.report_data
        
        # Generate report data
        report_data = await self._generate_report_data(date, portfolio_id)
        
        # Create report record
        report = Report(
            portfolio_id=portfolio_id,
            report_type=ReportType.DAILY,
            start_date=date,
            end_date=date,
            title=f"Daily Trading Report - {date.strftime('%Y-%m-%d')}",
            description=f"Comprehensive trading report for {date.strftime('%Y-%m-%d')}",
            report_data=report_data
        )
        
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        
        # Generate PDF
        pdf_path = await self._generate_pdf_report(report_data, report.id)
        
        # Update report with PDF path
        report.pdf_path = pdf_path
        self.db.commit()
        
        return report_data
    
    async def _generate_report_data(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate report data for a specific date."""
        # This method should be overridden by system-specific implementations
        raise NotImplementedError("This method must be implemented by subclasses")
    
    async def _generate_pdf_report(self, report_data: Dict[str, Any], report_id: int) -> str:
        """Generate PDF report from report data."""
        # Create PDF file path
        date_str = report_data["report_date"]
        pdf_path = os.path.join(self.report_dir, f"daily_report_{date_str}_{report_id}.pdf")
        
        # Create PDF document
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Build PDF content
        story = []
        
        # Add title
        styles = getSampleStyleSheet()
        title = Paragraph(f"Trading Report - {date_str}", styles["Title"])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Add daily summary section
        story.append(Paragraph("Daily Summary", styles["Heading1"]))
        summary = report_data["daily_summary"]
        
        # Create summary table
        summary_data = [
            ["Portfolio Value", f"${summary['portfolio_value']:,.2f}"],
            ["Daily P&L", f"${summary['daily_pnl']:,.2f} ({summary['daily_pnl_pct']:.2f}%)"],
            ["Total Trades", str(summary['total_trades'])],
            ["Signals Generated", str(summary['signals_generated'])],
            ["Signals Executed", str(summary['signals_executed'])],
            ["Market Condition", summary['market_context']['market_condition']]
        ]
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 24))
        
        # Add fundamental context section (7DTE specific)
        if "fundamental_context" in summary:
            story.append(Paragraph("Fundamental Context", styles["Heading2"]))
            
            # Add Mag7 fundamental data
            if "mag7_data" in summary["fundamental_context"]:
                story.append(Paragraph("Magnificent 7 Fundamentals", styles["Heading3"]))
                
                mag7_data = [["Symbol", "PE Ratio", "Price Target", "Analyst Rating", "Next Earnings"]]
                
                for symbol, data in summary["fundamental_context"]["mag7_data"].items():
                    mag7_data.append([
                        symbol,
                        f"{data.get('pe_ratio', 'N/A')}",
                        f"${data.get('price_target', 0):.2f}" if data.get('price_target') else "N/A",
                        data.get('analyst_rating', 'N/A'),
                        data.get('next_earnings_date', 'N/A')
                    ])
                
                mag7_table = Table(mag7_data)
                mag7_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(mag7_table)
                story.append(Spacer(1, 12))
            
            # Add earnings this week
            if "earnings_this_week" in summary["fundamental_context"] and summary["fundamental_context"]["earnings_this_week"]:
                story.append(Paragraph("Earnings This Week", styles["Heading3"]))
                
                earnings_data = [["Symbol", "Date", "Time", "Est. EPS", "Prev. EPS"]]
                
                for earnings in summary["fundamental_context"]["earnings_this_week"]:
                    earnings_data.append([
                        earnings['symbol'],
                        earnings['date'],
                        earnings['time'],
                        f"${earnings.get('estimated_eps', 0):.2f}" if earnings.get('estimated_eps') else "N/A",
                        f"${earnings.get('previous_eps', 0):.2f}" if earnings.get('previous_eps') else "N/A"
                    ])
                
                earnings_table = Table(earnings_data)
                earnings_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(earnings_table)
                story.append(Spacer(1, 12))
        
        # Add signal analysis section
        story.append(Paragraph("Signal Analysis", styles["Heading1"]))
        signals = report_data["signal_analysis"]
        
        # Add signal summary
        story.append(Paragraph(f"Total Signals: {signals['signal_count']}", styles["Normal"]))
        story.append(Spacer(1, 12))
        
        # Add source performance table
        if signals.get('source_performance'):
            story.append(Paragraph("Signal Source Performance", styles["Heading2"]))
            source_data = [["Source", "Signals", "Executed", "Win Rate", "Avg Confidence"]]
            
            for source, perf in signals['source_performance'].items():
                source_data.append([
                    source,
                    str(perf['total_signals']),
                    str(perf['executed_signals']),
                    f"{perf['win_rate']:.2%}",
                    f"{perf['avg_confidence']:.2f}"
                ])
            
            source_table = Table(source_data)
            source_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(source_table)
            story.append(Spacer(1, 12))
        
        # Add trade execution section
        story.append(Paragraph("Trade Execution", styles["Heading1"]))
        trades = report_data["trade_execution"]
        
        # Add trade summary
        story.append(Paragraph(f"Total Trades: {trades['total_trades']}", styles["Normal"]))
        story.append(Spacer(1, 12))
        
        # Add trade details table
        if trades.get('trades'):
            story.append(Paragraph("Trade Details", styles["Heading2"]))
            trade_data = [["Time", "Symbol", "Type", "Price", "Quantity", "Value"]]
            
            for trade in trades['trades']:
                trade_data.append([
                    trade['execution_time'],
                    trade['symbol'],
                    trade['trade_type'],
                    f"${trade['price']:.2f}",
                    str(trade['quantity']),
                    f"${trade['value']:.2f}"
                ])
            
            trade_table = Table(trade_data)
            trade_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'LEFT'),
                ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(trade_table)
            story.append(Spacer(1, 12))
        
        # Add position management section
        story.append(Paragraph("Position Management", styles["Heading1"]))
        positions = report_data["position_management"]
        
        # Add position summary
        story.append(Paragraph(f"Open Positions: {positions['open_position_count']}", styles["Normal"]))
        story.append(Paragraph(f"Closed Positions: {positions['closed_position_count']}", styles["Normal"]))
        story.append(Spacer(1, 12))
        
        # Add open positions table
        if positions.get('open_positions'):
            story.append(Paragraph("Open Positions", styles["Heading2"]))
            position_data = [["Symbol", "Entry Date", "Entry Price", "Current Price", "Quantity", "P&L", "P&L %", "Days Held"]]
            
            for position in positions['open_positions']:
                position_data.append([
                    position['symbol'],
                    position['entry_date'],
                    f"${position['entry_price']:.2f}",
                    f"${position['current_price']:.2f}",
                    str(position['quantity']),
                    f"${position['unrealized_pnl']:.2f}",
                    f"{position['unrealized_pnl_pct']:.2f}%",
                    str(position['days_held'])
                ])
            
            position_table = Table(position_data)
            position_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(position_table)
            story.append(Spacer(1, 12))
        
        # Add risk analysis section
        story.append(Paragraph("Risk Analysis", styles["Heading1"]))
        risk = report_data["risk_analysis"]
        
        # Add risk summary
        story.append(Paragraph(f"Portfolio Beta: {risk['portfolio_beta']:.2f}", styles["Normal"]))
        story.append(Paragraph(f"Value at Risk (95%): ${risk['value_at_risk']:,.2f}", styles["Normal"]))
        
        # Add correlation matrix (7DTE specific)
        if "correlation_matrix" in risk:
            story.append(Paragraph("Stock Correlation Matrix", styles["Heading2"]))
            
            # Create correlation matrix table
            corr_data = [[""] + risk["correlation_matrix"]["symbols"]]
            
            for i, symbol in enumerate(risk["correlation_matrix"]["symbols"]):
                row = [symbol]
                for j in range(len(risk["correlation_matrix"]["symbols"])):
                    row.append(f"{risk['correlation_matrix']['data'][i][j]:.2f}")
                corr_data.append(row)
            
            corr_table = Table(corr_data)
            
            # Create style with conditional formatting
            corr_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]
            
            # Add conditional formatting for correlation values
            for i in range(1, len(corr_data)):
                for j in range(1, len(corr_data[0])):
                    if i == j:  # Diagonal (self-correlation)
                        corr_style.append(('BACKGROUND', (j, i), (j, i), colors.lightgrey))
                    else:
                        try:
                            corr_value = float(corr_data[i][j])
                            if corr_value > 0.7:
                                corr_style.append(('BACKGROUND', (j, i), (j, i), colors.pink))
                            elif corr_value < 0.3:
                                corr_style.append(('BACKGROUND', (j, i), (j, i), colors.lightgreen))
                        except (ValueError, IndexError):
                            pass
            
            corr_table.setStyle(TableStyle(corr_style))
            
            story.append(corr_table)
            story.append(Spacer(1, 12))
        
        story.append(Spacer(1, 12))
        
        # Add system performance section
        story.append(Paragraph("System Performance", styles["Heading1"]))
        performance = report_data["system_performance"]
        
        # Add performance summary
        story.append(Paragraph(f"Signal Accuracy: {performance['signal_accuracy']:.2f}%", styles["Normal"]))
        story.append(Paragraph(f"Execution Efficiency: {performance['execution_efficiency']:.2f}%", styles["Normal"]))
        story.append(Spacer(1, 12))
        
        # Add next day outlook section
        story.append(Paragraph("Next Day Outlook", styles["Heading1"]))
        outlook = report_data["next_day_outlook"]
        
        # Add outlook summary
        story.append(Paragraph(f"Market Outlook: {outlook['market_outlook']}", styles["Normal"]))
        story.append(Paragraph(f"Expected Volatility: {outlook['expected_volatility']}", styles["Normal"]))
        
        # Add upcoming earnings (7DTE specific)
        if "upcoming_earnings" in outlook and outlook["upcoming_earnings"]:
            story.append(Paragraph("Upcoming Earnings", styles["Heading2"]))
            
            earnings_data = [["Symbol", "Date", "Time", "Est. EPS"]]
            
            for earnings in outlook["upcoming_earnings"]:
                earnings_data.append([
                    earnings['symbol'],
                    earnings['date'],
                    earnings['time'],
                    f"${earnings.get('estimated_eps', 0):.2f}" if earnings.get('estimated_eps') else "N/A"
                ])
            
            earnings_table = Table(earnings_data)
            earnings_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(earnings_table)
        
        story.append(Spacer(1, 12))
        
        # Build PDF
        doc.build(story)
        
        return pdf_path
    
    async def get_report_by_date(self, date: datetime.date, portfolio_id: int = 1) -> Optional[Dict[str, Any]]:
        """Get report for a specific date."""
        report = self.db.query(Report).filter(
            Report.portfolio_id == portfolio_id,
            Report.report_type == ReportType.DAILY,
            Report.start_date == date,
            Report.end_date == date
        ).first()
        
        if not report:
            return None
        
        return report.report_data
    
    async def get_report_pdf_path(self, date: datetime.date, portfolio_id: int = 1) -> Optional[str]:
        """Get PDF path for a report on a specific date."""
        report = self.db.query(Report).filter(
            Report.portfolio_id == portfolio_id,
            Report.report_type == ReportType.DAILY,
            Report.start_date == date,
            Report.end_date == date
        ).first()
        
        if not report or not report.pdf_path:
            return None
        
        return report.pdf_path

