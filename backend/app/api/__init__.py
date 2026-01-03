"""API router configuration"""

from fastapi import APIRouter

from app.api.endpoints import tenants, schedules, audit_logs, auth, terminal

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["Schedules"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])
api_router.include_router(terminal.router, prefix="/terminal", tags=["Terminal"])
