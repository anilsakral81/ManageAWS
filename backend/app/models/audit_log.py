"""Audit log database model"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class AuditAction(str, Enum):
    """Audit action enumeration"""
    TENANT_START = "tenant_start"
    TENANT_STOP = "tenant_stop"
    TENANT_SCALE = "tenant_scale"
    TENANT_CREATE = "tenant_create"
    TENANT_UPDATE = "tenant_update"
    TENANT_DELETE = "tenant_delete"
    SCHEDULE_CREATE = "schedule_create"
    SCHEDULE_UPDATE = "schedule_update"
    SCHEDULE_DELETE = "schedule_delete"
    SCHEDULE_EXECUTE = "schedule_execute"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"


class AuditLog(Base):
    """Audit log model for tracking all user actions"""
    
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)  # Keycloak user ID or email
    user_name = Column(String(255), nullable=True)
    
    # Action details
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(String(1000), nullable=True)
    details = Column(JSON, nullable=True)  # Additional context (e.g., replicas changed from X to Y)
    
    # Request metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(String(500), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(action='{self.action}', user='{self.user_id}', success={self.success})>"
