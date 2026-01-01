"""Schedule database model"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class ScheduleAction(str, Enum):
    """Schedule action enumeration"""
    START = "start"
    STOP = "stop"


class Schedule(Base):
    """Schedule model for automated tenant operations"""
    
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    action = Column(SQLEnum(ScheduleAction), nullable=False)
    cron_expression = Column(String(100), nullable=False)  # e.g., "0 18 * * 1-5"
    enabled = Column(Boolean, default=True, nullable=False)
    description = Column(String(500), nullable=True)
    
    # Execution tracking
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    last_run_status = Column(String(50), nullable=True)  # success, failed, skipped
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(255), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="schedules")

    def __repr__(self):
        return f"<Schedule(tenant_id={self.tenant_id}, action='{self.action}', cron='{self.cron_expression}')>"
