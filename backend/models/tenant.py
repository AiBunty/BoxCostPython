"""Tenant model - Multi-tenancy support for data isolation."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship

from backend.database import Base, BaseMixin


class Tenant(Base, BaseMixin):
    """
    Tenant model - Represents a company/organization in the system.
    Provides multi-tenant data isolation.
    """
    __tablename__ = "tenants"
    
    # Basic Information
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    
    # Contact
    primary_email = Column(String(255), nullable=True)
    primary_phone = Column(String(20), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_trial = Column(Boolean, default=True, nullable=False)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    
    # Settings
    timezone = Column(String(50), default="Asia/Kolkata", nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    
    # Relationships
    # users = relationship("TenantUser", back_populates="tenant")
    # company_profiles = relationship("CompanyProfile", back_populates="tenant")
    # subscriptions = relationship("UserSubscription", back_populates="tenant")
    
    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.name}, slug={self.slug})>"


class TenantUser(Base, BaseMixin):
    """
    TenantUser model - Maps users to tenants with roles.
    Supports users belonging to multiple tenants.
    """
    __tablename__ = "tenant_users"
    
    tenant_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Role within tenant
    role = Column(String(50), default="member", nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    invited_by = Column(Integer, nullable=True)
    joined_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    # tenant = relationship("Tenant", back_populates="users")
    # user = relationship("User", back_populates="tenants")
    
    def __repr__(self):
        return f"<TenantUser(tenant_id={self.tenant_id}, user_id={self.user_id}, role={self.role})>"
