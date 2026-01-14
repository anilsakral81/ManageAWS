"""Schedule schemas"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.schedule import ScheduleAction


class ScheduleBase(BaseModel):
    """Base schedule schema"""
    action: ScheduleAction = Field(..., description="Schedule action (start/stop)")
    cron_expression: str = Field(..., min_length=9, max_length=100, description="Cron expression")
    enabled: bool = Field(True, description="Whether schedule is enabled")
    description: Optional[str] = Field(None, max_length=500, description="Schedule description")

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Validate cron expression format"""
        parts = v.split()
        if len(parts) != 5:
            raise ValueError("Cron expression must have 5 parts: minute hour day month weekday")
        return v


class ScheduleCreate(ScheduleBase):
    """Schema for creating a new schedule"""
    tenant_id: Optional[int] = Field(None, gt=0, description="Tenant ID (deprecated, use namespace)")
    namespace: Optional[str] = Field(None, min_length=1, max_length=255, description="Tenant namespace name")
    
    @field_validator("namespace")
    @classmethod
    def validate_namespace_or_tenant_id(cls, v: Optional[str], values) -> Optional[str]:
        """Ensure either namespace or tenant_id is provided"""
        # This will be validated in the service layer
        return v


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule"""
    action: Optional[ScheduleAction] = None
    cron_expression: Optional[str] = Field(None, min_length=9, max_length=100)
    enabled: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        """Validate cron expression format"""
        if v is not None:
            parts = v.split()
            if len(parts) != 5:
                raise ValueError("Cron expression must have 5 parts: minute hour day month weekday")
        return v


class ScheduleResponse(ScheduleBase):
    """Schema for schedule response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    tenant_name: Optional[str] = None
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    last_run_status: Optional[str]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
