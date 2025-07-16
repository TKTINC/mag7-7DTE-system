from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.signal import Signal, SignalType, SignalSource, SignalStatus
from app.schemas.signal import SignalResponse, SignalCreate, SignalUpdate

router = APIRouter()

@router.get("/", response_model=List[SignalResponse])
def get_signals(
    instrument_symbol: Optional[str] = None,
    signal_type: Optional[str] = None,
    signal_source: Optional[str] = None,
    status: Optional[str] = None,
    min_confidence: Optional[float] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    skip: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get signals with optional filtering.
    """
    query = db.query(Signal)
    
    if instrument_symbol:
        query = query.join(Signal.instrument).filter(Signal.instrument.has(symbol=instrument_symbol))
    
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    
    if signal_source:
        query = query.filter(Signal.signal_source == signal_source)
    
    if status:
        query = query.filter(Signal.status == status)
    
    if min_confidence is not None:
        query = query.filter(Signal.confidence_score >= min_confidence)
    
    if start_date:
        query = query.filter(Signal.generation_time >= start_date)
    
    if end_date:
        query = query.filter(Signal.generation_time <= end_date)
    
    # Default to last 7 days if no dates provided
    if not start_date and not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        query = query.filter(Signal.generation_time >= start_date, Signal.generation_time <= end_date)
    
    # Order by generation time (newest first)
    query = query.order_by(Signal.generation_time.desc())
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    return query.all()

@router.get("/{signal_id}", response_model=SignalResponse)
def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """
    Get signal by ID.
    """
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal with ID {signal_id} not found")
    return signal

@router.post("/", response_model=SignalResponse)
def create_signal(signal: SignalCreate, db: Session = Depends(get_db)):
    """
    Create a new signal.
    """
    # Convert Pydantic model to ORM model
    db_signal = Signal(**signal.dict())
    
    # Add to database
    db.add(db_signal)
    db.commit()
    db.refresh(db_signal)
    
    return db_signal

@router.put("/{signal_id}", response_model=SignalResponse)
def update_signal(signal_id: int, signal_update: SignalUpdate, db: Session = Depends(get_db)):
    """
    Update an existing signal.
    """
    # Get existing signal
    db_signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not db_signal:
        raise HTTPException(status_code=404, detail=f"Signal with ID {signal_id} not found")
    
    # Update signal with new values
    for key, value in signal_update.dict(exclude_unset=True).items():
        setattr(db_signal, key, value)
    
    # Commit changes
    db.commit()
    db.refresh(db_signal)
    
    return db_signal

@router.delete("/{signal_id}")
def delete_signal(signal_id: int, db: Session = Depends(get_db)):
    """
    Delete a signal.
    """
    # Get existing signal
    db_signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not db_signal:
        raise HTTPException(status_code=404, detail=f"Signal with ID {signal_id} not found")
    
    # Delete signal
    db.delete(db_signal)
    db.commit()
    
    return {"message": f"Signal with ID {signal_id} deleted successfully"}

@router.get("/active/count")
def get_active_signals_count(db: Session = Depends(get_db)):
    """
    Get count of active signals.
    """
    count = db.query(Signal).filter(Signal.status == SignalStatus.ACTIVE).count()
    return {"active_signals_count": count}

@router.get("/performance/summary")
def get_signals_performance_summary(
    instrument_symbol: Optional[str] = None,
    signal_type: Optional[str] = None,
    signal_source: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get performance summary of signals.
    """
    query = db.query(Signal)
    
    if instrument_symbol:
        query = query.join(Signal.instrument).filter(Signal.instrument.has(symbol=instrument_symbol))
    
    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    
    if signal_source:
        query = query.filter(Signal.signal_source == signal_source)
    
    if start_date:
        query = query.filter(Signal.generation_time >= start_date)
    
    if end_date:
        query = query.filter(Signal.generation_time <= end_date)
    
    # Default to last 30 days if no dates provided
    if not start_date and not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        query = query.filter(Signal.generation_time >= start_date, Signal.generation_time <= end_date)
    
    # Filter signals with profit_loss not None (i.e., closed signals)
    query = query.filter(Signal.profit_loss != None)
    
    signals = query.all()
    
    # Calculate performance metrics
    total_signals = len(signals)
    profitable_signals = sum(1 for s in signals if s.profit_loss > 0)
    win_rate = profitable_signals / total_signals if total_signals > 0 else 0
    
    total_profit = sum(s.profit_loss for s in signals if s.profit_loss > 0)
    total_loss = sum(abs(s.profit_loss) for s in signals if s.profit_loss < 0)
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
    
    average_profit = total_profit / profitable_signals if profitable_signals > 0 else 0
    average_loss = total_loss / (total_signals - profitable_signals) if (total_signals - profitable_signals) > 0 else 0
    
    return {
        "total_signals": total_signals,
        "profitable_signals": profitable_signals,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "average_profit": average_profit,
        "average_loss": average_loss,
        "total_profit_loss": total_profit - total_loss
    }

