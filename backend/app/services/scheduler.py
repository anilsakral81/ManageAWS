"""APScheduler integration for automated tenant management"""

import logging
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.schedule import Schedule, ScheduleAction
from app.models.tenant import Tenant
from app.models.audit_log import AuditLog, AuditAction
from app.config import settings

logger = logging.getLogger(__name__)


class SchedulerManager:
    """Manages APScheduler for automated tenant operations"""
    
    def __init__(self, session_factory: async_sessionmaker):
        self.scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
        self.session_factory = session_factory
        logger.info(f"Scheduler initialized with timezone: {settings.scheduler_timezone}")
    
    def start(self):
        """Start the scheduler"""
        if not settings.scheduler_enabled:
            logger.info("Scheduler is disabled in configuration")
            return
        
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started successfully")
        else:
            logger.warning("Scheduler is already running")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler shut down successfully")
    
    async def load_schedules(self):
        """Load all enabled schedules from database and add them to scheduler"""
        if not settings.scheduler_enabled:
            logger.info("Scheduler disabled, skipping schedule loading")
            return
        
        async with self.session_factory() as db:
            result = await db.execute(
                select(Schedule).where(Schedule.enabled == True)
            )
            schedules = result.scalars().all()
            
            logger.info(f"Loading {len(schedules)} enabled schedules")
            
            for schedule in schedules:
                try:
                    self.add_schedule(schedule)
                    logger.info(
                        f"Loaded schedule {schedule.id}: {schedule.action.value} "
                        f"for tenant {schedule.tenant_id} with cron '{schedule.cron_expression}'"
                    )
                except Exception as e:
                    logger.error(f"Failed to load schedule {schedule.id}: {e}")
    
    def add_schedule(self, schedule: Schedule):
        """Add a schedule to APScheduler"""
        if not settings.scheduler_enabled:
            return
        
        job_id = f"schedule_{schedule.id}"
        
        # Remove existing job if present
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # Parse cron expression and create trigger
        trigger = CronTrigger.from_crontab(
            schedule.cron_expression,
            timezone=settings.scheduler_timezone
        )
        
        # Add job to scheduler
        self.scheduler.add_job(
            self._execute_schedule,
            trigger=trigger,
            id=job_id,
            name=f"{schedule.action.value} tenant {schedule.tenant_id}",
            args=[schedule.id, schedule.tenant_id, schedule.action],
            replace_existing=True,
            misfire_grace_time=300,  # 5 minutes grace period
        )
        
        logger.info(f"Added schedule {schedule.id} to scheduler with job_id {job_id}")
    
    def remove_schedule(self, schedule_id: int):
        """Remove a schedule from APScheduler"""
        if not settings.scheduler_enabled:
            return
        
        job_id = f"schedule_{schedule_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed schedule {schedule_id} from scheduler")
    
    async def _execute_schedule(self, schedule_id: int, tenant_id: int, action: ScheduleAction):
        """Execute a scheduled action"""
        logger.info(f"Executing schedule {schedule_id}: {action.value} for tenant {tenant_id}")
        
        async with self.session_factory() as db:
            try:
                # Get tenant details
                result = await db.execute(
                    select(Tenant).where(Tenant.id == tenant_id)
                )
                tenant = result.scalar_one_or_none()
                
                if not tenant:
                    logger.error(f"Tenant {tenant_id} not found for schedule {schedule_id}")
                    await self._update_schedule_status(
                        db, schedule_id, success=False, 
                        error="Tenant not found"
                    )
                    return
                
                # Execute the action
                from app.services.tenant_service import TenantService
                from app.schemas.user import UserInfo
                tenant_service = TenantService(db)
                
                # Create a system user for scheduler
                scheduler_user = UserInfo(
                    sub="scheduler",
                    email="scheduler@system",
                    name="Automated Scheduler",
                    preferred_username="scheduler"
                )
                
                success = False
                error_message = None
                
                if action == ScheduleAction.START:
                    await tenant_service.start_tenant(
                        namespace=tenant.namespace,
                        user=scheduler_user,
                        ip_address="scheduler"
                    )
                    success = True
                    logger.info(f"Schedule {schedule_id}: Started tenant {tenant.namespace}")
                
                elif action == ScheduleAction.STOP:
                    await tenant_service.stop_tenant(
                        namespace=tenant.namespace,
                        user=scheduler_user,
                        ip_address="scheduler"
                    )
                    success = True
                    logger.info(f"Schedule {schedule_id}: Stopped tenant {tenant.namespace}")
                
                elif action == ScheduleAction.SCALE:
                    # Get the schedule to get scale parameters
                    schedule_result = await db.execute(
                        select(Schedule).where(Schedule.id == schedule_id)
                    )
                    schedule = schedule_result.scalar_one_or_none()
                    
                    if schedule and schedule.description:
                        # Try to extract replica count from description
                        # Expected format: "Scale to X replicas" or similar
                        import re
                        match = re.search(r'(\d+)\s*replica', schedule.description, re.IGNORECASE)
                        if match:
                            replicas = int(match.group(1))
                            await tenant_service.scale_tenant(
                                namespace=tenant.namespace,
                                replicas=replicas,
                                user=scheduler_user,
                                ip_address="scheduler"
                            )
                            success = True
                            logger.info(f"Schedule {schedule_id}: Scaled tenant {tenant.namespace} to {replicas} replicas")
                        else:
                            error_message = "Could not extract replica count"
                            logger.error(f"Schedule {schedule_id}: {error_message}")
                    else:
                        error_message = "Schedule not found or missing description"
                        logger.error(f"Schedule {schedule_id}: {error_message}")
                
                # Update schedule status
                await self._update_schedule_status(
                    db, schedule_id, success=success, 
                    error=error_message
                )
                
                # Create audit log
                audit_action_map = {
                    ScheduleAction.START: AuditAction.TENANT_START,
                    ScheduleAction.STOP: AuditAction.TENANT_STOP,
                    ScheduleAction.SCALE: AuditAction.TENANT_SCALE,
                }
                
                audit_log = AuditLog(
                    tenant_id=tenant_id,
                    action=audit_action_map.get(action, AuditAction.TENANT_STOP),
                    user_id="scheduler",
                    user_name="Automated Scheduler",
                    ip_address="scheduler",
                    success=success,
                    error_message=error_message,
                    details={
                        "schedule_id": schedule_id,
                        "action": action.value,
                        "triggered_by": "scheduler"
                    }
                )
                db.add(audit_log)
                await db.commit()
                
            except Exception as e:
                logger.error(f"Error executing schedule {schedule_id}: {e}", exc_info=True)
                await self._update_schedule_status(
                    db, schedule_id, success=False, 
                    error=str(e)
                )
                await db.commit()
    
    async def _update_schedule_status(
        self, 
        db: AsyncSession, 
        schedule_id: int, 
        success: bool,
        error: Optional[str] = None
    ):
        """Update schedule execution status"""
        try:
            result = await db.execute(
                select(Schedule).where(Schedule.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            
            if schedule:
                schedule.last_run_at = datetime.utcnow()
                # Truncate error message to fit in VARCHAR(50)
                status_msg = "success" if success else f"failed: {error}"
                schedule.last_run_status = status_msg[:50] if status_msg else None
                
                # Calculate next run time
                job_id = f"schedule_{schedule_id}"
                job = self.scheduler.get_job(job_id)
                if job and job.next_run_time:
                    schedule.next_run_at = job.next_run_time.replace(tzinfo=None)
                
                await db.commit()
                logger.info(f"Updated schedule {schedule_id} status: {schedule.last_run_status}")
        except Exception as e:
            logger.error(f"Failed to update schedule {schedule_id} status: {e}")


# Global scheduler instance
_scheduler_manager: Optional[SchedulerManager] = None


def get_scheduler() -> Optional[SchedulerManager]:
    """Get the global scheduler instance"""
    return _scheduler_manager


def set_scheduler(scheduler: SchedulerManager):
    """Set the global scheduler instance"""
    global _scheduler_manager
    _scheduler_manager = scheduler
