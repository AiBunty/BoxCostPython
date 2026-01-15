"""Health check router for system monitoring."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Dict, Any

from backend.database import get_db

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        dict: Health status information
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "BoxCostPro Python Backend"
    }


@router.get("/health/db", status_code=status.HTTP_200_OK)
async def database_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Database health check endpoint.
    
    Args:
        db: Database session
        
    Returns:
        dict: Database health status
        
    Raises:
        HTTPException: If database connection fails
    """
    try:
        # Execute a simple query to check connection
        result = db.execute(text("SELECT 1"))
        result.fetchone()
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Detailed health check with all system components.
    
    Args:
        db: Database session
        
    Returns:
        dict: Detailed health status for all components
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
    
    # Check API
    health_status["components"]["api"] = {
        "status": "healthy",
        "message": "API is responding"
    }
    
    # Additional checks can be added here:
    # - Redis connection
    # - External API availability
    # - File system access
    # - Email service
    
    return health_status
