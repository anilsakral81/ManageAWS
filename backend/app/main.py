"""Main FastAPI application"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db, close_db
from app.api import api_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan events"""
    # Startup
    logger.info("Starting %s", settings.app_name)
    await init_db()
    logger.info("Database initialized")
    
    # Initialize scheduler
    from app.services.scheduler import SchedulerManager, set_scheduler
    from app.database import AsyncSessionLocal
    
    scheduler = SchedulerManager(AsyncSessionLocal)
    set_scheduler(scheduler)
    scheduler.start()
    logger.info("Scheduler initialized and started")
    
    # Load existing schedules from database
    await scheduler.load_schedules()
    logger.info("Existing schedules loaded")
    
    yield
    
    # Shutdown
    logger.info("Shutting down %s", settings.app_name)
    scheduler.shutdown()
    logger.info("Scheduler shut down")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Tenant Management System for CVS SaaS Apps",
    description="Web-based GUI for managing AWS EKS-based SaaS tenants for CVS applications",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        content={
            "status": "healthy",
            "app": settings.app_name,
            "environment": settings.app_env,
        }
    )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Kubernetes Tenant Management Portal API",
        "docs": "/docs" if settings.debug else "disabled in production",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
