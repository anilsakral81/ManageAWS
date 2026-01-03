"""Tenant management endpoints"""

from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.auth.keycloak import get_current_user
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantScaleRequest,
)
from app.schemas.user import UserInfo
from app.services.tenant_service import TenantService

router = APIRouter()


class ExecCommandRequest(BaseModel):
    """Request schema for exec command"""
    command: List[str]
    container: Optional[str] = None


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> List[TenantResponse]:
    """
    List all tenants accessible to the current user
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[TenantResponse]: List of tenants
    """
    service = TenantService(db)
    tenants = await service.list_tenants(
        user=current_user,
        skip=skip,
        limit=limit,
    )
    return tenants


@router.get("/{namespace}", response_model=TenantResponse)
async def get_tenant(
    namespace: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> TenantResponse:
    """
    Get tenant by namespace
    
    Args:
        namespace: Kubernetes namespace
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Tenant details
    """
    service = TenantService(db)
    tenant = await service.get_tenant(
        namespace=namespace,
        user=current_user,
    )
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Namespace {namespace} not found",
        )
    return tenant


@router.post("/{namespace}/start", response_model=TenantResponse)
async def start_tenant(
    namespace: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> TenantResponse:
    """
    Start tenant (scale all deployments to 1 replica)
    
    Args:
        namespace: Kubernetes namespace
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Updated tenant
    """
    service = TenantService(db)
    return await service.start_tenant(
        namespace=namespace,
        user_id=current_user.sub,
    )


@router.post("/{namespace}/stop", response_model=TenantResponse)
async def stop_tenant(
    namespace: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> TenantResponse:
    """
    Stop tenant (scale all deployments to 0 replicas)
    
    Args:
        namespace: Kubernetes namespace
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Updated tenant
    """
    service = TenantService(db)
    return await service.stop_tenant(
        namespace=namespace,
        user_id=current_user.sub,
    )


@router.post("/{namespace}/scale", response_model=TenantResponse)
async def scale_tenant(
    namespace: str,
    scale_request: TenantScaleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> TenantResponse:
    """
    Scale all deployments in tenant namespace to specific replica count
    
    Args:
        namespace: Kubernetes namespace
        scale_request: Scale request with target replicas
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Updated tenant
    """
    service = TenantService(db)
    return await service.scale_tenant(
        namespace=namespace,
        replicas=scale_request.replicas,
        user_id=current_user.sub,
    )


@router.get("/{namespace}/pods", response_model=List[Dict])
async def get_tenant_pods(
    namespace: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> List[Dict]:
    """
    Get all pods in tenant namespace
    
    Args:
        namespace: Kubernetes namespace
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[Dict]: List of pods with status
    """
    service = TenantService(db)
    return await service.get_tenant_pods(
        namespace=namespace,
        user_id=current_user.sub,
    )


@router.get("/{namespace}/pods/{pod_name}/containers", response_model=List[Dict])
async def get_pod_containers(
    namespace: str,
    pod_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> List[Dict]:
    """
    Get all containers in a pod
    
    Args:
        namespace: Kubernetes namespace
        pod_name: Pod name
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[Dict]: List of containers
    """
    service = TenantService(db)
    return await service.get_pod_containers(namespace=namespace, pod_name=pod_name)


@router.get("/{namespace}/pods/{pod_name}/logs")
async def get_pod_logs(
    namespace: str,
    pod_name: str,
    container: str = None,
    tail_lines: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> Dict:
    """
    Get logs from a pod container
    
    Args:
        namespace: Kubernetes namespace
        pod_name: Pod name
        container: Container name (optional)
        tail_lines: Number of lines to retrieve
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dict: Pod logs
    """
    service = TenantService(db)
    logs = await service.get_pod_logs(
        namespace=namespace,
        pod_name=pod_name,
        container=container,
        tail_lines=tail_lines
    )
    return {"logs": logs, "pod": pod_name, "container": container}


@router.post("/{namespace}/pods/{pod_name}/exec")
async def exec_pod_command(
    namespace: str,
    pod_name: str,
    exec_request: ExecCommandRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> Dict:
    """
    Execute a command in a pod container
    
    Args:
        namespace: Kubernetes namespace
        pod_name: Pod name
        exec_request: Exec request with command and optional container
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dict: Command output
    """
    service = TenantService(db)
    return await service.exec_pod_command(
        namespace=namespace,
        pod_name=pod_name,
        command=exec_request.command,
        container=exec_request.container
    )
