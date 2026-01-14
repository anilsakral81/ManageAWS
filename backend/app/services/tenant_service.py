"""Tenant service for business logic"""

import logging
from typing import List, Optional, Dict
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.tenant import Tenant, TenantStatus
from app.models.audit_log import AuditLog, AuditAction
from app.models.tenant_state_history import TenantStateHistory, StateType
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.schemas.user import UserInfo
from app.services.k8s_client import get_k8s_client
from app.auth.keycloak import get_user_allowed_namespaces

logger = logging.getLogger(__name__)


class TenantService:
    """Service for tenant management operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.k8s_client = get_k8s_client()
    
    async def _check_namespace_access(
        self,
        namespace: str,
        user: UserInfo
    ) -> bool:
        """Check if user has access to namespace"""
        # Get allowed namespaces from database
        if not user.allowed_namespaces:
            user.allowed_namespaces = await get_user_allowed_namespaces(user, self.db)
        
        # Check if user has access (either wildcard or specific namespace)
        if "*" in user.allowed_namespaces:
            return True
        
        # Check specific namespace permission
        return namespace in user.allowed_namespaces
    
    async def list_tenants(
        self,
        user: UserInfo,
        skip: int = 0,
        limit: int = 100
    ) -> List[TenantResponse]:
        """List all tenants (namespaces) accessible to user"""
        # Get user's allowed namespaces
        allowed_namespaces = await get_user_allowed_namespaces(user, self.db)
        
        # Get all non-system namespaces from K8s
        all_namespaces = await self.k8s_client.list_namespaces(exclude_system=True)
        
        # Filter by user permissions
        if "*" not in allowed_namespaces:
            all_namespaces = [ns for ns in all_namespaces if ns in allowed_namespaces]
        
        # Get deployment info for each namespace
        tenants = []
        for namespace in all_namespaces[skip:skip+limit]:
            # Get deployments in this namespace
            deployments = await self.k8s_client.list_namespace_deployments(namespace)
            
            # Skip tenants with no deployments/statefulsets/daemonsets
            if not deployments:
                continue
            
            # Get VirtualService hosts
            virtualservices = await self.k8s_client.list_namespace_virtualservices(namespace)
            
            # Calculate aggregate status
            total_replicas = 0
            ready_replicas = 0
            has_stopped_resources = False
            
            for d in deployments:
                if d["type"] == "DaemonSet":
                    # DaemonSets are stopped if they have the stop selector
                    if d.get("is_stopped", False):
                        has_stopped_resources = True
                    else:
                        total_replicas += d.get("replicas", 0)
                        ready_replicas += d.get("ready_replicas", 0)
                else:
                    # Deployments and StatefulSets have normal replica counts
                    total_replicas += d.get("replicas", 0)
                    ready_replicas += d.get("ready_replicas", 0)
            
            # Determine status
            if not deployments:
                status = TenantStatus.UNKNOWN
            elif total_replicas == 0 or has_stopped_resources:
                status = TenantStatus.STOPPED
            elif ready_replicas == total_replicas:
                status = TenantStatus.RUNNING
            elif ready_replicas < total_replicas:
                status = TenantStatus.SCALING
            else:
                status = TenantStatus.UNKNOWN
            
            # Get metadata from database if exists
            result = await self.db.execute(
                select(Tenant).where(Tenant.namespace == namespace)
            )
            db_tenant = result.scalar_one_or_none()
            
            # Build response
            deployment_names = [d["name"] for d in deployments] if deployments else []
            deployment_count = len(deployment_names)
            
            tenant_data = {
                "id": db_tenant.id if db_tenant else hash(namespace) % 1000000,  # Use hash as fake ID
                "name": db_tenant.name if db_tenant else namespace,
                "namespace": namespace,
                "deployment_name": f"{deployment_count} deployment(s)" if deployments else "none",
                "description": db_tenant.description if db_tenant else f"Namespace: {namespace} ({deployment_count} deployments)",
                "status": status,
                "current_replicas": ready_replicas,
                "desired_replicas": total_replicas,
                "enabled": db_tenant.enabled if db_tenant else True,
                "created_at": db_tenant.created_at if db_tenant else datetime.utcnow(),
                "updated_at": db_tenant.updated_at if db_tenant else datetime.utcnow(),
                "last_scaled_at": db_tenant.last_scaled_at if db_tenant else None,
                "last_scaled_by": db_tenant.last_scaled_by if db_tenant else None,
                "virtualservices": virtualservices,
            }
            
            tenants.append(TenantResponse(**tenant_data))
        
        return tenants
    
    async def get_tenant(
        self,
        namespace: str,
        user: UserInfo
    ) -> Optional[TenantResponse]:
        """Get tenant by namespace"""
        # Check access
        if not await self._check_namespace_access(namespace, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to namespace '{namespace}'"
            )
        
        # Check if namespace exists in K8s
        if not await self.k8s_client.namespace_exists(namespace):
            return None
        
        # Get deployments in this namespace
        deployments = await self.k8s_client.list_namespace_deployments(namespace)
        
        # Get VirtualService hosts
        virtualservices = await self.k8s_client.list_namespace_virtualservices(namespace)
        
        # Calculate status
        total_replicas = sum(d.get("replicas", 0) for d in deployments)
        ready_replicas = sum(d.get("ready_replicas", 0) for d in deployments)
        
        if not deployments:
            status = TenantStatus.UNKNOWN
        elif total_replicas == 0:
            status = TenantStatus.STOPPED
        elif ready_replicas == total_replicas:
            status = TenantStatus.RUNNING
        else:
            status = TenantStatus.SCALING
        
        # Get metadata from database if exists
        result = await self.db.execute(
            select(Tenant).where(Tenant.namespace == namespace)
        )
        db_tenant = result.scalar_one_or_none()
        
        deployment_count = len(deployments)
        
        tenant_data = {
            "id": db_tenant.id if db_tenant else hash(namespace) % 1000000,
            "name": db_tenant.name if db_tenant else namespace,
            "namespace": namespace,
            "deployment_name": f"{deployment_count} deployment(s)" if deployments else "none",
            "description": db_tenant.description if db_tenant else f"Namespace: {namespace} ({deployment_count} deployments)",
            "status": status,
            "current_replicas": ready_replicas,
            "desired_replicas": total_replicas,
            "enabled": db_tenant.enabled if db_tenant else True,
            "created_at": db_tenant.created_at if db_tenant else datetime.utcnow(),
            "updated_at": db_tenant.updated_at if db_tenant else datetime.utcnow(),
            "last_scaled_at": db_tenant.last_scaled_at if db_tenant else None,
            "last_scaled_by": db_tenant.last_scaled_by if db_tenant else None,
            "virtualservices": virtualservices,
        }
        
        return TenantResponse(**tenant_data)
    
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
    
    async def start_tenant(self, namespace: str, user: UserInfo, ip_address: Optional[str] = None) -> TenantResponse:
        """Start tenant (scale all deployments to 1)"""
        return await self.scale_tenant(
            namespace=namespace,
            replicas=1,
            user=user,
            ip_address=ip_address
        )
    
    async def stop_tenant(self, namespace: str, user: UserInfo, ip_address: Optional[str] = None) -> TenantResponse:
        """Stop tenant (scale all deployments to 0)"""
        return await self.scale_tenant(
            namespace=namespace,
            replicas=0,
            user=user,
            ip_address=ip_address
        )
    
    async def scale_tenant(
        self,
        namespace: str,
        replicas: int,
        user: UserInfo,
        ip_address: Optional[str] = None
    ) -> TenantResponse:
        """Scale all deployments in tenant namespace"""
        # Check if namespace exists
        if not await self.k8s_client.namespace_exists(namespace):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Namespace '{namespace}' not found"
            )
        
        try:
            # Scale all deployments in namespace
            scale_result = await self.k8s_client.scale_namespace(
                namespace=namespace,
                replicas=replicas
            )
            
            # Update or create database record for tracking
            result = await self.db.execute(
                select(Tenant).where(Tenant.namespace == namespace)
            )
            db_tenant = result.scalar_one_or_none()
            
            # Track previous replicas for state history
            previous_replicas = None
            
            if not db_tenant:
                # Create minimal tenant record for tracking
                resource_names = [r["resource"] for r in scale_result["results"]]
                resource_count = len(resource_names)
                
                db_tenant = Tenant(
                    name=namespace,
                    namespace=namespace,
                    deployment_name=f"{resource_count} resource(s)",
                    description=f"Auto-created for namespace {namespace}",
                )
                self.db.add(db_tenant)
                await self.db.flush()  # Get tenant ID for state history
            else:
                previous_replicas = db_tenant.current_replicas
            
            db_tenant.last_scaled_at = datetime.utcnow()
            db_tenant.last_scaled_by = user.sub
            
            # Record state change in history
            await self._record_state_change(
                tenant_id=db_tenant.id,
                previous_replicas=previous_replicas,
                new_replicas=replicas,
                changed_by=user.sub,
                reason=f"Scale to {replicas} replicas"
            )
            
            await self._create_audit_log(
                tenant_id=db_tenant.id if db_tenant.id else None,
                action=AuditAction.TENANT_SCALE if replicas > 0 else AuditAction.TENANT_STOP if replicas == 0 else AuditAction.TENANT_START,
                user_id=user.sub,
                ip_address=ip_address,
                success=True,
                details={"namespace": namespace, "replicas": replicas, "result": scale_result}
            )
            
            await self.db.commit()
            if db_tenant:
                await self.db.refresh(db_tenant)
            
            # Return updated tenant info
            return await self.get_tenant(namespace=namespace, user=user)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error scaling tenant {namespace}: {e}")
            await self._create_audit_log(
                tenant_id=None,
                action=AuditAction.TENANT_SCALE,
                user_id=user.sub,
                ip_address=ip_address,
                success=False,
                details={"namespace": namespace, "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to scale tenant: {str(e)}"
            )

    async def get_tenant_pods(
        self,
        namespace: str,
        user_id: str
    ) -> list[Dict]:
        """Get all pods in tenant namespace"""
        # Check if namespace exists
        if not await self.k8s_client.namespace_exists(namespace):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Namespace '{namespace}' not found"
            )
        
        return await self.k8s_client.list_namespace_pods(namespace)
    
    async def get_pod_logs(
        self,
        namespace: str,
        pod_name: str,
        container: Optional[str] = None,
        tail_lines: int = 100
    ) -> str:
        """Get logs from a specific pod"""
        return await self.k8s_client.get_pod_logs(pod_name, namespace, container, tail_lines)
    
    async def get_pod_containers(
        self,
        namespace: str,
        pod_name: str
    ) -> list[Dict]:
        """Get list of containers in a pod"""
        return await self.k8s_client.list_pod_containers(pod_name, namespace)
    
    async def exec_pod_command(
        self,
        namespace: str,
        pod_name: str,
        command: list[str],
        container: Optional[str] = None
    ) -> Dict:
        """Execute a command in a pod container"""
        return await self.k8s_client.exec_pod_command(pod_name, namespace, command, container)

    def _tenant_status_to_state_type(self, status: TenantStatus, replicas: int) -> StateType:
        """Convert TenantStatus to StateType for state history tracking"""
        if status == TenantStatus.STOPPED or replicas == 0:
            return StateType.STOPPED
        elif status == TenantStatus.RUNNING:
            return StateType.RUNNING
        elif status == TenantStatus.SCALING:
            # Scaling state is also considered "running" for uptime tracking
            return StateType.SCALING
        else:
            return StateType.UNKNOWN

    async def _record_state_change(
        self,
        tenant_id: int,
        previous_replicas: Optional[int],
        new_replicas: int,
        changed_by: str,
        reason: str = "Manual scaling"
    ) -> None:
        """Record state change in history"""
        # Get previous state if there's a previous record
        previous_state = None
        if previous_replicas is not None:
            if previous_replicas == 0:
                previous_state = StateType.STOPPED
            else:
                previous_state = StateType.RUNNING
        
        # Determine new state
        if new_replicas == 0:
            new_state = StateType.STOPPED
        else:
            # Check if any pods are not ready yet (scaling state)
            # For now, we'll consider it RUNNING when replicas > 0
            # The frontend can filter for "upscaling" by checking SCALING state
            new_state = StateType.RUNNING
        
        # Only record if state actually changed or if it's the first record
        if previous_state != new_state or previous_state is None:
            state_history = TenantStateHistory(
                tenant_id=tenant_id,
                previous_state=previous_state,
                new_state=new_state,
                previous_replicas=previous_replicas,
                new_replicas=new_replicas,
                changed_at=datetime.utcnow(),
                changed_by=changed_by,
                reason=reason
            )
            self.db.add(state_history)

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
        
        # Use 'System' for scheduler instead of fetching from Keycloak
        if user_id == "scheduler":
            user_name = "System"
        else:
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
