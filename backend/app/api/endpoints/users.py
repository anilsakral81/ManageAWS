"""Admin endpoints for user and namespace permission management"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import httpx

from app.database import get_db
from app.auth.keycloak import get_current_user, require_admin, get_keycloak_openid
from app.models.user_namespace import UserNamespace
from app.schemas.user import (
    UserInfo, 
    UserNamespaceCreate, 
    UserNamespaceResponse, 
    UserCreate, 
    UserUpdate,
    PasswordReset
)
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/users/me", response_model=Dict[str, Any])
async def get_current_user_details(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get current authenticated user's details from token
    
    Args:
        current_user: Current authenticated user from JWT token
        
    Returns:
        Dict: User details including ID, email, username, name, and roles
    """
    user_details = {
        "id": current_user.sub,
        "email": current_user.email,
        "username": current_user.username,
        "name": current_user.name,
        "roles": current_user.roles,
    }
    
    logger.info(f"Retrieved current user details: {current_user.sub}")
    return user_details


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
    current_user: UserInfo = Depends(get_current_user)
):
    """
    List user-namespace permissions
    - Admins see all permissions
    - Operators/Viewers see only their own permissions
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List[UserNamespaceResponse]: Permissions (all for admin, own for others)
    """
    # Admin sees all permissions
    if "admin" in current_user.roles:
        result = await db.execute(
            select(UserNamespace).where(UserNamespace.enabled == True)
        )
        permissions = result.scalars().all()
        logger.info(f"Admin listed all user-namespace permissions: {len(permissions)} found")
    else:
        # Non-admin users see only their own permissions
        result = await db.execute(
            select(UserNamespace).where(
                UserNamespace.user_id == current_user.sub,
                UserNamespace.enabled == True
            )
        )
        permissions = result.scalars().all()
        logger.info(f"User {current_user.sub} listed own permissions: {len(permissions)} found")
    
    # Fetch granter details from Keycloak for each unique granted_by user
    granter_ids = {p.granted_by for p in permissions if p.granted_by}
    granter_details = {}
    
    if granter_ids:
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
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if token_response.status_code == 200:
                    admin_token = token_response.json()["access_token"]
                    
                    # Fetch details for each granter
                    for granter_id in granter_ids:
                        try:
                            user_response = await client.get(
                                f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/users/{granter_id}",
                                headers={"Authorization": f"Bearer {admin_token}"}
                            )
                            
                            if user_response.status_code == 200:
                                user_data = user_response.json()
                                granter_details[granter_id] = {
                                    "email": user_data.get("email", ""),
                                    "name": f"{user_data.get('firstName', '')} {user_data.get('lastName', '')}".strip() or user_data.get("username", "")
                                }
                        except Exception as e:
                            logger.warning(f"Could not fetch details for granter {granter_id}: {e}")
        except Exception as e:
            logger.warning(f"Could not fetch granter details: {e}")
    
    # Build response with granter details
    response_permissions = []
    for perm in permissions:
        perm_dict = {
            "user_id": perm.user_id,
            "namespace": perm.namespace,
            "enabled": perm.enabled,
            "granted_by": perm.granted_by,
            "granted_at": perm.granted_at,
        }
        
        # Add granter details if available
        if perm.granted_by and perm.granted_by in granter_details:
            perm_dict["granted_by_email"] = granter_details[perm.granted_by]["email"]
            perm_dict["granted_by_name"] = granter_details[perm.granted_by]["name"]
        
        response_permissions.append(perm_dict)
    
    return response_permissions


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


@router.get("/keycloak/users", response_model=List[Dict[str, Any]])
async def list_keycloak_users(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    List users from Keycloak realm
    - Admins see all users
    - Operators/Viewers see only themselves
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List[Dict]: List of users with id, username, email, firstName, lastName, roles
    """
    try:
        # Get admin token
        async with httpx.AsyncClient() as client:
            # Get admin access token
            token_response = await client.post(
                f"{settings.keycloak_url}/realms/master/protocol/openid-connect/token",
                data={
                    "username": settings.keycloak_admin_username,
                    "password": settings.keycloak_admin_password,
                    "grant_type": "password",
                    "client_id": "admin-cli"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                logger.error(f"Failed to get admin token: {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Could not authenticate with Keycloak admin API"
                )
            
            admin_token = token_response.json()["access_token"]
            
            # Admins fetch all users, others only their own
            if "admin" in current_user.roles:
                # Fetch all users from realm
                users_response = await client.get(
                    f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/users",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                
                if users_response.status_code != 200:
                    logger.error(f"Failed to fetch users: {users_response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Could not fetch users from Keycloak"
                    )
                
                users = users_response.json()
            else:
                # Non-admin users: fetch only their own details
                user_response = await client.get(
                    f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/users/{current_user.sub}",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                
                if user_response.status_code != 200:
                    logger.error(f"Failed to fetch own user details: {user_response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Could not fetch user details from Keycloak"
                    )
                
                users = [user_response.json()]
            
            # Fetch roles for each user
            formatted_users = []
            for user in users:
                # Get user's realm roles
                roles_response = await client.get(
                    f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/users/{user['id']}/role-mappings/realm",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                
                roles = []
                if roles_response.status_code == 200:
                    realm_roles = roles_response.json()
                    roles = [role["name"] for role in realm_roles if role["name"] in ["admin", "operator", "viewer"]]
                
                formatted_users.append({
                    "id": user["id"],
                    "username": user.get("username", ""),
                    "email": user.get("email", ""),
                    "firstName": user.get("firstName", ""),
                    "lastName": user.get("lastName", ""),
                    "enabled": user.get("enabled", False),
                    "roles": roles,
                })
            
            logger.info(f"Fetched {len(formatted_users)} users from Keycloak (user: {current_user.sub})")
            return formatted_users
            
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching Keycloak users: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Keycloak"
        )
    except Exception as e:
        logger.error(f"Error fetching Keycloak users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users"
        )


@router.post("/keycloak/users", response_model=Dict[str, Any])
async def create_keycloak_user(
    user: UserCreate,
    current_user: UserInfo = Depends(require_admin)
):
    """
    Create a new user in Keycloak realm
    
    Args:
        user: User data to create
        current_user: Current authenticated admin user
        
    Returns:
        Dict: Created user information with id
    """
    try:
        async with httpx.AsyncClient() as client:
            # Get admin access token
            token_response = await client.post(
                f"{settings.keycloak_url}/realms/master/protocol/openid-connect/token",
                data={
                    "username": settings.keycloak_admin_username,
                    "password": settings.keycloak_admin_password,
                    "grant_type": "password",
                    "client_id": "admin-cli"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                logger.error(f"Failed to get admin token: {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Could not authenticate with Keycloak admin API"
                )
            
            admin_token = token_response.json()["access_token"]
            
            # Create user payload
            user_payload = {
                "username": user.username,
                "email": user.email,
                "firstName": user.firstName,
                "lastName": user.lastName,
                "enabled": user.enabled,
                "emailVerified": user.emailVerified,
                "credentials": [
                    {
                        "type": "password",
                        "value": user.password,
                        "temporary": False
                    }
                ]
            }
            
            # Create user in Keycloak
            create_response = await client.post(
                f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/users",
                json=user_payload,
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if create_response.status_code == 409:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this username or email already exists"
                )
            elif create_response.status_code != 201:
                logger.error(f"Failed to create user: {create_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Could not create user in Keycloak: {create_response.text}"
                )
            
            # Get the created user ID from Location header
            location = create_response.headers.get("Location")
            if not location:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="User created but could not retrieve user ID"
                )
            
            user_id = location.split("/")[-1]
            
            # Assign roles if provided
            if user.roles:
                # Get available realm roles
                roles_response = await client.get(
                    f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/roles",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                
                if roles_response.status_code == 200:
                    available_roles = roles_response.json()
                    roles_to_assign = [
                        role for role in available_roles 
                        if role["name"] in user.roles
                    ]
                    
                    if roles_to_assign:
                        # Assign roles to user
                        assign_response = await client.post(
                            f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/users/{user_id}/role-mappings/realm",
                            json=roles_to_assign,
                            headers={
                                "Authorization": f"Bearer {admin_token}",
                                "Content-Type": "application/json"
                            }
                        )
                        
                        if assign_response.status_code not in [200, 204]:
                            logger.warning(f"Failed to assign roles to user: {assign_response.text}")
            
            logger.info(f"Created user {user.username} with ID {user_id}")
            
            return {
                "id": user_id,
                "username": user.username,
                "email": user.email,
                "firstName": user.firstName,
                "lastName": user.lastName,
                "enabled": user.enabled,
                "message": "User created successfully"
            }
            
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        logger.error(f"HTTP error creating Keycloak user: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Keycloak"
        )
    except Exception as e:
        logger.error(f"Error creating Keycloak user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.delete("/keycloak/users/{user_id}")
async def delete_keycloak_user(
    user_id: str,
    current_user: UserInfo = Depends(require_admin)
):
    """
    Delete a user from Keycloak realm
    
    Args:
        user_id: Keycloak user ID
        current_user: Current authenticated admin user
        
    Returns:
        Dict: Success message
    """
    try:
        async with httpx.AsyncClient() as client:
            # Get admin access token
            token_response = await client.post(
                f"{settings.keycloak_url}/realms/master/protocol/openid-connect/token",
                data={
                    "username": settings.keycloak_admin_username,
                    "password": settings.keycloak_admin_password,
                    "grant_type": "password",
                    "client_id": "admin-cli"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                logger.error(f"Failed to get admin token: {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Could not authenticate with Keycloak admin API"
                )
            
            admin_token = token_response.json()["access_token"]
            
            # Delete user
            delete_response = await client.delete(
                f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/users/{user_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            if delete_response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            elif delete_response.status_code not in [200, 204]:
                logger.error(f"Failed to delete user: {delete_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not delete user from Keycloak"
                )
            
            logger.info(f"Deleted user {user_id}")
            return {"message": "User deleted successfully"}
            
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        logger.error(f"HTTP error deleting Keycloak user: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Keycloak"
        )
    except Exception as e:
        logger.error(f"Error deleting Keycloak user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


@router.put("/keycloak/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    password_reset: PasswordReset,
    current_user: UserInfo = Depends(require_admin)
):
    """
    Reset password for any user (admin only)
    
    Args:
        user_id: Keycloak user ID
        password_reset: New password and temporary flag
        current_user: Current authenticated admin user
        
    Returns:
        Dict: Success message
    """
    try:
        async with httpx.AsyncClient() as client:
            # Get admin access token
            token_response = await client.post(
                f"{settings.keycloak_url}/realms/master/protocol/openid-connect/token",
                data={
                    "username": settings.keycloak_admin_username,
                    "password": settings.keycloak_admin_password,
                    "grant_type": "password",
                    "client_id": "admin-cli"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                logger.error(f"Failed to get admin token: {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Could not authenticate with Keycloak admin API"
                )
            
            admin_token = token_response.json()["access_token"]
            
            # Reset password
            reset_response = await client.put(
                f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/users/{user_id}/reset-password",
                json={
                    "type": "password",
                    "value": password_reset.password,
                    "temporary": password_reset.temporary
                },
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if reset_response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            elif reset_response.status_code not in [200, 204]:
                logger.error(f"Failed to reset password: {reset_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not reset password in Keycloak"
                )
            
            logger.info(f"Reset password for user {user_id} (temporary: {password_reset.temporary})")
            return {
                "message": "Password reset successfully",
                "temporary": password_reset.temporary
            }
            
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        logger.error(f"HTTP error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Keycloak"
        )
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


@router.put("/profile/reset-password")
async def reset_own_password(
    password_reset: PasswordReset,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Reset own password (any authenticated user)
    
    Args:
        password_reset: New password
        current_user: Current authenticated user
        
    Returns:
        Dict: Success message
    """
    try:
        async with httpx.AsyncClient() as client:
            # Get admin access token (needed to change user password via API)
            token_response = await client.post(
                f"{settings.keycloak_url}/realms/master/protocol/openid-connect/token",
                data={
                    "username": settings.keycloak_admin_username,
                    "password": settings.keycloak_admin_password,
                    "grant_type": "password",
                    "client_id": "admin-cli"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                logger.error(f"Failed to get admin token: {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Could not authenticate with Keycloak admin API"
                )
            
            admin_token = token_response.json()["access_token"]
            
            # Reset own password
            reset_response = await client.put(
                f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}/users/{current_user.sub}/reset-password",
                json={
                    "type": "password",
                    "value": password_reset.password,
                    "temporary": False  # Never temporary for self-reset
                },
                headers={
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if reset_response.status_code not in [200, 204]:
                logger.error(f"Failed to reset own password: {reset_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not reset password in Keycloak"
                )
            
            logger.info(f"User {current_user.sub} reset their own password")
            return {"message": "Password reset successfully"}
            
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        logger.error(f"HTTP error resetting own password: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to Keycloak"
        )
    except Exception as e:
        logger.error(f"Error resetting own password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


