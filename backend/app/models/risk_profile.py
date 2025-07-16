from sqlalchemy import Column, Integer, Float, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

class RiskProfile(Base):
    __tablename__ = "risk_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Risk parameters
    max_portfolio_risk = Column(Float, default=2.0)  # Max % of portfolio to risk per trade
    max_portfolio_exposure = Column(Float, default=50.0)  # Max % of portfolio in options
    max_stock_allocation = Column(Float, default=10.0)  # Max % allocation to a single stock
    max_loss_per_trade = Column(Float, default=25.0)  # Max % loss per trade
    risk_reward_ratio = Column(Float, default=2.0)  # Target risk-reward ratio
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="risk_profile")
    
    def to_dict(self):
        return {
            "max_portfolio_risk": self.max_portfolio_risk,
            "max_portfolio_exposure": self.max_portfolio_exposure,
            "max_stock_allocation": self.max_stock_allocation,
            "max_loss_per_trade": self.max_loss_per_trade,
            "risk_reward_ratio": self.risk_reward_ratio
        }

