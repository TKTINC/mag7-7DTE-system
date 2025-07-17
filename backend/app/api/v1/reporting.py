from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta

from app.database import get_db
from app.schemas.reporting import ReportResponse, ReportScheduleCreate, ReportScheduleResponse
from app.models.reporting import Report, ReportType, ReportSchedule
from app.services.sevendte_reporting_service import SevenDTEReportingService

router = APIRouter(
    prefix="/reporting",
    tags=["reporting"],
    responses={404: {"description": "Not found"}},
)

@router.get("/daily/{date}", response_model=ReportResponse)
async def get_daily_report(
    date: date,
    portfolio_id: int = 1,
    db: Session = Depends(get_db)
):
    """Get daily report for a specific date."""
    # Convert string date to datetime.date
    report_date = date
    
    # Check if report exists
    report = db.query(Report).filter(
        Report.portfolio_id == portfolio_id,
        Report.report_type == ReportType.DAILY,
        Report.start_date == report_date,
        Report.end_date == report_date
    ).first()
    
    # If report doesn't exist, generate it
    if not report:
        reporting_service = SevenDTEReportingService(db)
        report_data = await reporting_service.generate_daily_report(report_date, portfolio_id)
        
        # Get the newly created report
        report = db.query(Report).filter(
            Report.portfolio_id == portfolio_id,
            Report.report_type == ReportType.DAILY,
            Report.start_date == report_date,
            Report.end_date == report_date
        ).first()
        
        if not report:
            raise HTTPException(status_code=500, detail="Failed to generate report")
    
    return {
        "id": report.id,
        "portfolio_id": report.portfolio_id,
        "report_type": report.report_type,
        "start_date": report.start_date,
        "end_date": report.end_date,
        "title": report.title,
        "description": report.description,
        "report_data": report.report_data,
        "pdf_path": report.pdf_path,
        "created_at": report.created_at
    }

@router.get("/daily/{date}/pdf")
async def get_daily_report_pdf(
    date: date,
    portfolio_id: int = 1,
    db: Session = Depends(get_db)
):
    """Get PDF for daily report."""
    # Convert string date to datetime.date
    report_date = date
    
    # Check if report exists
    report = db.query(Report).filter(
        Report.portfolio_id == portfolio_id,
        Report.report_type == ReportType.DAILY,
        Report.start_date == report_date,
        Report.end_date == report_date
    ).first()
    
    # If report doesn't exist or PDF doesn't exist, generate it
    if not report or not report.pdf_path:
        reporting_service = SevenDTEReportingService(db)
        report_data = await reporting_service.generate_daily_report(report_date, portfolio_id)
        
        # Get the newly created report
        report = db.query(Report).filter(
            Report.portfolio_id == portfolio_id,
            Report.report_type == ReportType.DAILY,
            Report.start_date == report_date,
            Report.end_date == report_date
        ).first()
        
        if not report or not report.pdf_path:
            raise HTTPException(status_code=500, detail="Failed to generate report PDF")
    
    # Return PDF file
    return FileResponse(
        path=report.pdf_path,
        filename=f"daily_report_{report_date}.pdf",
        media_type="application/pdf"
    )

@router.get("/list", response_model=List[ReportResponse])
async def list_reports(
    report_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    portfolio_id: int = 1,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List reports with optional filtering."""
    query = db.query(Report).filter(Report.portfolio_id == portfolio_id)
    
    if report_type:
        query = query.filter(Report.report_type == report_type)
    
    if start_date:
        query = query.filter(Report.start_date >= start_date)
    
    if end_date:
        query = query.filter(Report.end_date <= end_date)
    
    # Order by date descending
    query = query.order_by(Report.start_date.desc())
    
    # Apply pagination
    reports = query.offset(offset).limit(limit).all()
    
    return reports

@router.post("/schedule", response_model=ReportScheduleResponse)
async def create_report_schedule(
    schedule: ReportScheduleCreate,
    db: Session = Depends(get_db)
):
    """Create a new report schedule."""
    # Create new schedule
    db_schedule = ReportSchedule(
        user_id=schedule.user_id,
        report_type=schedule.report_type,
        is_active=schedule.is_active,
        time_of_day=schedule.time_of_day,
        days_of_week=schedule.days_of_week,
        email_delivery=schedule.email_delivery,
        notification_delivery=schedule.notification_delivery
    )
    
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    
    return db_schedule

@router.get("/schedule/{schedule_id}", response_model=ReportScheduleResponse)
async def get_report_schedule(
    schedule_id: int,
    db: Session = Depends(get_db)
):
    """Get a report schedule by ID."""
    schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Report schedule not found")
    
    return schedule

@router.delete("/schedule/{schedule_id}")
async def delete_report_schedule(
    schedule_id: int,
    db: Session = Depends(get_db)
):
    """Delete a report schedule."""
    schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Report schedule not found")
    
    db.delete(schedule)
    db.commit()
    
    return {"message": "Report schedule deleted successfully"}

@router.post("/generate/daily")
async def generate_daily_report(
    background_tasks: BackgroundTasks,
    report_date: Optional[date] = None,
    portfolio_id: int = 1,
    db: Session = Depends(get_db)
):
    """Generate daily report in the background."""
    if report_date is None:
        report_date = datetime.utcnow().date()
    
    # Add task to background
    background_tasks.add_task(_generate_daily_report_task, report_date, portfolio_id, db)
    
    return {"message": f"Daily report generation for {report_date} started in background"}

async def _generate_daily_report_task(report_date: date, portfolio_id: int, db: Session):
    """Background task to generate daily report."""
    reporting_service = SevenDTEReportingService(db)
    await reporting_service.generate_daily_report(report_date, portfolio_id)

@router.get("/fundamental/{symbol}")
async def get_fundamental_data(
    symbol: str,
    date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get fundamental data for a specific symbol."""
    from app.models.market_data import Instrument
    from app.models.reporting import FundamentalData
    
    if date is None:
        date = datetime.utcnow().date()
    
    # Get instrument
    instrument = db.query(Instrument).filter(Instrument.symbol == symbol).first()
    
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol} not found")
    
    # Get fundamental data
    fundamental_data = db.query(FundamentalData).filter(
        FundamentalData.instrument_id == instrument.id,
        FundamentalData.date <= date
    ).order_by(FundamentalData.date.desc()).first()
    
    if not fundamental_data:
        raise HTTPException(status_code=404, detail=f"Fundamental data for {symbol} not found")
    
    return {
        "symbol": symbol,
        "date": fundamental_data.date,
        "next_earnings_date": fundamental_data.next_earnings_date,
        "earnings_time": fundamental_data.earnings_time,
        "estimated_eps": fundamental_data.estimated_eps,
        "previous_eps": fundamental_data.previous_eps,
        "pe_ratio": fundamental_data.pe_ratio,
        "forward_pe": fundamental_data.forward_pe,
        "peg_ratio": fundamental_data.peg_ratio,
        "price_to_sales": fundamental_data.price_to_sales,
        "price_to_book": fundamental_data.price_to_book,
        "revenue_growth_yoy": fundamental_data.revenue_growth_yoy,
        "eps_growth_yoy": fundamental_data.eps_growth_yoy,
        "analyst_rating": fundamental_data.analyst_rating,
        "price_target": fundamental_data.price_target,
        "price_target_high": fundamental_data.price_target_high,
        "price_target_low": fundamental_data.price_target_low
    }

@router.get("/correlation-matrix")
async def get_correlation_matrix(
    date: Optional[date] = None,
    lookback_days: int = 30,
    db: Session = Depends(get_db)
):
    """Get correlation matrix for Magnificent 7 stocks."""
    from app.models.market_data import MarketData
    import numpy as np
    
    if date is None:
        date = datetime.utcnow().date()
    
    # Define Magnificent 7 symbols
    mag7_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"]
    
    # Calculate start date for lookback period
    start_date = date - timedelta(days=lookback_days)
    
    # Get price data for each symbol
    price_data = {}
    for symbol in mag7_symbols:
        prices = db.query(MarketData).filter(
            MarketData.symbol == symbol,
            MarketData.date >= start_date,
            MarketData.date <= date
        ).order_by(MarketData.date).all()
        
        if prices:
            price_data[symbol] = [p.close for p in prices]
    
    # Calculate correlation matrix
    correlation_matrix = {
        "symbols": mag7_symbols,
        "data": []
    }
    
    for symbol1 in mag7_symbols:
        row = []
        for symbol2 in mag7_symbols:
            if symbol1 in price_data and symbol2 in price_data:
                # Ensure both price series have the same length
                min_length = min(len(price_data[symbol1]), len(price_data[symbol2]))
                
                if min_length > 1:
                    # Calculate correlation
                    corr = np.corrcoef(price_data[symbol1][:min_length], price_data[symbol2][:min_length])[0, 1]
                    row.append(corr)
                else:
                    row.append(1.0 if symbol1 == symbol2 else 0.0)
            else:
                row.append(1.0 if symbol1 == symbol2 else 0.0)
        
        correlation_matrix["data"].append(row)
    
    return correlation_matrix

