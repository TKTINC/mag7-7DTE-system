from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON, Text, Enum, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.models.market_data import Base

class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    ANALYST = "analyst"
    TRADER = "trader"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # User preferences
    preferences = Column(JSON, nullable=True)
    
    # API access
    api_key = Column(String(100), nullable=True, unique=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    api_keys = relationship("ApiKey", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    activity_logs = relationship("ActivityLog", back_populates="user")

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key = Column(String(100), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Permissions
    permissions = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Notification details
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)  # e.g., "signal", "trade", "system"
    is_read = Column(Boolean, nullable=False, default=False)
    
    # Related entities
    related_entity_type = Column(String(50), nullable=True)  # e.g., "signal", "trade", "position"
    related_entity_id = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="notifications")

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Activity details
    activity_type = Column(String(50), nullable=False)  # e.g., "login", "signal_generation", "trade"
    description = Column(Text, nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(200), nullable=True)
    
    # Related entities
    related_entity_type = Column(String(50), nullable=True)
    related_entity_id = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="activity_logs")

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # UI preferences
    theme = Column(String(20), nullable=True, default="light")
    dashboard_layout = Column(JSON, nullable=True)
    default_timeframe = Column(String(20), nullable=True, default="7d")
    
    # Notification preferences
    email_notifications = Column(Boolean, nullable=False, default=True)
    push_notifications = Column(Boolean, nullable=False, default=True)
    notification_frequency = Column(String(20), nullable=True, default="realtime")  # "realtime", "daily", "weekly"
    
    # Trading preferences
    default_account_id = Column(Integer, nullable=True)
    default_risk_profile_id = Column(Integer, nullable=True)
    auto_trade = Column(Boolean, nullable=False, default=False)
    
    # Watchlist preferences
    default_watchlist_id = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

