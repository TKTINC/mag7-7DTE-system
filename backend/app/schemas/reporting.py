from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from enum import Enum

class ReportTypeEnum(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    CUSTOM = "CUSTOM"

class ReportBase(BaseModel):
    portfolio_id: int
    report_type: ReportTypeEnum
    start_date: date
    end_date: date
    title: str
    description: Optional[str] = None

class ReportCreate(ReportBase):
    pass

class ReportResponse(ReportBase):
    id: int
    report_data: Dict[str, Any]
    pdf_path: Optional[str] = None
    created_at: datetime
    
    class Config:
        orm_mode = True

class ReportScheduleBase(BaseModel):
    user_id: int
    report_type: ReportTypeEnum
    is_active: bool = True
    time_of_day: str  # Format: "HH:MM" in 24-hour format
    days_of_week: List[int]  # 0 = Monday, 6 = Sunday
    email_delivery: bool = True
    notification_delivery: bool = False

class ReportScheduleCreate(ReportScheduleBase):
    pass

class ReportScheduleResponse(ReportScheduleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class SignalFactorResponse(BaseModel):
    id: int
    signal_id: int
    factor_name: str
    factor_value: float
    factor_weight: float
    factor_category: str
    factor_description: Optional[str] = None
    
    class Config:
        orm_mode = True

class MarketConditionResponse(BaseModel):
    id: int
    date: date
    vix_open: float
    vix_high: float
    vix_low: float
    vix_close: float
    spy_open: float
    spy_high: float
    spy_low: float
    spy_close: float
    spy_volume: int
    condition_type: str
    is_unusual: bool
    notes: Optional[str] = None
    
    class Config:
        orm_mode = True

class FundamentalDataBase(BaseModel):
    instrument_id: int
    date: date
    next_earnings_date: Optional[date] = None
    earnings_time: Optional[str] = None  # BMO (Before Market Open), AMC (After Market Close)
    estimated_eps: Optional[float] = None
    previous_eps: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    price_to_sales: Optional[float] = None
    price_to_book: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    eps_growth_yoy: Optional[float] = None
    analyst_rating: Optional[str] = None
    price_target: Optional[float] = None
    price_target_high: Optional[float] = None
    price_target_low: Optional[float] = None

class FundamentalDataCreate(FundamentalDataBase):
    pass

class FundamentalDataResponse(FundamentalDataBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class CorrelationMatrixResponse(BaseModel):
    symbols: List[str]
    data: List[List[float]]

