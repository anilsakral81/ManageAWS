"""Audit service - Placeholder for implementation"""

import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.tenant import Tenant
from app.schemas.audit_log import AuditLogResponse

logger = logging.getLogger(__name__)


class AuditService:
    """Service for audit log operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def list_audit_logs(
        self,
        requesting_user_id: str,
        tenant_id: Optional[int] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLogResponse]:
        """List audit logs with filters"""
        query = select(AuditLog)
        
        if tenant_id:
            query = query.where(AuditLog.tenant_id == tenant_id)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        query = query.order_by(AuditLog.created_at.desc())
        result = await self.db.execute(query.offset(skip).limit(limit))
        logs = result.scalars().all()
        
        # Get tenant names for all logs
        tenant_ids = {log.tenant_id for log in logs if log.tenant_id}
        tenant_names = {}
        if tenant_ids:
            tenant_result = await self.db.execute(
                select(Tenant.id, Tenant.name).where(Tenant.id.in_(tenant_ids))
            )
            tenant_names = {tid: tname for tid, tname in tenant_result.all()}
        
        # Fetch user names from Keycloak for logs missing user_name
        await self._backfill_user_names(logs)
        
        # Convert to response objects
        responses = []
        for log in logs:
            response = AuditLogResponse.from_audit_log(log)
            if log.tenant_id and log.tenant_id in tenant_names:
                response.tenant_name = tenant_names[log.tenant_id]
            responses.append(response)
        
        return responses
    
    async def _backfill_user_names(self, logs: List[AuditLog]) -> None:
        """Fetch user names from Keycloak for logs missing user_name"""
        import httpx
        from app.config import settings
        
        # Find logs that need user names
        logs_needing_names = [log for log in logs if not log.user_name and log.user_id and log.user_id != "scheduler"]
        
        if not logs_needing_names:
            return
        
        try:
            async with httpx.AsyncClient() as client:
                # Get admin token
                token_response = await client.post(
                    f"{settings.keycloak_url}/realms/master/protocol/openid-connect/token",
                    data={
                        "username": settings.keycloak_admin_username,
                        "password": settings.keycloak_admin_password,
                        "grant_type": "password",
                        "client_id": "admin-cli",
                    },
                )
                
                if token_response.status_code != 200:
                    logger.warning("Failed to get Keycloak admin token for user name backfill")
                    return
                
                access_token = token_response.json()["access_token"]
                
                # Fetch user names for each unique user_id
                user_ids_to_fetch = {log.user_id for log in logs_needing_names}
                user_names_cache = {}
                
                for user_id in user_ids_to_fetch:
                    try:
                        user_response = await client.get(
                            f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/users/{user_id}",
                            headers={"Authorization": f"Bearer {access_token}"},
                        )
                        
                        if user_response.status_code == 200:
                            user_data = user_response.json()
                            first_name = user_data.get("firstName", "")
                            last_name = user_data.get("lastName", "")
                            user_name = f"{first_name} {last_name}".strip() or user_data.get("email", user_data.get("username", ""))
                            user_names_cache[user_id] = user_name
                        else:
                            logger.debug(f"User {user_id} not found in Keycloak")
                    except Exception as e:
                        logger.debug(f"Error fetching user {user_id}: {e}")
                        continue
                
                # Update logs with fetched names
                for log in logs_needing_names:
                    if log.user_id in user_names_cache:
                        log.user_name = user_names_cache[log.user_id]
                        
        except Exception as e:
            logger.warning(f"Error backfilling user names: {e}")
    
    async def get_audit_log(self, log_id: int, user_id: str) -> AuditLogResponse:
        """Get audit log by ID"""
        result = await self.db.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        
        response = AuditLogResponse.from_audit_log(log)
        
        # Get tenant name if tenant_id exists
        if log.tenant_id:
            tenant_result = await self.db.execute(
                select(Tenant.name).where(Tenant.id == log.tenant_id)
            )
            tenant_name = tenant_result.scalar_one_or_none()
            if tenant_name:
                response.tenant_name = tenant_name
        
        return response
