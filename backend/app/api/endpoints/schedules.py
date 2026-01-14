"""Schedule management endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.keycloak import get_current_user, require_operator
from app.schemas.user import UserInfo
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
)
from app.services.schedule_service import ScheduleService

router = APIRouter()


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    tenant_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> List[ScheduleResponse]:
    """
    List schedules, optionally filtered by tenant
    
    Args:
        tenant_id: Optional tenant ID to filter by
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[ScheduleResponse]: List of schedules
    """
    service = ScheduleService(db)
    return await service.list_schedules(
        user_id=current_user.sub,
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule: ScheduleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(require_operator),
) -> ScheduleResponse:
    """
    Create a new schedule
    
    Args:
        schedule: Schedule creation data
        request: HTTP request object
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        ScheduleResponse: Created schedule
    """
    service = ScheduleService(db)
    return await service.create_schedule(
        schedule=schedule,
        user_id=current_user.sub,
        ip_address=request.client.host if request.client else None,
    )


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> ScheduleResponse:
    """
    Get schedule by ID
    
    Args:
        schedule_id: Schedule ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        ScheduleResponse: Schedule details
    """
    service = ScheduleService(db)
    schedule = await service.get_schedule(
        schedule_id=schedule_id,
        user_id=current_user.sub,
    )
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule {schedule_id} not found",
        )
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_update: ScheduleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> ScheduleResponse:
    """
    Update schedule
    
    Args:
        schedule_id: Schedule ID
        schedule_update: Schedule update data
        request: HTTP request object
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        ScheduleResponse: Updated schedule
    """
    service = ScheduleService(db)
    return await service.update_schedule(
        schedule_id=schedule_id,
        schedule_update=schedule_update,
        user_id=current_user.sub,
        ip_address=request.client.host if request.client else None,
    )


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(require_operator),
) -> None:
    """
    Delete schedule
    
    Args:
        schedule_id: Schedule ID
        request: HTTP request object
        db: Database session
        current_user: Current authenticated user
    """
    service = ScheduleService(db)
    await service.delete_schedule(
        schedule_id=schedule_id,
        user_id=current_user.sub,
        ip_address=request.client.host if request.client else None,
    )
