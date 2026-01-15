"""
FastAPI application entry point.
BoxCostPro - Python Backend for Corrugated Box Manufacturing SaaS
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from backend.config import settings
from backend.database import engine, Base
from backend.routers import health, pricing, quotes

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting BoxCostPro Python Backend...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database URL: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'Not configured'}")
    
    # Create database tables (in production, use Alembic migrations instead)
    # Base.metadata.create_all(bind=engine)
    
    yield
    
    # Shutdown
    logger.info("Shutting down BoxCostPro Python Backend...")


# Create FastAPI application
app = FastAPI(
    title="BoxCostPro API",
    description="Comprehensive SaaS platform for corrugated box manufacturing industry",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed error messages."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body,
            "message": "Validation error"
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "Internal server error",
            "detail": str(exc) if settings.is_development else "An unexpected error occurred"
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "application": "BoxCostPro Python Backend",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat(),
        "docs": f"{settings.app_url}/docs",
        "health": f"{settings.app_url}/health"
    }


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(pricing.router, prefix="/api", tags=["Pricing"])
app.include_router(quotes.router, prefix="/api", tags=["Quotes"])

# Additional routers will be added here as they are created:
# app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(users.router, prefix="/api/users", tags=["Users"])
# app.include_router(parties.router, prefix="/api/parties", tags=["Customers"])
# app.include_router(invoices.router, prefix="/api/invoices", tags=["Invoices"])
# app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.is_development
    )
