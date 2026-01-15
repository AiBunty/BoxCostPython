"""Subscription and entitlement models."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from backend.database import Base, BaseMixin, TenantMixin


class PlanInterval(str, enum.Enum):
    """Subscription plan interval."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status."""
    ACTIVE = "active"
    TRIAL = "trial"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


class SubscriptionPlan(Base, BaseMixin):
    """
    Subscription plan definitions.
    Defines features, quotas, and pricing for each tier.
    """
    __tablename__ = "subscription_plans"
    
    # Plan Identity
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Pricing
    price = Column(Numeric(10, 2), nullable=False)
    interval = Column(SQLEnum(PlanInterval), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    
    # Trial
    trial_days = Column(Integer, default=0, nullable=False)
    
    # Features (JSON)
    features = Column(JSON, nullable=False)  # {feature_key: boolean}
    quotas = Column(JSON, nullable=False)  # {quota_key: limit}
    
    # Display
    display_order = Column(Integer, default=0, nullable=False)
    is_popular = Column(Boolean, default=False, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<SubscriptionPlan(name={self.name}, price={self.price})>"


class UserSubscription(Base, BaseMixin, TenantMixin):
    """
    Active user subscriptions.
    Links users to their current subscription plan.
    """
    __tablename__ = "user_subscriptions"
    
    user_id = Column(Integer, nullable=False, index=True)
    plan_id = Column(Integer, nullable=False, index=True)
    
    # Subscription Period
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.TRIAL, nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    
    # Payment
    payment_transaction_id = Column(String(255), nullable=True)
    razorpay_subscription_id = Column(String(255), nullable=True, index=True)
    
    # Auto-renewal
    auto_renew = Column(Boolean, default=True, nullable=False)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Usage Tracking
    last_usage_reset = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<UserSubscription(user_id={self.user_id}, plan_id={self.plan_id}, status={self.status})>"


class SubscriptionOverride(Base, BaseMixin):
    """
    Admin-controlled temporary subscription overrides.
    Allows admins to grant temporary access or quotas.
    """
    __tablename__ = "subscription_overrides"
    
    subscription_id = Column(Integer, nullable=False, index=True)
    
    # Override Type
    override_type = Column(String(50), nullable=False)  # FEATURE_UNLOCK, QUOTA_INCREASE, TRIAL_EXTENSION
    
    # Override Details
    feature_key = Column(String(100), nullable=True)
    quota_key = Column(String(100), nullable=True)
    quota_value = Column(Integer, nullable=True)
    
    # Validity
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Admin Info
    created_by_admin_id = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<SubscriptionOverride(type={self.override_type}, expires={self.expires_at})>"


class EntitlementCache(Base, BaseMixin):
    """
    Denormalized entitlement cache for performance.
    Stores computed entitlements to avoid repeated calculations.
    """
    __tablename__ = "entitlement_cache"
    
    subscription_id = Column(Integer, unique=True, nullable=False, index=True)
    
    # Cached Entitlements
    features = Column(JSON, nullable=False)  # {feature_key: boolean}
    quotas = Column(JSON, nullable=False)  # {quota_key: {limit, used}}
    
    # Cache Metadata
    computed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    def __repr__(self):
        return f"<EntitlementCache(subscription_id={self.subscription_id})>"


class UserFeatureUsage(Base, BaseMixin):
    """
    Track feature usage for quota enforcement.
    """
    __tablename__ = "user_feature_usage"
    
    subscription_id = Column(Integer, nullable=False, index=True)
    feature_key = Column(String(100), nullable=False, index=True)
    
    # Usage Counts
    usage_count = Column(Integer, default=0, nullable=False)
    usage_limit = Column(Integer, nullable=True)
    
    # Reset Period
    reset_period = Column(String(20), default="monthly", nullable=False)  # monthly, yearly
    last_reset_at = Column(DateTime(timezone=True), nullable=True)
    next_reset_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<UserFeatureUsage(feature={self.feature_key}, usage={self.usage_count}/{self.usage_limit})>"


class PlatformEvent(Base, BaseMixin):
    """
    Immutable platform events log.
    Records all significant admin actions and system events.
    """
    __tablename__ = "platform_events"
    
    # Event Identity
    event_type = Column(String(100), nullable=False, index=True)
    event_category = Column(String(50), nullable=False)  # subscription, user, admin, system
    
    # Event Data
    actor_type = Column(String(50), nullable=False)  # admin, system, user
    actor_id = Column(Integer, nullable=True)
    
    # Subject
    subject_type = Column(String(50), nullable=False)  # user, subscription, tenant
    subject_id = Column(Integer, nullable=False, index=True)
    
    # Metadata
    event_data = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Immutability
    is_immutable = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<PlatformEvent(type={self.event_type}, subject={self.subject_type}:{self.subject_id})>"


class SubscriptionCoupon(Base, BaseMixin):
    """
    Discount coupons for subscriptions.
    """
    __tablename__ = "subscription_coupons"
    
    # Coupon Identity
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Discount
    discount_type = Column(String(20), nullable=False)  # percentage, fixed
    discount_value = Column(Numeric(10, 2), nullable=False)
    
    # Applicability
    applicable_plans = Column(JSON, nullable=True)  # List of plan IDs, null = all
    max_uses = Column(Integer, nullable=True)
    uses_count = Column(Integer, default=0, nullable=False)
    
    # Validity
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_admin_id = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<SubscriptionCoupon(code={self.code}, discount={self.discount_value})>"
