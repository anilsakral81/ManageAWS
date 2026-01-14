"""Metrics schemas for API responses"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CurrentStateDuration(BaseModel):
    """Schema for current state duration"""
    current_state: str
    duration_seconds: int
    duration_formatted: str
    state_since: Optional[str]
    changed_by: Optional[str]


class MonthlyMetrics(BaseModel):
    """Schema for monthly uptime/downtime metrics"""
    year: int
    month: int
    uptime_seconds: int
    downtime_seconds: int
    scaling_seconds: int
    uptime_percentage: float
    downtime_percentage: float
    uptime_formatted: str
    downtime_formatted: str
    scaling_formatted: str
    total_seconds: int
    month_start: str
    month_end: str


class StateHistoryRecord(BaseModel):
    """Schema for state history record"""
    id: int
    previous_state: Optional[str]
    new_state: str
    previous_replicas: Optional[int]
    new_replicas: int
    changed_at: str
    changed_by: Optional[str]
    reason: Optional[str]


class TenantMetrics(BaseModel):
    """Schema for comprehensive tenant metrics"""
    tenant_id: int
    tenant_name: str
    namespace: str
    current_state: CurrentStateDuration
    monthly_metrics: Optional[MonthlyMetrics] = None
    recent_history: List[StateHistoryRecord] = []
