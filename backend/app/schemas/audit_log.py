"""Audit log schemas"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

from app.models.audit_log import AuditAction


class AuditLogResponse(BaseModel):
    """Schema for audit log response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: Optional[int]
    action: AuditAction
    user_id: str
    user_name: Optional[str]
    success: bool
    error_message: Optional[str]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
