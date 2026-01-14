"""Tenant management endpoints"""

from typing import List, Dict, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.auth.keycloak import get_current_user, require_operator
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantScaleRequest,
)
from app.schemas.metrics import (
    CurrentStateDuration,
    MonthlyMetrics,
    StateHistoryRecord,
    TenantMetrics,
)
from app.schemas.user import UserInfo
from app.services.tenant_service import TenantService
from app.services.metrics_service import MetricsService

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
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(require_operator),
) -> TenantResponse:
    """
    Start tenant (scale all deployments to 1 replica)
    
    Args:
        namespace: Kubernetes namespace
        request: HTTP request object
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Updated tenant
    """
    service = TenantService(db)
    return await service.start_tenant(
        namespace=namespace,
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )


@router.post("/{namespace}/stop", response_model=TenantResponse)
async def stop_tenant(
    namespace: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(require_operator),
) -> TenantResponse:
    """
    Stop tenant (scale all deployments to 0 replicas)
    
    Args:
        namespace: Kubernetes namespace
        request: HTTP request object
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Updated tenant
    """
    service = TenantService(db)
    return await service.stop_tenant(
        namespace=namespace,
        user=current_user,
        ip_address=request.client.host if request.client else None,
    )


@router.post("/{namespace}/scale", response_model=TenantResponse)
async def scale_tenant(
    namespace: str,
    scale_request: TenantScaleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(require_operator),
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


# Metrics endpoints

@router.get("/{namespace}/metrics/current-state", response_model=CurrentStateDuration)
async def get_current_state_duration(
    namespace: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> CurrentStateDuration:
    """
    Get how long the tenant has been in its current state
    
    Args:
        namespace: Kubernetes namespace
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        CurrentStateDuration: Current state and duration information
    """
    from app.models.tenant import Tenant
    from sqlalchemy import select
    
    # Get tenant by namespace
    result = await db.execute(
        select(Tenant).where(Tenant.namespace == namespace)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with namespace '{namespace}' not found"
        )
    
    metrics_service = MetricsService(db)
    current_state = await metrics_service.get_current_state_duration(tenant.id)
    
    return CurrentStateDuration(**current_state)


@router.get("/{namespace}/metrics/monthly", response_model=MonthlyMetrics)
async def get_monthly_metrics(
    namespace: str,
    year: Optional[int] = Query(None, description="Year (default: current year)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month 1-12 (default: current month)"),
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> MonthlyMetrics:
    """
    Get monthly uptime/downtime metrics for a tenant
    
    Args:
        namespace: Kubernetes namespace
        year: Year (default: current year)
        month: Month 1-12 (default: current month)
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        MonthlyMetrics: Monthly uptime/downtime statistics
    """
    from app.models.tenant import Tenant
    from sqlalchemy import select
    
    # Get tenant by namespace
    result = await db.execute(
        select(Tenant).where(Tenant.namespace == namespace)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with namespace '{namespace}' not found"
        )
    
    # Use current year/month if not provided
    now = datetime.utcnow()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    
    metrics_service = MetricsService(db)
    monthly_metrics = await metrics_service.get_monthly_uptime_downtime(
        tenant_id=tenant.id,
        year=year,
        month=month
    )
    
    return MonthlyMetrics(**monthly_metrics)


@router.get("/{namespace}/metrics/history", response_model=List[StateHistoryRecord])
async def get_state_history(
    namespace: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> List[StateHistoryRecord]:
    """
    Get state change history for a tenant
    
    Args:
        namespace: Kubernetes namespace
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[StateHistoryRecord]: List of state changes
    """
    from app.models.tenant import Tenant
    from sqlalchemy import select
    
    # Get tenant by namespace
    result = await db.execute(
        select(Tenant).where(Tenant.namespace == namespace)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with namespace '{namespace}' not found"
        )
    
    metrics_service = MetricsService(db)
    history = await metrics_service.get_state_history(
        tenant_id=tenant.id,
        limit=limit
    )
    
    return [StateHistoryRecord(**record) for record in history]


@router.get("/{namespace}/metrics", response_model=TenantMetrics)
async def get_tenant_metrics(
    namespace: str,
    include_monthly: bool = Query(True, description="Include current month metrics"),
    include_history: bool = Query(True, description="Include recent state history"),
    history_limit: int = Query(10, ge=1, le=100, description="Number of history records"),
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> TenantMetrics:
    """
    Get comprehensive metrics for a tenant
    
    Args:
        namespace: Kubernetes namespace
        include_monthly: Whether to include monthly metrics
        include_history: Whether to include recent history
        history_limit: Number of history records to include
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantMetrics: Comprehensive tenant metrics
    """
    from app.models.tenant import Tenant
    from sqlalchemy import select
    
    # Get tenant by namespace
    result = await db.execute(
        select(Tenant).where(Tenant.namespace == namespace)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with namespace '{namespace}' not found"
        )
    
    metrics_service = MetricsService(db)
    
    # Get current state
    current_state = await metrics_service.get_current_state_duration(tenant.id)
    
    # Get monthly metrics if requested
    monthly_metrics = None
    if include_monthly:
        now = datetime.utcnow()
        monthly_data = await metrics_service.get_monthly_uptime_downtime(
            tenant_id=tenant.id,
            year=now.year,
            month=now.month
        )
        monthly_metrics = MonthlyMetrics(**monthly_data)
    
    # Get recent history if requested
    recent_history = []
    if include_history:
        history_data = await metrics_service.get_state_history(
            tenant_id=tenant.id,
            limit=history_limit
        )
        recent_history = [StateHistoryRecord(**record) for record in history_data]
    
    return TenantMetrics(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        namespace=tenant.namespace,
        current_state=CurrentStateDuration(**current_state),
        monthly_metrics=monthly_metrics,
        recent_history=recent_history
    )
