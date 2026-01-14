"""Schedule service - Placeholder for implementation"""

import logging
from typing import List, Optional, Dict
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.schedule import Schedule
from app.models.tenant import Tenant
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleResponse

logger = logging.getLogger(__name__)


class ScheduleService:
    """Service for schedule management operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def list_schedules(
        self,
        user_id: str,
        tenant_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ScheduleResponse]:
        """List schedules"""
        from sqlalchemy.orm import selectinload
        
        query = select(Schedule).options(selectinload(Schedule.tenant))
        if tenant_id:
            query = query.where(Schedule.tenant_id == tenant_id)
        
        result = await self.db.execute(query.offset(skip).limit(limit))
        schedules = result.scalars().all()
        
        # Build response with tenant names
        response_schedules = []
        for schedule in schedules:
            schedule_dict = ScheduleResponse.model_validate(schedule).model_dump()
            schedule_dict["tenant_name"] = schedule.tenant.name if schedule.tenant else None
            response_schedules.append(ScheduleResponse(**schedule_dict))
        
        return response_schedules
    
    async def get_schedule(self, schedule_id: int, user_id: str) -> Optional[ScheduleResponse]:
        """Get schedule by ID"""
        from sqlalchemy.orm import selectinload
        
        result = await self.db.execute(
            select(Schedule).options(selectinload(Schedule.tenant)).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            return None
        
        schedule_dict = ScheduleResponse.model_validate(schedule).model_dump()
        schedule_dict["tenant_name"] = schedule.tenant.name if schedule.tenant else None
        return ScheduleResponse(**schedule_dict)
    
    async def create_schedule(
        self,
        schedule: ScheduleCreate,
        user_id: str,
        ip_address: Optional[str] = None
    ) -> ScheduleResponse:
        """Create schedule"""
        # Validate input
        if not schedule.namespace and not schedule.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'namespace' or 'tenant_id' must be provided"
            )
        
        # Find or create tenant
        if schedule.namespace:
            # Find tenant by namespace name, create if not exists
            result = await self.db.execute(
                select(Tenant).where(Tenant.namespace == schedule.namespace)
            )
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                # Create tenant record for this namespace
                tenant = Tenant(
                    name=schedule.namespace,
                    namespace=schedule.namespace,
                    deployment_name=f"{schedule.namespace}-deployment",
                    description=f"Auto-created for schedule",
                )
                self.db.add(tenant)
                await self.db.flush()  # Get the ID without committing
            
            tenant_id = tenant.id
        else:
            # Legacy: use tenant_id directly
            result = await self.db.execute(
                select(Tenant).where(Tenant.id == schedule.tenant_id)
            )
            tenant = result.scalar_one_or_none()
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant with id {schedule.tenant_id} not found"
                )
            tenant_id = tenant.id
        
        # Create schedule with resolved tenant_id
        schedule_data = schedule.model_dump(exclude={"namespace"})
        schedule_data["tenant_id"] = tenant_id
        db_schedule = Schedule(**schedule_data, created_by=user_id)
        self.db.add(db_schedule)
        await self.db.commit()
        await self.db.refresh(db_schedule)
        
        # Create audit log
        await self._create_audit_log(
            tenant_id=tenant.id,
            action=AuditAction.SCHEDULE_CREATE,
            user_id=user_id,
            ip_address=ip_address,
            success=True,
            details={"schedule_id": db_schedule.id, "description": db_schedule.description, "action": db_schedule.action.value}
        )
        await self.db.commit()  # Commit audit log
        
        # Add to scheduler if enabled
        if db_schedule.enabled:
            from app.services.scheduler import get_scheduler
            scheduler = get_scheduler()
            if scheduler:
                scheduler.add_schedule(db_schedule)
                logger.info(f"Registered schedule {db_schedule.id} with scheduler")
        
        # Populate tenant_name in response
        schedule_dict = ScheduleResponse.model_validate(db_schedule).model_dump()
        schedule_dict["tenant_name"] = tenant.name
        return ScheduleResponse(**schedule_dict)
    
    async def update_schedule(
        self,
        schedule_id: int,
        schedule_update: ScheduleUpdate,
        user_id: str,
        ip_address: Optional[str] = None
    ) -> ScheduleResponse:
        """Update schedule"""
        from sqlalchemy.orm import selectinload
        
        result = await self.db.execute(
            select(Schedule).options(selectinload(Schedule.tenant)).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        
        update_data = schedule_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(schedule, field, value)
        
        await self.db.commit()
        await self.db.refresh(schedule)
        
        # Update scheduler registration
        from app.services.scheduler import get_scheduler
        scheduler = get_scheduler()
        if scheduler:
            if schedule.enabled:
                scheduler.add_schedule(schedule)
                logger.info(f"Updated schedule {schedule.id} in scheduler")
            else:
                scheduler.remove_schedule(schedule.id)
                logger.info(f"Removed disabled schedule {schedule.id} from scheduler")
        
        # Create audit log
        await self._create_audit_log(
            tenant_id=schedule.tenant_id,
            action=AuditAction.SCHEDULE_UPDATE,
            user_id=user_id,
            ip_address=ip_address,
            success=True,
            details={"schedule_id": schedule.id, "description": schedule.description, "updates": update_data}
        )
        await self.db.commit()  # Commit audit log
        
        # Populate tenant_name in response
        schedule_dict = ScheduleResponse.model_validate(schedule).model_dump()
        schedule_dict["tenant_name"] = schedule.tenant.name if schedule.tenant else None
        return ScheduleResponse(**schedule_dict)
    
    async def delete_schedule(self, schedule_id: int, user_id: str, ip_address: Optional[str] = None) -> None:
        """Delete schedule"""
        result = await self.db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if not schedule:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        
        # Store details before deletion
        tenant_id = schedule.tenant_id
        schedule_description = schedule.description
        
        # Remove from scheduler
        from app.services.scheduler import get_scheduler
        scheduler = get_scheduler()
        if scheduler:
            scheduler.remove_schedule(schedule_id)
            logger.info(f"Removed schedule {schedule_id} from scheduler")
        
        await self.db.delete(schedule)
        await self.db.commit()
        
        # Create audit log
        await self._create_audit_log(
            tenant_id=tenant_id,
            action=AuditAction.SCHEDULE_DELETE,
            user_id=user_id,
            ip_address=ip_address,
            success=True,
            details={"schedule_id": schedule_id, "description": schedule_description}
        )
        await self.db.commit()  # Commit audit log
    
    async def _create_audit_log(
        self,
        action: AuditAction,
        user_id: str,
        tenant_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> None:
        """Create audit log entry"""
        import httpx
        from app.config import settings
        
        # Fetch user name from Keycloak
        user_name = None
        try:
            async with httpx.AsyncClient() as client:
                # Get admin token
                token_response = await client.post(
                    f"{settings.keycloak_url}/realms/master/protocol/openid-connect/token",
                    data={
                        "username": settings.keycloak_admin_username,
                        "password": settings.keycloak_admin_password,
                        "grant_type": "password",
                        "client_id": "admin-cli"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=5.0
                )
                
                if token_response.status_code == 200:
                    admin_token = token_response.json()["access_token"]
                    
                    # Get user details
                    user_response = await client.get(
                        f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/users/{user_id}",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        timeout=5.0
                    )
                    
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        first_name = user_data.get("firstName", "")
                        last_name = user_data.get("lastName", "")
                        user_name = f"{first_name} {last_name}".strip() or user_data.get("email", user_data.get("username", ""))
        except Exception as e:
            logger.warning(f"Could not fetch user name for audit log: {e}")
        
        audit_log = AuditLog(
            tenant_id=tenant_id,
            action=action,
            user_id=user_id,
            user_name=user_name,
            ip_address=ip_address,
            success=success,
            error_message=error_message,
            details=details
        )
        self.db.add(audit_log)
