"""Keycloak authentication and JWT validation"""

import logging
from typing import Dict, Optional, List
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from keycloak import KeycloakOpenID
import httpx

from app.config import settings
from app.schemas.user import UserInfo

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)  # Don't auto-error if no auth header


@lru_cache()
def get_keycloak_openid() -> KeycloakOpenID:
    """
    Get Keycloak OpenID client (cached)
    
    Returns:
        KeycloakOpenID: Keycloak client instance
    """
    return KeycloakOpenID(
        server_url=settings.keycloak_url,
        realm_name=settings.keycloak_realm,
        client_id=settings.keycloak_client_id,
        client_secret_key=settings.keycloak_client_secret,
    )


async def get_keycloak_public_key() -> str:
    """
    Fetch Keycloak public key for JWT validation
    
    Returns:
        str: Public key in PEM format
    """
    try:
        keycloak_openid = get_keycloak_openid()
        return (
            "-----BEGIN PUBLIC KEY-----\n"
            + keycloak_openid.public_key()
            + "\n-----END PUBLIC KEY-----"
        )
    except Exception as e:
        logger.error(f"Failed to fetch Keycloak public key: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )


async def verify_token(token: str) -> Dict:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Dict: Decoded token payload
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        # Get public key
        public_key = await get_keycloak_public_key()
        
        # Decode and verify token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_exp": True,
            },
        )
        
        return payload
        
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserInfo:
    """
    Dependency to get current authenticated user from JWT token
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        UserInfo: User information from token
        
    Raises:
        HTTPException: If authentication fails
    """
    # Development mode bypass - if Keycloak URL is default/not configured
    # Note: Only use this in local development with proper configuration
    if settings.keycloak_url == "https://keycloak.example.com":
        logger.warning("Auth bypass enabled - using mock admin user for local development (Keycloak not configured)")
        return UserInfo(
            sub="dev-user-123",
            email="dev@example.com",
            preferred_username="developer",
            name="Development User",
            roles=["admin"],  # Only grant admin role in bypass mode
            groups=[],
            allowed_namespaces=["*"]  # Admin has access to all
        )
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = await verify_token(token)
    
    # Extract roles
    roles = extract_roles(payload)
    
    # Extract groups
    groups = payload.get("groups", [])
    
    # Extract user info from token
    user_info = UserInfo(
        sub=payload.get("sub"),
        email=payload.get("email"),
        preferred_username=payload.get("preferred_username", payload.get("email")),
        name=payload.get("name"),
        roles=roles,
        groups=groups,
        allowed_namespaces=[]  # Will be populated from database
    )
    
    if not user_info.sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    return user_info


def extract_roles(payload: Dict) -> list[str]:
    """
    Extract roles from JWT token payload
    
    Args:
        payload: JWT token payload
        
    Returns:
        list[str]: List of user roles
    """
    roles = []
    
    # Check resource_access for client-specific roles
    resource_access = payload.get("resource_access", {})
    client_roles = resource_access.get(settings.keycloak_client_id, {})
    roles.extend(client_roles.get("roles", []))
    
    # Check realm_access for realm roles
    realm_access = payload.get("realm_access", {})
    roles.extend(realm_access.get("roles", []))
    
    return list(set(roles))  # Remove duplicates


def check_permission(required_roles: list[str]):
    """
    Decorator to check if user has required roles
    
    Args:
        required_roles: List of required roles
        
    Returns:
        Dependency function
    """
    async def permission_checker(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
        user_roles = current_user.roles
        
        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        return current_user
    
    return permission_checker


# Role-based dependencies
require_admin = check_permission(["admin"])
require_operator = check_permission(["admin", "operator"])
require_viewer = check_permission(["admin", "operator", "viewer"])


async def get_user_allowed_namespaces(
    user: UserInfo,
    db
) -> List[str]:
    """
    Get list of namespaces user is allowed to access
    
    Args:
        user: User information
        db: Database session
        
    Returns:
        List[str]: List of allowed namespace names, or ["*"] for admins/viewers
    """
    from sqlalchemy import select
    from app.models.user_namespace import UserNamespace
    
    # Admin role: access all namespaces with full permissions
    if "admin" in user.roles:
        return ["*"]
    
    # Viewer role: can see all namespaces but read-only
    if "viewer" in user.roles:
        return ["*"]
    
    # Operator role: only see explicitly granted namespaces
    # Get user-specific namespace permissions from database
    result = await db.execute(
        select(UserNamespace.namespace)
        .where(UserNamespace.user_id == user.sub)
        .where(UserNamespace.enabled == True)
    )
    
    namespaces = [row[0] for row in result.all()]
    return namespaces if namespaces else []



async def get_current_user_ws(token: str = None) -> Dict:
    """
    Get current user for WebSocket connections
    
    Args:
        token: Bearer token
        
    Returns:
        Dict: User information
    """
    # Development bypass
    if settings.auth_bypass_enabled:
        return {
            "sub": "dev-user",
            "email": "dev@example.com",
            "preferred_username": "developer",
            "name": "Development User"
        }
    
    if not token:
        return None
    
    try:
        token_info = keycloak_openid.introspect(token)
        if token_info.get("active"):
            return token_info
    except:
        pass
    
    return None
