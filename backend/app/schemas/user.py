"""User schemas"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict

from app.models.user_permission import UserRole


class UserInfo(BaseModel):
    """Current user information from Keycloak"""
    sub: str  # Keycloak user ID
    email: Optional[str] = None  # Changed from EmailStr to allow .local domains
    preferred_username: Optional[str] = None
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
    granted_by_email: Optional[str] = None  # Email of the user who granted access
    granted_by_name: Optional[str] = None   # Name of the user who granted access
    
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """Schema for creating a new user in Keycloak"""
    username: str
    email: str
    firstName: str
    lastName: str
    password: str
    enabled: bool = True
    emailVerified: bool = True
    roles: List[str] = []  # List of realm roles to assign


class UserUpdate(BaseModel):
    """Schema for updating a user in Keycloak"""
    email: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    enabled: Optional[bool] = None


class PasswordReset(BaseModel):
    """Schema for resetting user password"""
    password: str
    temporary: bool = False  # If True, user must change password on next login
