"""Admin endpoints for user and namespace permission management"""

import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.auth.keycloak import get_current_user, require_admin
from app.models.user_namespace import UserNamespace
from app.schemas.user import UserInfo, UserNamespaceCreate, UserNamespaceResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/users/namespaces", response_model=UserNamespaceResponse)
async def grant_namespace_access(
    permission: UserNamespaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(require_admin)
):
    """
    Grant user access to a namespace
    
    Args:
        permission: User namespace permission to create
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        UserNamespaceResponse: Created permission
    """
    # Check if already exists
    result = await db.execute(
        select(UserNamespace).where(
            UserNamespace.user_id == permission.user_id,
            UserNamespace.namespace == permission.namespace
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Re-enable if was revoked
        existing.enabled = True
        existing.granted_by = current_user.sub
        existing.granted_at = datetime.utcnow()
        existing.revoked_at = None
        await db.commit()
        await db.refresh(existing)
        logger.info(f"Re-enabled namespace access: {permission.user_id} -> {permission.namespace}")
        return existing
    else:
        # Create new permission
        new_permission = UserNamespace(
            user_id=permission.user_id,
            namespace=permission.namespace,
            granted_by=current_user.sub
        )
        db.add(new_permission)
        await db.commit()
        await db.refresh(new_permission)
        logger.info(f"Granted namespace access: {permission.user_id} -> {permission.namespace}")
        return new_permission


@router.delete("/users/{user_id}/namespaces/{namespace}")
async def revoke_namespace_access(
    user_id: str,
    namespace: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(require_admin)
):
    """
    Revoke user access to a namespace
    
    Args:
        user_id: User ID (Keycloak sub)
        namespace: Namespace name
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        dict: Success message
    """
    result = await db.execute(
        select(UserNamespace).where(
            UserNamespace.user_id == user_id,
            UserNamespace.namespace == namespace
        )
    )
    permission = result.scalar_one_or_none()
    
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    permission.enabled = False
    permission.revoked_at = datetime.utcnow()
    await db.commit()
    
    logger.info(f"Revoked namespace access: {user_id} -> {namespace}")
    return {"message": "Access revoked successfully"}


@router.get("/users/{user_id}/namespaces", response_model=List[str])
async def list_user_namespaces(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(require_admin)
):
    """
    List namespaces accessible to a user
    
    Args:
        user_id: User ID (Keycloak sub)
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        List[str]: List of namespace names
    """
    result = await db.execute(
        select(UserNamespace.namespace).where(
            UserNamespace.user_id == user_id,
            UserNamespace.enabled == True
        )
    )
    namespaces = [row[0] for row in result.all()]
    
    logger.info(f"Listed namespaces for user {user_id}: {len(namespaces)} found")
    return namespaces


@router.get("/users/namespaces", response_model=List[UserNamespaceResponse])
async def list_all_user_namespaces(
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(require_admin)
):
    """
    List all user-namespace permissions
    
    Args:
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        List[UserNamespaceResponse]: All permissions
    """
    result = await db.execute(
        select(UserNamespace).where(UserNamespace.enabled == True)
    )
    permissions = result.scalars().all()
    
    logger.info(f"Listed all user-namespace permissions: {len(permissions)} found")
    return permissions


@router.get("/namespaces/{namespace}/users", response_model=List[str])
async def list_namespace_users(
    namespace: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(require_admin)
):
    """
    List users who have access to a namespace
    
    Args:
        namespace: Namespace name
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        List[str]: List of user IDs
    """
    result = await db.execute(
        select(UserNamespace.user_id).where(
            UserNamespace.namespace == namespace,
            UserNamespace.enabled == True
        )
    )
    user_ids = [row[0] for row in result.all()]
    
    logger.info(f"Listed users for namespace {namespace}: {len(user_ids)} found")
    return user_ids
