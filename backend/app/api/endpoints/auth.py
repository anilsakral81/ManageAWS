"""Authentication endpoints"""

from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth.keycloak import get_current_user
from app.schemas.user import UserResponse

router = APIRouter()
security = HTTPBearer()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Dict = Depends(get_current_user)
) -> UserResponse:
    """
    Get current authenticated user information
    
    Returns:
        UserResponse: Current user details
    """
    return UserResponse(
        id=current_user.get("sub"),
        email=current_user.get("email"),
        name=current_user.get("name"),
        roles=current_user.get("roles", []),
    )


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, str]:
    """
    Logout endpoint (client should discard token)
    
    Returns:
        Dict: Success message
    """
    # In a JWT-based system, logout is typically handled client-side
    # The client should discard the token
    # Optionally, you could maintain a token blacklist here
    return {"message": "Successfully logged out"}


@router.get("/health")
async def auth_health() -> Dict[str, str]:
    """
    Authentication service health check
    
    Returns:
        Dict: Health status
    """
    return {"status": "healthy", "service": "authentication"}
