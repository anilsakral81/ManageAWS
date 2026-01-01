"""Tenant database model"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class TenantStatus(str, Enum):
    """Tenant status enumeration"""
    RUNNING = "running"
    STOPPED = "stopped"
    SCALING = "scaling"
    ERROR = "error"
    UNKNOWN = "unknown"


class Tenant(Base):
    """Tenant model representing a Kubernetes-based tenant"""
    
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    namespace = Column(String(255), nullable=False, index=True)
    deployment_name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    status = Column(SQLEnum(TenantStatus), default=TenantStatus.UNKNOWN, nullable=False)
    current_replicas = Column(Integer, default=0, nullable=False)
    desired_replicas = Column(Integer, default=1, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_scaled_at = Column(DateTime, nullable=True)
    last_scaled_by = Column(String(255), nullable=True)

    # Relationships
    schedules = relationship("Schedule", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")
    user_permissions = relationship("UserPermission", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(name='{self.name}', namespace='{self.namespace}', status='{self.status}')>"
