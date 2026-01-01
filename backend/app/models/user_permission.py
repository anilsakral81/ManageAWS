"""User permission database model"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class UserPermission(Base):
    """User permission model mapping users to tenants with roles"""
    
    __tablename__ = "user_permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)  # Keycloak user ID or email
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    granted_by = Column(String(255), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="user_permissions")

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant"),
    )

    def __repr__(self):
        return f"<UserPermission(user='{self.user_id}', tenant_id={self.tenant_id}, role='{self.role}')>"
