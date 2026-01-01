"""Tenant management endpoints"""

from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.keycloak import get_current_user
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantScaleRequest,
)
from app.services.tenant_service import TenantService

router = APIRouter()


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
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
        user_id=current_user.get("sub"),
        skip=skip,
        limit=limit,
    )
    return tenants


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant: TenantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> TenantResponse:
    """
    Create a new tenant
    
    Args:
        tenant: Tenant creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Created tenant
    """
    service = TenantService(db)
    return await service.create_tenant(
        tenant=tenant,
        user_id=current_user.get("sub"),
    )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> TenantResponse:
    """
    Get tenant by ID
    
    Args:
        tenant_id: Tenant ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Tenant details
    """
    service = TenantService(db)
    tenant = await service.get_tenant(
        tenant_id=tenant_id,
        user_id=current_user.get("sub"),
    )
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )
    return tenant


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    tenant_update: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> TenantResponse:
    """
    Update tenant
    
    Args:
        tenant_id: Tenant ID
        tenant_update: Tenant update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Updated tenant
    """
    service = TenantService(db)
    return await service.update_tenant(
        tenant_id=tenant_id,
        tenant_update=tenant_update,
        user_id=current_user.get("sub"),
    )


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> None:
    """
    Delete tenant
    
    Args:
        tenant_id: Tenant ID
        db: Database session
        current_user: Current authenticated user
    """
    service = TenantService(db)
    await service.delete_tenant(
        tenant_id=tenant_id,
        user_id=current_user.get("sub"),
    )


@router.post("/{tenant_id}/start", response_model=TenantResponse)
async def start_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> TenantResponse:
    """
    Start tenant (scale to desired replicas)
    
    Args:
        tenant_id: Tenant ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Updated tenant
    """
    service = TenantService(db)
    return await service.start_tenant(
        tenant_id=tenant_id,
        user_id=current_user.get("sub"),
    )


@router.post("/{tenant_id}/stop", response_model=TenantResponse)
async def stop_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> TenantResponse:
    """
    Stop tenant (scale to 0 replicas)
    
    Args:
        tenant_id: Tenant ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Updated tenant
    """
    service = TenantService(db)
    return await service.stop_tenant(
        tenant_id=tenant_id,
        user_id=current_user.get("sub"),
    )


@router.post("/{tenant_id}/scale", response_model=TenantResponse)
async def scale_tenant(
    tenant_id: int,
    scale_request: TenantScaleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> TenantResponse:
    """
    Scale tenant to specific replica count
    
    Args:
        tenant_id: Tenant ID
        scale_request: Scale request with target replicas
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        TenantResponse: Updated tenant
    """
    service = TenantService(db)
    return await service.scale_tenant(
        tenant_id=tenant_id,
        replicas=scale_request.replicas,
        user_id=current_user.get("sub"),
    )


@router.get("/{tenant_id}/status", response_model=Dict[str, str])
async def get_tenant_status(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Get real-time tenant status from Kubernetes
    
    Args:
        tenant_id: Tenant ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dict: Tenant status information
    """
    service = TenantService(db)
    return await service.get_tenant_k8s_status(
        tenant_id=tenant_id,
        user_id=current_user.get("sub"),
    )
