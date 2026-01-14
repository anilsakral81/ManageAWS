"""Service for calculating tenant uptime/downtime metrics"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from calendar import monthrange

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, case

from app.models.tenant import Tenant
from app.models.tenant_state_history import TenantStateHistory, StateType

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for calculating tenant uptime/downtime metrics"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_current_state_duration(self, tenant_id: int) -> Dict:
        """
        Get how long the tenant has been in its current state
        
        Returns:
            Dict with current_state, duration_seconds, duration_formatted, state_since
        """
        # Get the most recent state change
        result = await self.db.execute(
            select(TenantStateHistory)
            .where(TenantStateHistory.tenant_id == tenant_id)
            .order_by(TenantStateHistory.changed_at.desc())
            .limit(1)
        )
        latest_state = result.scalar_one_or_none()
        
        if not latest_state:
            return {
                "current_state": "unknown",
                "duration_seconds": 0,
                "duration_formatted": "Unknown",
                "state_since": None
            }
        
        current_time = datetime.now(timezone.utc)
        duration = current_time - latest_state.changed_at
        duration_seconds = int(duration.total_seconds())
        
        return {
            "current_state": latest_state.new_state.value,
            "duration_seconds": duration_seconds,
            "duration_formatted": self._format_duration(duration_seconds),
            "state_since": latest_state.changed_at.isoformat(),
            "changed_by": latest_state.changed_by
        }
    
    async def get_monthly_uptime_downtime(
        self,
        tenant_id: int,
        year: int,
        month: int
    ) -> Dict:
        """
        Calculate uptime and downtime for a specific month
        
        Args:
            tenant_id: Tenant ID
            year: Year (e.g., 2026)
            month: Month (1-12)
            
        Returns:
            Dict with uptime_seconds, downtime_seconds, uptime_percentage, etc.
        """
        # Calculate month start and end (timezone-aware)
        month_start = datetime(year, month, 1, tzinfo=timezone.utc)
        last_day = monthrange(year, month)[1]
        month_end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
        
        # If month hasn't ended yet, use current time
        current_time = datetime.now(timezone.utc)
        if month_end > current_time:
            month_end = current_time
        
        # Get all state changes in this month plus the one before
        result = await self.db.execute(
            select(TenantStateHistory)
            .where(
                and_(
                    TenantStateHistory.tenant_id == tenant_id,
                    TenantStateHistory.changed_at <= month_end
                )
            )
            .order_by(TenantStateHistory.changed_at.asc())
        )
        state_history = result.scalars().all()
        
        if not state_history:
            # No history, assume stopped
            total_seconds = (month_end - month_start).total_seconds()
            return {
                "year": year,
                "month": month,
                "uptime_seconds": 0,
                "downtime_seconds": int(total_seconds),
                "scaling_seconds": 0,
                "uptime_percentage": 0.0,
                "downtime_percentage": 100.0,
                "uptime_formatted": "0h",
                "downtime_formatted": self._format_duration(int(total_seconds)),
                "total_seconds": int(total_seconds)
            }
        
        # Calculate durations
        uptime_seconds = 0
        downtime_seconds = 0
        scaling_seconds = 0
        
        # Find the state at the beginning of the month
        initial_state = None
        for i, state in enumerate(state_history):
            if state.changed_at >= month_start:
                # Found first change in the month
                if i > 0:
                    initial_state = state_history[i-1].new_state
                break
        else:
            # All changes are in this month, or last change is before month end
            if state_history[-1].changed_at < month_start:
                initial_state = state_history[-1].new_state
        
        # If we don't have initial state, assume stopped
        if initial_state is None:
            initial_state = StateType.STOPPED
        
        # Process each state change
        current_state = initial_state
        current_time = month_start
        
        for state in state_history:
            if state.changed_at < month_start:
                continue
            
            if state.changed_at > month_end:
                break
            
            # Calculate duration in current state
            duration = (state.changed_at - current_time).total_seconds()
            
            # Track duration based on state - SCALING is considered uptime
            if current_state in [StateType.RUNNING, StateType.SCALING]:
                uptime_seconds += duration
                if current_state == StateType.SCALING:
                    scaling_seconds += duration
            elif current_state == StateType.STOPPED:
                downtime_seconds += duration
            
            # Move to next state
            current_time = state.changed_at
            current_state = state.new_state
        
        # Add remaining time in the month
        if current_time < month_end:
            duration = (month_end - current_time).total_seconds()
            if current_state in [StateType.RUNNING, StateType.SCALING]:
                uptime_seconds += duration
                if current_state == StateType.SCALING:
                    scaling_seconds += duration
            elif current_state == StateType.STOPPED:
                downtime_seconds += duration
        
        total_seconds = uptime_seconds + downtime_seconds
        uptime_percentage = (uptime_seconds / total_seconds * 100) if total_seconds > 0 else 0
        downtime_percentage = (downtime_seconds / total_seconds * 100) if total_seconds > 0 else 0
        
        return {
            "year": year,
            "month": month,
            "uptime_seconds": int(uptime_seconds),
            "downtime_seconds": int(downtime_seconds),
            "scaling_seconds": int(scaling_seconds),
            "uptime_percentage": round(uptime_percentage, 2),
            "downtime_percentage": round(downtime_percentage, 2),
            "uptime_formatted": self._format_duration(int(uptime_seconds)),
            "downtime_formatted": self._format_duration(int(downtime_seconds)),
            "scaling_formatted": self._format_duration(int(scaling_seconds)),
            "total_seconds": int(total_seconds),
            "month_start": month_start.isoformat(),
            "month_end": month_end.isoformat()
        }
    
    async def get_state_history(
        self,
        tenant_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get state change history for a tenant
        
        Args:
            tenant_id: Tenant ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of records to return
            
        Returns:
            List of state change records
        """
        query = select(TenantStateHistory).where(TenantStateHistory.tenant_id == tenant_id)
        
        if start_date:
            query = query.where(TenantStateHistory.changed_at >= start_date)
        
        if end_date:
            query = query.where(TenantStateHistory.changed_at <= end_date)
        
        query = query.order_by(TenantStateHistory.changed_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        history = result.scalars().all()
        
        return [
            {
                "id": h.id,
                "previous_state": h.previous_state.value if h.previous_state else None,
                "new_state": h.new_state.value,
                "previous_replicas": h.previous_replicas,
                "new_replicas": h.new_replicas,
                "changed_at": h.changed_at.isoformat(),
                "changed_by": h.changed_by,
                "reason": h.reason
            }
            for h in history
        ]
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to human-readable string"""
        if seconds < 60:
            return f"{seconds}s"
        
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m"
        
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if hours < 24:
            if remaining_minutes > 0:
                return f"{hours}h {remaining_minutes}m"
            return f"{hours}h"
        
        days = hours // 24
        remaining_hours = hours % 24
        if remaining_hours > 0:
            return f"{days}d {remaining_hours}h"
        return f"{days}d"
