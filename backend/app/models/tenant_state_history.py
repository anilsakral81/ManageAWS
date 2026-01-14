"""Tenant state history database model for tracking uptime/downtime"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class StateType(str, Enum):
    """State type enumeration"""
    RUNNING = "running"  # Scaled >= 1 (including upscaling state)
    STOPPED = "stopped"  # Scaled to 0
    SCALING = "scaling"  # In the process of scaling up
    UNKNOWN = "unknown"


class TenantStateHistory(Base):
    """Model for tracking tenant state transitions over time"""
    
    __tablename__ = "tenant_state_history"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # State information
    previous_state = Column(SQLEnum(StateType, values_callable=lambda x: [e.value for e in x]), nullable=True)
    new_state = Column(SQLEnum(StateType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    
    # Replica information
    previous_replicas = Column(Integer, nullable=True)
    new_replicas = Column(Integer, nullable=False)
    
    # Timestamp for when state changed
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    changed_by = Column(String(255), nullable=True)  # User who triggered the change
    
    # Additional context
    reason = Column(String(500), nullable=True)  # e.g., "Manual scaling", "Schedule execution", "Auto-scale"
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    def __repr__(self):
        return f"<TenantStateHistory(tenant_id={self.tenant_id}, {self.previous_state} -> {self.new_state}, changed_at={self.changed_at})>"
