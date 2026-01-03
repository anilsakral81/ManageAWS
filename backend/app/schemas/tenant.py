"""Tenant schemas"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict

from app.models.tenant import TenantStatus


class TenantBase(BaseModel):
    """Base tenant schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Tenant name")
    namespace: str = Field(..., min_length=1, max_length=255, description="Kubernetes namespace")
    deployment_name: str = Field(..., min_length=1, max_length=255, description="Deployment name")
    description: Optional[str] = Field(None, max_length=500, description="Tenant description")
    enabled: bool = Field(True, description="Whether tenant is enabled")


class TenantCreate(TenantBase):
    """Schema for creating a new tenant"""
    desired_replicas: int = Field(1, ge=0, le=100, description="Desired replica count")


class TenantUpdate(BaseModel):
    """Schema for updating a tenant"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    enabled: Optional[bool] = None
    desired_replicas: Optional[int] = Field(None, ge=0, le=100)


class TenantScaleRequest(BaseModel):
    """Schema for scaling a tenant"""
    replicas: int = Field(..., ge=0, le=100, description="Target replica count (0=stop, 1=start)")


class TenantResponse(TenantBase):
    """Schema for tenant response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: TenantStatus
    current_replicas: int
    desired_replicas: int
    created_at: datetime
    updated_at: datetime
    last_scaled_at: Optional[datetime]
    last_scaled_by: Optional[str]
    virtualservices: List[Dict[str, str]] = []
