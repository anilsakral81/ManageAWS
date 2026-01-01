"""Tenant service for business logic"""

import logging
from typing import List, Optional, Dict
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.tenant import Tenant, TenantStatus
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.services.k8s_client import get_k8s_client

logger = logging.getLogger(__name__)


class TenantService:
    """Service for tenant management operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.k8s_client = get_k8s_client()
    
    async def list_tenants(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[TenantResponse]:
        """List all tenants accessible to user"""
        # TODO: Add permission filtering based on user_permissions table
        result = await self.db.execute(
            select(Tenant)
            .offset(skip)
            .limit(limit)
        )
        tenants = result.scalars().all()
        return [TenantResponse.model_validate(t) for t in tenants]
    
    async def get_tenant(
        self,
        tenant_id: int,
        user_id: str
    ) -> Optional[TenantResponse]:
        """Get tenant by ID"""
        # TODO: Check user permissions
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        return TenantResponse.model_validate(tenant) if tenant else None
    
    async def create_tenant(
        self,
        tenant: TenantCreate,
        user_id: str
    ) -> TenantResponse:
        """Create a new tenant"""
        # Verify namespace and deployment exist in K8s
        if not await self.k8s_client.namespace_exists(tenant.namespace):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Namespace '{tenant.namespace}' does not exist"
            )
        
        if not await self.k8s_client.deployment_exists(
            tenant.deployment_name, tenant.namespace
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Deployment '{tenant.deployment_name}' not found in namespace '{tenant.namespace}'"
            )
        
        # Create tenant record
        db_tenant = Tenant(**tenant.model_dump())
        self.db.add(db_tenant)
        
        # Create audit log
        await self._create_audit_log(
            tenant_id=None,
            action=AuditAction.TENANT_CREATE,
            user_id=user_id,
            success=True,
            details={"tenant_name": tenant.name}
        )
        
        await self.db.commit()
        await self.db.refresh(db_tenant)
        
        return TenantResponse.model_validate(db_tenant)
    
    async def update_tenant(
        self,
        tenant_id: int,
        tenant_update: TenantUpdate,
        user_id: str
    ) -> TenantResponse:
        """Update tenant"""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found"
            )
        
        # Update fields
        update_data = tenant_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)
        
        await self._create_audit_log(
            tenant_id=tenant_id,
            action=AuditAction.TENANT_UPDATE,
            user_id=user_id,
            success=True,
            details=update_data
        )
        
        await self.db.commit()
        await self.db.refresh(tenant)
        
        return TenantResponse.model_validate(tenant)
    
    async def delete_tenant(self, tenant_id: int, user_id: str) -> None:
        """Delete tenant"""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found"
            )
        
        await self._create_audit_log(
            tenant_id=tenant_id,
            action=AuditAction.TENANT_DELETE,
            user_id=user_id,
            success=True,
            details={"tenant_name": tenant.name}
        )
        
        await self.db.delete(tenant)
        await self.db.commit()
    
    async def start_tenant(self, tenant_id: int, user_id: str) -> TenantResponse:
        """Start tenant (scale to desired replicas)"""
        return await self.scale_tenant(
            tenant_id=tenant_id,
            replicas=None,  # Use desired_replicas
            user_id=user_id
        )
    
    async def stop_tenant(self, tenant_id: int, user_id: str) -> TenantResponse:
        """Stop tenant (scale to 0)"""
        return await self.scale_tenant(
            tenant_id=tenant_id,
            replicas=0,
            user_id=user_id
        )
    
    async def scale_tenant(
        self,
        tenant_id: int,
        replicas: Optional[int],
        user_id: str
    ) -> TenantResponse:
        """Scale tenant to specific replica count"""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found"
            )
        
        # Use desired_replicas if replicas not specified
        target_replicas = replicas if replicas is not None else tenant.desired_replicas
        
        try:
            # Scale in Kubernetes
            tenant.status = TenantStatus.SCALING
            await self.db.commit()
            
            await self.k8s_client.scale_deployment(
                name=tenant.deployment_name,
                namespace=tenant.namespace,
                replicas=target_replicas
            )
            
            # Update tenant record
            tenant.current_replicas = target_replicas
            tenant.status = TenantStatus.RUNNING if target_replicas > 0 else TenantStatus.STOPPED
            tenant.last_scaled_at = datetime.utcnow()
            tenant.last_scaled_by = user_id
            
            action = AuditAction.TENANT_START if target_replicas > 0 else AuditAction.TENANT_STOP
            
            await self._create_audit_log(
                tenant_id=tenant_id,
                action=action,
                user_id=user_id,
                success=True,
                details={"replicas": target_replicas}
            )
            
            await self.db.commit()
            await self.db.refresh(tenant)
            
            return TenantResponse.model_validate(tenant)
            
        except Exception as e:
            tenant.status = TenantStatus.ERROR
            await self.db.commit()
            
            await self._create_audit_log(
                tenant_id=tenant_id,
                action=AuditAction.TENANT_SCALE,
                user_id=user_id,
                success=False,
                error_message=str(e),
                details={"target_replicas": target_replicas}
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to scale tenant: {str(e)}"
            )
    
    async def get_tenant_k8s_status(
        self,
        tenant_id: int,
        user_id: str
    ) -> Dict[str, str]:
        """Get real-time tenant status from Kubernetes"""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found"
            )
        
        deployment = await self.k8s_client.get_deployment(
            name=tenant.deployment_name,
            namespace=tenant.namespace
        )
        
        if not deployment:
            return {"status": "not_found", "message": "Deployment not found in Kubernetes"}
        
        return deployment
    
    async def _create_audit_log(
        self,
        action: AuditAction,
        user_id: str,
        tenant_id: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> None:
        """Create audit log entry"""
        audit_log = AuditLog(
            tenant_id=tenant_id,
            action=action,
            user_id=user_id,
            success=success,
            error_message=error_message,
            details=details
        )
        self.db.add(audit_log)
