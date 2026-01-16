"""Coupon and promotion models."""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Enum as SQLEnum, Numeric
import enum
from datetime import datetime
from backend.database import Base, BaseMixin, TenantMixin


class CouponType(str, enum.Enum):
    """Coupon discount type."""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"


class CouponStatus(str, enum.Enum):
    """Coupon status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    DISABLED = "disabled"


class Coupon(Base, BaseMixin, TenantMixin):
    """
    Discount coupon for subscriptions or invoices.
    """
    __tablename__ = "coupons"
    
    # Coupon Identity
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Discount
    coupon_type = Column(SQLEnum(CouponType), default=CouponType.PERCENTAGE, nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)  # Percentage or fixed amount
    
    # Limits
    max_uses = Column(Integer, nullable=True)  # Null = unlimited
    uses_count = Column(Integer, default=0, nullable=False)
    max_uses_per_user = Column(Integer, nullable=True)
    min_purchase_amount = Column(Numeric(10, 2), nullable=True)
    
    # Validity
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    # Scope
    applies_to = Column(String(50), nullable=True)  # subscription, invoice, all
    plan_ids = Column(Text, nullable=True)  # JSON array of applicable plan IDs
    
    # Status
    status = Column(SQLEnum(CouponStatus), default=CouponStatus.ACTIVE, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)  # Public or invite-only
    
    # Metadata
    created_by_admin_id = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<Coupon(code={self.code}, type={self.coupon_type}, value={self.discount_value})>"
    
    def is_valid(self) -> bool:
        """Check if coupon is currently valid."""
        now = datetime.utcnow()
        if self.status != CouponStatus.ACTIVE:
            return False
        if self.valid_from > now:
            return False
        if self.valid_until and self.valid_until < now:
            return False
        if self.max_uses and self.uses_count >= self.max_uses:
            return False
        return True


class CouponUsage(Base, BaseMixin):
    """
    Track coupon usage by users.
    """
    __tablename__ = "coupon_usages"
    
    coupon_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    
    # Application
    applied_to_type = Column(String(50), nullable=False)  # subscription, invoice
    applied_to_id = Column(Integer, nullable=False, index=True)
    
    # Discount Applied
    original_amount = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), nullable=False)
    final_amount = Column(Numeric(10, 2), nullable=False)
    
    # Tracking
    used_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP", nullable=False)
    
    def __repr__(self):
        return f"<CouponUsage(coupon={self.coupon_id}, user={self.user_id}, discount={self.discount_amount})>"
