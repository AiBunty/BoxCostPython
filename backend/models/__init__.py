"""Models package initialization - imports all database models."""
from backend.models.user import User, UserRole, ApprovalStatus
from backend.models.tenant import Tenant, TenantUser
from backend.models.company_profile import CompanyProfile
from backend.models.admin import Admin, AdminSession
from backend.models.pricing import (
    PaperBFPrice,
    PaperShade,
    ShadePremium,
    PaperPricingRule,
    BusinessDefault,
    FluteSettings
)
from backend.models.party import PartyProfile
from backend.models.quote import Quote, QuoteVersion, QuoteItem, QuoteSendLog, QuoteStatus
from backend.models.support import SupportTicket, SupportMessage, SupportAgent, SLARule
from backend.models.audit import AdminAuditLog, AuthAuditLog, AdminLoginAuditLog, EmailLog
from backend.models.coupon import Coupon, CouponUsage, CouponType, CouponStatus
from backend.models.two_factor_auth import TwoFactorAuth, TwoFactorBackupCode
from backend.models.entitlement import (
    Feature,
    UserEntitlement,
    TenantEntitlement,
    PlanTemplate,
    EntitlementLog,
)
from backend.models.subscription import (
    SubscriptionPlan,
    UserSubscription,
    SubscriptionOverride,
    PlanInterval,
    SubscriptionStatus,
)
from backend.models.payment import (
    PaymentMethod,
    Transaction,
    UsageRecord,
    SubscriptionChange,
)

__all__ = [
    "User",
    "UserRole",
    "ApprovalStatus",
    "Tenant",
    "TenantUser",
    "CompanyProfile",
    "Admin",
    "AdminSession",
    "PaperBFPrice",
    "PaperShade",
    "ShadePremium",
    "PaperPricingRule",
    "BusinessDefault",
    "FluteSettings",
    "PartyProfile",
    "Quote",
    "QuoteVersion",
    "QuoteItem",
    "QuoteSendLog",
    "QuoteStatus",
    "SupportTicket",
    "SupportMessage",
    "SupportAgent",
    "SLARule",
    "AdminAuditLog",
    "AuthAuditLog",
    "AdminLoginAuditLog",
    "EmailLog",
    "Coupon",
    "CouponUsage",
    "CouponType",
    "CouponStatus",
    "TwoFactorAuth",
    "TwoFactorBackupCode",
    "Feature",
    "UserEntitlement",
    "TenantEntitlement",
    "PlanTemplate",
    "EntitlementLog",
    "SubscriptionPlan",
    "UserSubscription",
    "SubscriptionOverride",
    "PlanInterval",
    "SubscriptionStatus",
    "PaymentMethod",
    "Transaction",
    "UsageRecord",
    "SubscriptionChange",
]
