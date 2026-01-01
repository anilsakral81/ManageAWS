"""User schemas"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

from app.models.user_permission import UserRole


class UserResponse(BaseModel):
    """Schema for user response"""
    id: str
    email: EmailStr
    name: Optional[str]
    roles: list[str]


class UserPermissionResponse(BaseModel):
    """Schema for user permission response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    tenant_id: int
    role: UserRole
    created_at: datetime
    updated_at: datetime
    granted_by: Optional[str]
