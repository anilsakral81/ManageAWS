"""Audit log schemas"""

from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, field_serializer

from app.models.audit_log import AuditAction


class AuditLogResponse(BaseModel):
    """Schema for audit log response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: Optional[int]
    tenant_name: Optional[str] = None
    action: AuditAction
    user_id: str
    user_name: Optional[str] = None
    status: Literal['success', 'failed']
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    
    @staticmethod
    def from_audit_log(log) -> "AuditLogResponse":
        """Create response from audit log model"""
        return AuditLogResponse(
            id=log.id,
            tenant_id=log.tenant_id,
            tenant_name=None,  # Will be populated by service if needed
            action=log.action,
            user_id=log.user_id,
            user_name=log.user_name,
            status='success' if log.success else 'failed',
            details=log.error_message if not log.success else (str(log.details) if log.details else None),
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at
        )
