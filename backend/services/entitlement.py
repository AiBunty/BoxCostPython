"""
Entitlement Service - Pure function for access control decisions.
Single source of truth for all feature access and quota calculations.
"""
from typing import Dict, Optional, Any
from datetime import datetime
from decimal import Decimal


class EntitlementDecision:
    """Result of an entitlement check."""
    
    def __init__(self, allowed: bool, reason: str = "", metadata: Optional[Dict] = None):
        self.allowed = allowed
        self.reason = reason
        self.metadata = metadata or {}
    
    def __bool__(self):
        return self.allowed


class EntitlementService:
    """
    Pure function entitlement calculator.
    NO I/O, NO side effects - only calculations based on input.
    """
    
    # Feature Keys
    FEATURE_API_ACCESS = "api_access"
    FEATURE_WHATSAPP = "whatsapp_integration"
    FEATURE_24_7_SUPPORT = "support_24_7"
    FEATURE_CUSTOM_BRANDING = "custom_branding"
    FEATURE_ANALYTICS = "analytics_dashboard"
    FEATURE_TEAM_MEMBERS = "team_members"
    FEATURE_AUTOMATION = "automation"
    FEATURE_EXPORT = "data_export"
    
    # Quota Keys
    QUOTA_QUOTES_MONTHLY = "quotes_monthly"
    QUOTA_EMAIL_ACCOUNTS = "email_accounts"
    QUOTA_CUSTOMERS = "customers"
    QUOTA_TEAM_SIZE = "team_size"
    QUOTA_API_CALLS = "api_calls_daily"
    QUOTA_STORAGE_GB = "storage_gb"
    
    def calculate_entitlement(
        self,
        subscription: Dict[str, Any],
        plan: Dict[str, Any],
        overrides: list = None,
        usage: Dict[str, int] = None,
        current_time: datetime = None
    ) -> Dict[str, Any]:
        """
        Calculate complete entitlement for a subscription.
        
        Args:
            subscription: Subscription data
            plan: Plan data with features and quotas
            overrides: List of active overrides
            usage: Current usage counts
            current_time: Current timestamp (for testing)
            
        Returns:
            dict: Complete entitlement decision with features, quotas, and reasoning
        """
        current_time = current_time or datetime.utcnow()
        overrides = overrides or []
        usage = usage or {}
        
        result = {
            "subscription_id": subscription.get("id"),
            "plan_name": plan.get("name"),
            "status": subscription.get("status"),
            "features": {},
            "quotas": {},
            "overrides_applied": [],
            "computed_at": current_time.isoformat()
        }
        
        # Check subscription status
        if not self._is_subscription_active(subscription, current_time):
            result["status"] = "expired"
            result["reason"] = "Subscription expired or inactive"
            return result
        
        # Calculate base features from plan
        plan_features = plan.get("features", {})
        for feature_key, feature_enabled in plan_features.items():
            result["features"][feature_key] = {
                "enabled": feature_enabled,
                "source": "plan"
            }
        
        # Calculate base quotas from plan
        plan_quotas = plan.get("quotas", {})
        for quota_key, quota_limit in plan_quotas.items():
            used = usage.get(quota_key, 0)
            result["quotas"][quota_key] = {
                "limit": quota_limit,
                "used": used,
                "remaining": max(0, quota_limit - used),
                "percentage_used": (used / quota_limit * 100) if quota_limit > 0 else 0,
                "source": "plan"
            }
        
        # Apply overrides
        for override in overrides:
            if not self._is_override_active(override, current_time):
                continue
            
            override_type = override.get("override_type")
            
            if override_type == "FEATURE_UNLOCK":
                feature_key = override.get("feature_key")
                if feature_key:
                    result["features"][feature_key] = {
                        "enabled": True,
                        "source": "override",
                        "override_expires": override.get("expires_at")
                    }
                    result["overrides_applied"].append({
                        "type": override_type,
                        "feature": feature_key,
                        "expires_at": override.get("expires_at")
                    })
            
            elif override_type == "QUOTA_INCREASE":
                quota_key = override.get("quota_key")
                quota_value = override.get("quota_value")
                if quota_key and quota_value:
                    current_quota = result["quotas"].get(quota_key, {})
                    new_limit = current_quota.get("limit", 0) + quota_value
                    used = current_quota.get("used", 0)
                    
                    result["quotas"][quota_key] = {
                        "limit": new_limit,
                        "used": used,
                        "remaining": max(0, new_limit - used),
                        "percentage_used": (used / new_limit * 100) if new_limit > 0 else 0,
                        "source": "override",
                        "override_expires": override.get("expires_at")
                    }
                    result["overrides_applied"].append({
                        "type": override_type,
                        "quota": quota_key,
                        "increase": quota_value,
                        "expires_at": override.get("expires_at")
                    })
        
        return result
    
    def check_feature_access(
        self,
        feature_key: str,
        entitlement: Dict[str, Any]
    ) -> EntitlementDecision:
        """
        Check if a specific feature is accessible.
        
        Args:
            feature_key: Feature identifier
            entitlement: Computed entitlement data
            
        Returns:
            EntitlementDecision: Access decision
        """
        features = entitlement.get("features", {})
        feature_data = features.get(feature_key, {})
        
        if not feature_data:
            return EntitlementDecision(
                False,
                f"Feature '{feature_key}' not available in current plan"
            )
        
        if feature_data.get("enabled"):
            return EntitlementDecision(
                True,
                f"Feature enabled via {feature_data.get('source')}",
                feature_data
            )
        
        return EntitlementDecision(
            False,
            f"Feature '{feature_key}' not enabled in current plan"
        )
    
    def check_quota_available(
        self,
        quota_key: str,
        entitlement: Dict[str, Any],
        requested_amount: int = 1
    ) -> EntitlementDecision:
        """
        Check if quota is available for requested amount.
        
        Args:
            quota_key: Quota identifier
            entitlement: Computed entitlement data
            requested_amount: Amount to check
            
        Returns:
            EntitlementDecision: Quota availability decision
        """
        quotas = entitlement.get("quotas", {})
        quota_data = quotas.get(quota_key, {})
        
        if not quota_data:
            return EntitlementDecision(
                False,
                f"Quota '{quota_key}' not configured"
            )
        
        remaining = quota_data.get("remaining", 0)
        
        if remaining >= requested_amount:
            return EntitlementDecision(
                True,
                f"{remaining} units available",
                quota_data
            )
        
        return EntitlementDecision(
            False,
            f"Quota exceeded: {remaining}/{quota_data.get('limit')} remaining",
            quota_data
        )
    
    def _is_subscription_active(
        self,
        subscription: Dict[str, Any],
        current_time: datetime
    ) -> bool:
        """Check if subscription is currently active."""
        status = subscription.get("status")
        
        if status not in ["active", "trial"]:
            return False
        
        ends_at_str = subscription.get("ends_at")
        if ends_at_str:
            if isinstance(ends_at_str, str):
                ends_at = datetime.fromisoformat(ends_at_str.replace('Z', '+00:00'))
            else:
                ends_at = ends_at_str
            
            if current_time > ends_at:
                return False
        
        return True
    
    def _is_override_active(
        self,
        override: Dict[str, Any],
        current_time: datetime
    ) -> bool:
        """Check if override is currently active."""
        if not override.get("is_active", True):
            return False
        
        expires_at_str = override.get("expires_at")
        if expires_at_str:
            if isinstance(expires_at_str, str):
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            else:
                expires_at = expires_at_str
            
            if current_time > expires_at:
                return False
        
        return True


# Singleton instance
entitlement_service = EntitlementService()
