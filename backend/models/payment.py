"""
Payment and Transaction Models - Extended subscription features
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship

from backend.database import Base, BaseMixin


class PaymentMethodType(str, Enum):
    """Payment method types."""
    CARD = "card"
    BANK_ACCOUNT = "bank_account"
    UPI = "upi"
    WALLET = "wallet"


class TransactionStatus(str, Enum):
    """Transaction status."""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELED = "canceled"


class TransactionType(str, Enum):
    """Transaction types."""
    PAYMENT = "payment"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"
    CREDIT = "credit"


class PaymentMethod(Base, BaseMixin):
    """Saved payment methods."""
    __tablename__ = "payment_methods"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Payment method details
    type = Column(String(20), nullable=False)  # PaymentMethodType
    last4 = Column(String(4), nullable=True)
    brand = Column(String(50), nullable=True)  # visa, mastercard, etc.
    exp_month = Column(Integer, nullable=True)
    exp_year = Column(Integer, nullable=True)
    
    # Status
    is_default = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    
    # Payment gateway integration
    stripe_payment_method_id = Column(String(255), unique=True, nullable=True, index=True)
    razorpay_token_id = Column(String(255), unique=True, nullable=True, index=True)
    gateway_customer_id = Column(String(255), nullable=True, index=True)
    
    # Metadata
    billing_details = Column(JSON)  # name, email, address
    extra_data = Column(JSON)  # Additional metadata
    
    # Relationships
    user = relationship("User", backref="payment_methods")
    tenant = relationship("Tenant")
    
    __table_args__ = (
        Index("ix_payment_methods_user_default", "user_id", "is_default"),
    )


class Transaction(Base, BaseMixin):
    """Billing transactions and payments."""
    __tablename__ = "transactions"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=True, index=True)
    
    # Transaction details
    amount = Column(Integer, nullable=False)  # In cents/paise
    currency = Column(String(3), default="INR")
    description = Column(String(500))
    
    # Type and status
    type = Column(String(50), nullable=False, index=True)  # TransactionType
    status = Column(String(50), nullable=False, index=True)  # TransactionStatus
    
    # Payment method
    payment_method_id = Column(Integer, ForeignKey("payment_methods.id"), nullable=True)
    
    # Payment gateway integration
    stripe_charge_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_invoice_id = Column(String(255), nullable=True, index=True)
    stripe_payment_intent_id = Column(String(255), nullable=True, index=True)
    razorpay_payment_id = Column(String(255), unique=True, nullable=True, index=True)
    razorpay_order_id = Column(String(255), nullable=True, index=True)
    
    # Failure details
    failure_code = Column(String(100), nullable=True)
    failure_message = Column(String(500), nullable=True)
    
    # Timestamps
    paid_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    
    # Additional data
    extra_data = Column(JSON)  # Additional metadata
    receipt_url = Column(String(500), nullable=True)
    
    # Relationships
    user = relationship("User", backref="transactions")
    tenant = relationship("Tenant")
    subscription = relationship("UserSubscription", backref="transactions", foreign_keys=[subscription_id])
    payment_method = relationship("PaymentMethod")
    
    __table_args__ = (
        Index("ix_transactions_user_status", "user_id", "status"),
        Index("ix_transactions_created", "created_at"),
        Index("ix_transactions_subscription", "subscription_id", "created_at"),
    )


class UsageRecord(Base, BaseMixin):
    """Track feature usage for metered billing and analytics."""
    __tablename__ = "usage_records"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=True, index=True)
    feature_id = Column(Integer, ForeignKey("features.id"), nullable=False, index=True)
    
    # Usage details
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Integer, nullable=True)  # Price per unit in cents/paise
    total_amount = Column(Integer, nullable=True)  # Total cost
    
    # Period tracking
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    
    # Billing
    is_billed = Column(Boolean, default=False)
    billed_at = Column(DateTime, nullable=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    
    # Additional data
    extra_data = Column(JSON)  # Additional metadata
    description = Column(String(500))
    
    # Relationships
    user = relationship("User")
    tenant = relationship("Tenant")
    subscription = relationship("UserSubscription", foreign_keys=[subscription_id])
    feature = relationship("Feature")
    transaction = relationship("Transaction")
    
    __table_args__ = (
        Index("ix_usage_records_user_period", "user_id", "period_start", "period_end"),
        Index("ix_usage_records_feature_period", "feature_id", "period_start"),
        Index("ix_usage_records_billing", "is_billed", "billed_at"),
    )


class SubscriptionChange(Base, BaseMixin):
    """Track subscription changes for analytics and auditing."""
    __tablename__ = "subscription_changes"

    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Change details
    change_type = Column(String(50), nullable=False, index=True)  # created, upgraded, downgraded, canceled, reactivated, renewed
    
    # Before/after
    old_plan = Column(String(100), nullable=True)
    new_plan = Column(String(100), nullable=True)
    old_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=True)
    old_amount = Column(Integer, nullable=True)
    new_amount = Column(Integer, nullable=True)
    
    # Prorated amount (if applicable)
    proration_amount = Column(Integer, nullable=True)
    proration_days = Column(Integer, nullable=True)
    
    # Reason
    reason = Column(String(500), nullable=True)
    initiated_by = Column(String(50), nullable=True)  # user, admin, system
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=True)
    
    # Effective date
    effective_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Additional data
    extra_data = Column(JSON)  # Additional metadata
    notes = Column(String(1000), nullable=True)
    
    # Relationships
    subscription = relationship("UserSubscription", backref="changes", foreign_keys=[subscription_id])
    user = relationship("User")
    admin = relationship("Admin")
    
    __table_args__ = (
        Index("ix_subscription_changes_type", "change_type", "created_at"),
        Index("ix_subscription_changes_effective", "effective_at"),
        Index("ix_subscription_changes_user", "user_id", "created_at"),
    )
