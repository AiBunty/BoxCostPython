"""
User Entitlement Models - Feature access and quotas
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship

from backend.database import Base, BaseMixin


class FeatureCategory(str, Enum):
    """Feature categories."""
    CORE = "core"
    QUOTES = "quotes"
    INVOICES = "invoices"
    PARTIES = "parties"
    ADMIN = "admin"
    INTEGRATIONS = "integrations"
    ANALYTICS = "analytics"
    SUPPORT = "support"


class Feature(Base, BaseMixin):
    """Available features in the system."""
    __tablename__ = "features"

    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(String(500))
    category = Column(String(50), nullable=False, index=True)  # FeatureCategory
    
    # Default availability
    is_default = Column(Boolean, default=False)  # Available to all
    min_plan_level = Column(Integer, default=0)  # 0=free, 1=basic, 2=pro, 3=enterprise
    
    # Additional configuration
    feature_metadata = Column(JSON)  # Additional feature configuration

    __table_args__ = (
        Index("ix_features_category_name", "category", "name"),
    )


class UserEntitlement(Base, BaseMixin):
    """User-specific feature entitlements and quotas."""
    __tablename__ = "user_entitlements"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    feature_id = Column(Integer, ForeignKey("features.id"), nullable=False, index=True)
    
    # Access control
    is_enabled = Column(Boolean, default=True)
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Temporary access
    granted_by = Column(Integer, ForeignKey("admins.id"), nullable=True)  # Who granted it
    
    # Quota management
    quota_limit = Column(Integer, nullable=True)  # Max usage (null = unlimited)
    quota_used = Column(Integer, default=0)  # Current usage
    quota_reset_at = Column(DateTime, nullable=True)  # When quota resets
    
    # Relationships
    user = relationship("User", backref="entitlements")
    tenant = relationship("Tenant")
    feature = relationship("Feature")
    granted_by_admin = relationship("Admin", foreign_keys=[granted_by])

    __table_args__ = (
        Index("ix_user_entitlements_user_feature", "user_id", "feature_id", unique=True),
        Index("ix_user_entitlements_tenant_feature", "tenant_id", "feature_id"),
        Index("ix_user_entitlements_expires", "expires_at"),
    )


class TenantEntitlement(Base, BaseMixin):
    """Tenant-wide feature entitlements (applies to all users in tenant)."""
    __tablename__ = "tenant_entitlements"

    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    feature_id = Column(Integer, ForeignKey("features.id"), nullable=False, index=True)
    
    # Access control
    is_enabled = Column(Boolean, default=True)
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    granted_by = Column(Integer, ForeignKey("admins.id"), nullable=True)
    
    # Tenant-wide quota
    quota_limit = Column(Integer, nullable=True)
    quota_used = Column(Integer, default=0)
    quota_reset_at = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", backref="entitlements")
    feature = relationship("Feature")
    granted_by_admin = relationship("Admin", foreign_keys=[granted_by])

    __table_args__ = (
        Index("ix_tenant_entitlements_tenant_feature", "tenant_id", "feature_id", unique=True),
    )


class PlanTemplate(Base, BaseMixin):
    """Subscription plan templates with predefined feature sets."""
    __tablename__ = "plan_templates"

    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(String(500))
    level = Column(Integer, nullable=False, index=True)  # 0=free, 1=basic, 2=pro, 3=enterprise
    
    # Pricing (reference only, actual pricing in subscription system)
    monthly_price = Column(Integer, nullable=True)  # In cents
    annual_price = Column(Integer, nullable=True)
    
    # Features included (JSON array of feature names)
    included_features = Column(JSON, nullable=False, default=list)
    
    # Default quotas (JSON object: {feature_name: limit})
    default_quotas = Column(JSON, nullable=False, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)  # Visible to customers


class EntitlementLog(Base, BaseMixin):
    """Audit log for entitlement changes."""
    __tablename__ = "entitlement_logs"

    # What changed
    entity_type = Column(String(50), nullable=False, index=True)  # user_entitlement, tenant_entitlement
    entity_id = Column(Integer, nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)  # granted, revoked, quota_increased, quota_reset
    
    # Who and when
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    
    # Details
    old_value = Column(JSON)
    new_value = Column(JSON)
    reason = Column(String(500))
    
    # Relationships
    admin = relationship("Admin")
    user = relationship("User")
    tenant = relationship("Tenant")

    __table_args__ = (
        Index("ix_entitlement_logs_entity", "entity_type", "entity_id"),
        Index("ix_entitlement_logs_admin", "admin_id", "created_at"),
    )
