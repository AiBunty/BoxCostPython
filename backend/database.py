"""
Database connection and session management using SQLAlchemy.
Provides database engine, session factory, and base model class.
"""
from sqlalchemy import create_engine, Column, Integer, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from typing import Generator
from datetime import datetime

from backend.config import settings

# Create database engine
engine = create_engine(
    settings.database_url,
    echo=settings.is_development,  # SQL logging in development
    pool_pre_ping=True,  # Verify connections before using
    poolclass=NullPool if settings.is_development else None,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()


class BaseMixin:
    """Base mixin for all models with common fields."""
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


class TenantMixin:
    """Mixin for multi-tenant models."""
    
    tenant_id = Column(Integer, nullable=False, index=True)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Usage in FastAPI routes:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    Creates all tables defined in models.
    """
    from backend.models import user, tenant, company_profile  # Import all models
    Base.metadata.create_all(bind=engine)


def drop_db():
    """
    Drop all database tables.
    WARNING: This will delete all data!
    """
    Base.metadata.drop_all(bind=engine)
