"""User-Namespace permission mapping"""

from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base


class UserNamespace(Base):
    """Maps users to namespaces they can manage"""
    __tablename__ = "user_namespaces"
    
    user_id = Column(String(255), primary_key=True, index=True)  # Keycloak user sub
    namespace = Column(String(255), primary_key=True, index=True)
    enabled = Column(Boolean, default=True, nullable=False)
    granted_by = Column(String(255))  # Admin who granted access
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index('idx_user_namespace_active', 'user_id', 'namespace', 'enabled'),
    )
