"""Audit log endpoints"""

from typing import List, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.keycloak import get_current_user
from app.schemas.audit_log import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    tenant_id: int = None,
    user_id: str = None,
    action: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    skip: int = 0,
    limit: int = Query(default=100, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> List[AuditLogResponse]:
    """
    List audit logs with optional filters
    
    Args:
        tenant_id: Optional tenant ID filter
        user_id: Optional user ID filter
        action: Optional action type filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[AuditLogResponse]: List of audit logs
    """
    service = AuditService(db)
    return await service.list_audit_logs(
        requesting_user_id=current_user.get("sub"),
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
) -> AuditLogResponse:
    """
    Get audit log by ID
    
    Args:
        log_id: Audit log ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        AuditLogResponse: Audit log details
    """
    service = AuditService(db)
    return await service.get_audit_log(
        log_id=log_id,
        user_id=current_user.get("sub"),
    )
