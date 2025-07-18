import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    """Email service for sending notifications and reports."""
    
    def __init__(self):
        """Initialize email service with configuration from environment variables."""
        self.smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", 587))
        self.smtp_username = os.environ.get("SMTP_USERNAME", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.from_email = os.environ.get("FROM_EMAIL", "noreply@mag7-7dte-system.com")
        self.from_name = os.environ.get("FROM_NAME", "Mag7 7DTE System")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """Send email with optional attachments."""
        if not self.smtp_username or not self.smtp_password:
            logger.error("SMTP credentials not configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email
            
            # Add text content if provided
            if text_content:
                msg.attach(MIMEText(text_content, "plain"))
            
            # Add HTML content
            msg.attach(MIMEText(html_content, "html"))
            
            # Add attachments if provided
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, "rb") as file:
                            attachment = MIMEApplication(file.read(), _subtype="pdf")
                            attachment.add_header(
                                "Content-Disposition",
                                f"attachment; filename={os.path.basename(attachment_path)}"
                            )
                            msg.attach(attachment)
                    else:
                        logger.warning(f"Attachment not found: {attachment_path}")
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to_email}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def send_daily_report_email(
        self,
        to_email: str,
        report_date: datetime.date,
        report_data: dict,
        pdf_path: str
    ) -> bool:
        """Send daily report email with PDF attachment."""
        # Create subject
        subject = f"Mag7 7DTE Daily Trading Report - {report_date.strftime('%Y-%m-%d')}"
        
        # Create HTML content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #6200ea; }}
                h2 {{ color: #7c4dff; }}
                .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .metrics {{ display: flex; justify-content: space-between; flex-wrap: wrap; }}
                .metric {{ width: 48%; margin-bottom: 10px; }}
                .metric-title {{ font-weight: bold; }}
                .metric-value {{ font-size: 1.2em; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                .stocks {{ margin-top: 20px; }}
                .stock {{ margin-bottom: 10px; padding: 10px; background-color: #f9f9f9; border-radius: 5px; }}
                .stock-header {{ display: flex; justify-content: space-between; }}
                .stock-name {{ font-weight: bold; }}
                .stock-price {{ }}
                .stock-change {{ }}
                .footer {{ margin-top: 30px; font-size: 0.8em; color: #666; }}
                .earnings {{ margin-top: 20px; }}
                .earnings-item {{ margin-bottom: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Mag7 7DTE Daily Trading Report</h1>
                <p>Date: {report_date.strftime('%Y-%m-%d')}</p>
                
                <div class="summary">
                    <h2>Daily Summary</h2>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-title">Portfolio Value</div>
                            <div class="metric-value">${report_data['daily_summary']['portfolio_value']:,.2f}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Daily P&L</div>
                            <div class="metric-value {('positive' if report_data['daily_summary']['daily_pnl'] >= 0 else 'negative')}">
                                ${report_data['daily_summary']['daily_pnl']:,.2f} ({report_data['daily_summary']['daily_pnl_pct']:.2f}%)
                            </div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Signals Generated</div>
                            <div class="metric-value">{report_data['daily_summary']['signals_generated']}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Signals Executed</div>
                            <div class="metric-value">{report_data['daily_summary']['signals_executed']}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Total Trades</div>
                            <div class="metric-value">{report_data['daily_summary']['total_trades']}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Market Condition</div>
                            <div class="metric-value">{report_data['daily_summary']['market_context']['market_condition']}</div>
                        </div>
                    </div>
                </div>
                
                <div class="stocks">
                    <h2>Magnificent 7 Performance</h2>
        """
        
        # Add Mag7 stock data if available
        if 'fundamental_context' in report_data['daily_summary'] and 'mag7_data' in report_data['daily_summary']['fundamental_context']:
            for symbol, data in report_data['daily_summary']['fundamental_context']['mag7_data'].items():
                html_content += f"""
                    <div class="stock">
                        <div class="stock-header">
                            <span class="stock-name">{symbol}</span>
                            <span class="stock-price">P/E: {data['pe_ratio']:.2f}</span>
                        </div>
                        <div>Price Target: ${data['price_target']:.2f}</div>
                        <div>Analyst Rating: {data['analyst_rating']}</div>
                        <div>Next Earnings: {data['next_earnings_date'] if data['next_earnings_date'] else 'N/A'}</div>
                    </div>
                """
        
        # Add upcoming earnings if available
        if 'fundamental_context' in report_data['daily_summary'] and 'earnings_this_week' in report_data['daily_summary']['fundamental_context']:
            html_content += f"""
                <div class="earnings">
                    <h2>Upcoming Earnings</h2>
            """
            
            for earnings in report_data['daily_summary']['fundamental_context']['earnings_this_week']:
                html_content += f"""
                    <div class="earnings-item">
                        <strong>{earnings['symbol']}</strong> - {earnings['date']} ({earnings['time']})
                        Est. EPS: ${earnings['estimated_eps']:.2f} (Previous: ${earnings['previous_eps']:.2f})
                    </div>
                """
            
            html_content += """
                </div>
            """
        
        # Complete the HTML content
        html_content += f"""
                <p>The complete daily report is attached as a PDF. Please open the attachment to view the full report with detailed analysis.</p>
                
                <h2>Next Day Outlook</h2>
                <p><strong>Market Outlook:</strong> {report_data['next_day_outlook']['market_outlook']}</p>
                <p><strong>Expected Volatility:</strong> {report_data['next_day_outlook']['expected_volatility']}</p>
                
                <div class="footer">
                    <p>This is an automated report from the Mag7 7DTE System. Please do not reply to this email.</p>
                    <p>To change your notification preferences, please visit the system settings.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create text content
        text_content = f"""
        Mag7 7DTE Daily Trading Report - {report_date.strftime('%Y-%m-%d')}
        
        Daily Summary:
        - Portfolio Value: ${report_data['daily_summary']['portfolio_value']:,.2f}
        - Daily P&L: ${report_data['daily_summary']['daily_pnl']:,.2f} ({report_data['daily_summary']['daily_pnl_pct']:.2f}%)
        - Signals Generated: {report_data['daily_summary']['signals_generated']}
        - Signals Executed: {report_data['daily_summary']['signals_executed']}
        - Total Trades: {report_data['daily_summary']['total_trades']}
        - Market Condition: {report_data['daily_summary']['market_context']['market_condition']}
        
        The complete daily report is attached as a PDF. Please open the attachment to view the full report with detailed analysis.
        
        Next Day Outlook:
        - Market Outlook: {report_data['next_day_outlook']['market_outlook']}
        - Expected Volatility: {report_data['next_day_outlook']['expected_volatility']}
        
        This is an automated report from the Mag7 7DTE System. Please do not reply to this email.
        To change your notification preferences, please visit the system settings.
        """
        
        # Send email with PDF attachment
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            attachments=[pdf_path]
        )
    
    async def send_earnings_alert_email(
        self,
        to_email: str,
        symbol: str,
        earnings_date: datetime.date,
        earnings_time: str,
        estimated_eps: float,
        previous_eps: float,
        price_target: float,
        analyst_rating: str
    ) -> bool:
        """Send earnings alert email."""
        # Create subject
        subject = f"Earnings Alert: {symbol} - {earnings_date.strftime('%Y-%m-%d')}"
        
        # Create HTML content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #6200ea; }}
                h2 {{ color: #7c4dff; }}
                .alert {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .metrics {{ display: flex; justify-content: space-between; flex-wrap: wrap; }}
                .metric {{ width: 48%; margin-bottom: 10px; }}
                .metric-title {{ font-weight: bold; }}
                .metric-value {{ font-size: 1.2em; }}
                .footer {{ margin-top: 30px; font-size: 0.8em; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Earnings Alert: {symbol}</h1>
                
                <div class="alert">
                    <h2>Earnings Information</h2>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-title">Date</div>
                            <div class="metric-value">{earnings_date.strftime('%Y-%m-%d')}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Time</div>
                            <div class="metric-value">{earnings_time}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Estimated EPS</div>
                            <div class="metric-value">${estimated_eps:.2f}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Previous EPS</div>
                            <div class="metric-value">${previous_eps:.2f}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Price Target</div>
                            <div class="metric-value">${price_target:.2f}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-title">Analyst Rating</div>
                            <div class="metric-value">{analyst_rating}</div>
                        </div>
                    </div>
                </div>
                
                <p>This is an earnings alert for {symbol}. Please review your positions and consider adjusting your strategy accordingly.</p>
                
                <div class="footer">
                    <p>This is an automated alert from the Mag7 7DTE System. Please do not reply to this email.</p>
                    <p>To change your notification preferences, please visit the system settings.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create text content
        text_content = f"""
        Earnings Alert: {symbol} - {earnings_date.strftime('%Y-%m-%d')}
        
        Earnings Information:
        - Date: {earnings_date.strftime('%Y-%m-%d')}
        - Time: {earnings_time}
        - Estimated EPS: ${estimated_eps:.2f}
        - Previous EPS: ${previous_eps:.2f}
        - Price Target: ${price_target:.2f}
        - Analyst Rating: {analyst_rating}
        
        This is an earnings alert for {symbol}. Please review your positions and consider adjusting your strategy accordingly.
        
        This is an automated alert from the Mag7 7DTE System. Please do not reply to this email.
        To change your notification preferences, please visit the system settings.
        """
        
        # Send email
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

