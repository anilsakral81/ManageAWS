"""User schemas"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict

from app.models.user_permission import UserRole


class UserInfo(BaseModel):
    """Current user information from Keycloak"""
    sub: str  # Keycloak user ID
    email: Optional[EmailStr] = None
    preferred_username: str
    name: Optional[str] = None
    roles: List[str] = []
    groups: List[str] = []
    allowed_namespaces: List[str] = []


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


class UserNamespaceCreate(BaseModel):
    """Grant namespace access to user"""
    user_id: str
    namespace: str
    

class UserNamespaceResponse(BaseModel):
    """User namespace permission"""
    user_id: str
    namespace: str
    enabled: bool
    granted_by: Optional[str]
    granted_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
