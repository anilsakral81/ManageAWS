"""Keycloak authentication and JWT validation"""

import logging
from typing import Dict, Optional
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from keycloak import KeycloakOpenID
import httpx

from app.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()


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
) -> Dict:
    """
    Dependency to get current authenticated user from JWT token
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Dict: User information from token
        
    Raises:
        HTTPException: If authentication fails
    """
    # Development mode bypass - if Keycloak URL is default/not configured
    if settings.keycloak_url == "https://keycloak.example.com" or settings.debug:
        logger.warning("Auth bypass enabled - using mock user for development")
        return {
            "sub": "dev-user-123",
            "email": "dev@example.com",
            "name": "Development User",
            "roles": ["tenant-admin", "admin"],
        }
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = await verify_token(token)
    
    # Extract user info from token
    user_info = {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name", payload.get("preferred_username")),
        "roles": extract_roles(payload),
    }
    
    if not user_info.get("sub"):
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
    async def permission_checker(current_user: Dict = Depends(get_current_user)) -> Dict:
        user_roles = current_user.get("roles", [])
        
        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        return current_user
    
    return permission_checker


# Role-based dependencies
require_admin = check_permission(["tenant-admin", "admin"])
require_operator = check_permission(["tenant-admin", "tenant-operator", "admin"])
require_viewer = check_permission(["tenant-admin", "tenant-operator", "tenant-viewer", "admin"])
