from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.services.risk_management_service import RiskManagementService
from app.schemas.risk_management import (
    PositionSizeRequest,
    PositionSizeResponse,
    PortfolioExposureResponse,
    StopLossTakeProfitRequest,
    StopLossTakeProfitResponse,
    StopLossTakeProfitCheckResponse,
    PortfolioMetricsResponse,
    RiskProfileRecommendationsResponse
)

router = APIRouter()

@router.post("/position-size", response_model=PositionSizeResponse)
def calculate_position_size(
    request: PositionSizeRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate recommended position size based on risk parameters.
    """
    risk_service = RiskManagementService(db)
    result = risk_service.calculate_position_size(
        user_id=request.user_id,
        instrument_id=request.instrument_id,
        signal_confidence=request.signal_confidence,
        option_price=request.option_price
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@router.get("/portfolio-exposure/{user_id}", response_model=PortfolioExposureResponse)
def check_portfolio_exposure(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Check portfolio exposure against risk limits.
    """
    risk_service = RiskManagementService(db)
    result = risk_service.check_portfolio_exposure(user_id)
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.post("/stop-loss-take-profit", response_model=StopLossTakeProfitResponse)
def calculate_stop_loss_take_profit(
    request: StopLossTakeProfitRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate recommended stop-loss and take-profit levels for a position.
    """
    risk_service = RiskManagementService(db)
    result = risk_service.calculate_stop_loss_take_profit(
        position_id=request.position_id,
        risk_reward_ratio=request.risk_reward_ratio
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.get("/stop-loss-take-profit/check/{position_id}", response_model=StopLossTakeProfitCheckResponse)
def check_stop_loss_take_profit(
    position_id: int,
    db: Session = Depends(get_db)
):
    """
    Check if a position has hit stop-loss or take-profit levels.
    """
    risk_service = RiskManagementService(db)
    result = risk_service.check_stop_loss_take_profit(position_id)
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.get("/portfolio-metrics/{user_id}", response_model=PortfolioMetricsResponse)
def get_portfolio_metrics(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Calculate risk metrics for a user's portfolio.
    """
    risk_service = RiskManagementService(db)
    result = risk_service.calculate_portfolio_metrics(user_id)
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.get("/risk-profile-recommendations/{user_id}", response_model=RiskProfileRecommendationsResponse)
def get_risk_profile_recommendations(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate risk profile recommendations based on trading history.
    """
    risk_service = RiskManagementService(db)
    result = risk_service.get_risk_profile_recommendations(user_id)
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.get("/correlation-matrix")
def get_correlation_matrix(
    lookback_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Calculate correlation matrix between Magnificent 7 stocks.
    """
    risk_service = RiskManagementService(db)
    correlation_matrix = risk_service.calculate_correlation_matrix(lookback_days)
    
    if correlation_matrix is None:
        raise HTTPException(status_code=400, detail="Failed to calculate correlation matrix")
    
    return correlation_matrix.to_dict()

