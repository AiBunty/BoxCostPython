"""
Subscription Management Service
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.models.subscription import (
    SubscriptionPlan,
    UserSubscription,
    SubscriptionStatus,
    PlanInterval,
)
from backend.models.payment import SubscriptionChange, Transaction, TransactionType, TransactionStatus
from backend.services.entitlement_service import entitlement_service


class SubscriptionService:
    """Service for managing user subscriptions."""

    @staticmethod
    def create_subscription(
        db: Session,
        user_id: int,
        tenant_id: int,
        plan_slug: str,
        payment_transaction_id: Optional[str] = None,
        trial_days: Optional[int] = None,
    ) -> UserSubscription:
        """
        Create a new subscription for a user.
        
        Args:
            db: Database session
            user_id: User ID
            tenant_id: Tenant ID
            plan_slug: Plan slug identifier
            payment_transaction_id: Payment transaction ID (if paid)
            trial_days: Override trial days (None = use plan default)
            
        Returns:
            Created UserSubscription
        """
        # Get plan
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.slug == plan_slug,
            SubscriptionPlan.is_active == True
        ).first()
        
        if not plan:
            raise ValueError(f"Plan not found: {plan_slug}")
        
        # Check if user already has active subscription
        existing = db.query(UserSubscription).filter(
            UserSubscription.user_id == user_id,
            UserSubscription.tenant_id == tenant_id,
            UserSubscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
        ).first()
        
        if existing:
            raise ValueError("User already has an active subscription")
        
        # Calculate dates
        now = datetime.utcnow()
        trial_period = trial_days if trial_days is not None else plan.trial_days
        
        # Determine status
        status = SubscriptionStatus.TRIAL if trial_period > 0 and not payment_transaction_id else SubscriptionStatus.ACTIVE
        
        # Calculate trial end
        trial_ends_at = None
        if status == SubscriptionStatus.TRIAL:
            trial_ends_at = now + timedelta(days=trial_period)
        
        # Calculate subscription end based on interval
        if plan.interval == PlanInterval.MONTHLY:
            ends_at = now + timedelta(days=30)
        elif plan.interval == PlanInterval.QUARTERLY:
            ends_at = now + timedelta(days=90)
        elif plan.interval == PlanInterval.YEARLY:
            ends_at = now + timedelta(days=365)
        else:  # LIFETIME
            ends_at = now + timedelta(days=36500)  # 100 years
        
        # Create subscription
        subscription = UserSubscription(
            user_id=user_id,
            tenant_id=tenant_id,
            plan_id=plan.id,
            status=status,
            starts_at=now,
            ends_at=ends_at,
            trial_ends_at=trial_ends_at,
            payment_transaction_id=payment_transaction_id,
            auto_renew=True,
            last_usage_reset=now,
        )
        
        db.add(subscription)
        db.flush()
        
        # Log the change
        change = SubscriptionChange(
            subscription_id=subscription.id,
            user_id=user_id,
            change_type="created",
            new_plan=plan.name,
            new_status=status.value,
            new_amount=int(plan.price * 100),  # Convert to cents/paise
            reason="Initial subscription creation",
            initiated_by="user",
            effective_at=now,
        )
        db.add(change)
        
        # Auto-provision entitlements based on plan features
        SubscriptionService._provision_entitlements(db, subscription, plan)
        
        db.commit()
        db.refresh(subscription)
        
        return subscription

    @staticmethod
    def _provision_entitlements(
        db: Session,
        subscription: UserSubscription,
        plan: SubscriptionPlan,
    ):
        """Auto-provision entitlements based on plan features."""
        # Plan features is a JSON dict: {feature_name: enabled}
        if not plan.features:
            return
        
        for feature_name, enabled in plan.features.items():
            if enabled:
                try:
                    # Get quota from plan quotas
                    quota_limit = None
                    if plan.quotas and feature_name in plan.quotas:
                        quota_limit = plan.quotas[feature_name]
                    
                    # Grant feature
                    entitlement_service.grant_user_feature(
                        db=db,
                        user_id=subscription.user_id,
                        tenant_id=subscription.tenant_id,
                        feature_name=feature_name,
                        quota_limit=quota_limit,
                        expires_at=subscription.ends_at,
                    )
                except ValueError:
                    # Feature doesn't exist, skip
                    pass

    @staticmethod
    def change_plan(
        db: Session,
        subscription_id: int,
        new_plan_slug: str,
        admin_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Dict:
        """
        Change subscription plan (upgrade/downgrade).
        
        Args:
            db: Database session
            subscription_id: Subscription ID
            new_plan_slug: New plan slug
            admin_id: Admin ID if initiated by admin
            reason: Reason for change
            
        Returns:
            Dict with proration details
        """
        subscription = db.query(UserSubscription).filter(
            UserSubscription.id == subscription_id
        ).first()
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        # Get old and new plans
        old_plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == subscription.plan_id
        ).first()
        
        new_plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.slug == new_plan_slug,
            SubscriptionPlan.is_active == True
        ).first()
        
        if not new_plan:
            raise ValueError(f"Plan not found: {new_plan_slug}")
        
        if old_plan.id == new_plan.id:
            raise ValueError("Already on this plan")
        
        # Calculate proration
        now = datetime.utcnow()
        days_remaining = (subscription.ends_at - now).days
        total_days = (subscription.ends_at - subscription.starts_at).days
        
        # Prorated refund/charge
        old_daily_rate = float(old_plan.price) / max(total_days, 1)
        new_daily_rate = float(new_plan.price) / max(total_days, 1)
        
        unused_amount = old_daily_rate * days_remaining
        new_amount = new_daily_rate * days_remaining
        proration_amount = int((new_amount - unused_amount) * 100)  # In cents
        
        # Determine if upgrade or downgrade
        change_type = "upgraded" if new_plan.price > old_plan.price else "downgraded"
        
        # Update subscription
        subscription.plan_id = new_plan.id
        
        # Log the change
        change = SubscriptionChange(
            subscription_id=subscription.id,
            user_id=subscription.user_id,
            change_type=change_type,
            old_plan=old_plan.name,
            new_plan=new_plan.name,
            old_status=subscription.status.value,
            new_status=subscription.status.value,
            old_amount=int(old_plan.price * 100),
            new_amount=int(new_plan.price * 100),
            proration_amount=proration_amount,
            proration_days=days_remaining,
            reason=reason or f"Plan {change_type}",
            initiated_by="admin" if admin_id else "user",
            admin_id=admin_id,
            effective_at=now,
        )
        db.add(change)
        
        # Reprovision entitlements
        SubscriptionService._provision_entitlements(db, subscription, new_plan)
        
        db.commit()
        
        return {
            "old_plan": old_plan.name,
            "new_plan": new_plan.name,
            "proration_amount": proration_amount,
            "proration_days": days_remaining,
            "change_type": change_type,
        }

    @staticmethod
    def cancel_subscription(
        db: Session,
        subscription_id: int,
        immediate: bool = False,
        reason: Optional[str] = None,
        admin_id: Optional[int] = None,
    ) -> UserSubscription:
        """
        Cancel a subscription.
        
        Args:
            db: Database session
            subscription_id: Subscription ID
            immediate: Cancel immediately vs at period end
            reason: Cancellation reason
            admin_id: Admin ID if initiated by admin
            
        Returns:
            Updated subscription
        """
        subscription = db.query(UserSubscription).filter(
            UserSubscription.id == subscription_id
        ).first()
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        if subscription.status == SubscriptionStatus.CANCELLED:
            raise ValueError("Subscription already cancelled")
        
        now = datetime.utcnow()
        
        if immediate:
            # Cancel immediately
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.ends_at = now
            subscription.cancelled_at = now
        else:
            # Cancel at period end
            subscription.auto_renew = False
            subscription.cancelled_at = now
        
        subscription.cancellation_reason = reason
        
        # Log the change
        change = SubscriptionChange(
            subscription_id=subscription.id,
            user_id=subscription.user_id,
            change_type="canceled",
            old_status=SubscriptionStatus.ACTIVE.value if subscription.status == SubscriptionStatus.CANCELLED else subscription.status.value,
            new_status=subscription.status.value,
            reason=reason or "User cancellation",
            initiated_by="admin" if admin_id else "user",
            admin_id=admin_id,
            effective_at=now if immediate else subscription.ends_at,
        )
        db.add(change)
        
        db.commit()
        db.refresh(subscription)
        
        return subscription

    @staticmethod
    def reactivate_subscription(
        db: Session,
        subscription_id: int,
        payment_transaction_id: Optional[str] = None,
    ) -> UserSubscription:
        """Reactivate a cancelled subscription."""
        subscription = db.query(UserSubscription).filter(
            UserSubscription.id == subscription_id
        ).first()
        
        if not subscription:
            raise ValueError("Subscription not found")
        
        if subscription.status not in [SubscriptionStatus.CANCELLED, SubscriptionStatus.EXPIRED]:
            raise ValueError("Subscription is already active")
        
        now = datetime.utcnow()
        
        # Get plan for duration
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == subscription.plan_id
        ).first()
        
        # Calculate new end date
        if plan.interval == PlanInterval.MONTHLY:
            ends_at = now + timedelta(days=30)
        elif plan.interval == PlanInterval.QUARTERLY:
            ends_at = now + timedelta(days=90)
        elif plan.interval == PlanInterval.YEARLY:
            ends_at = now + timedelta(days=365)
        else:
            ends_at = now + timedelta(days=36500)
        
        # Update subscription
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.starts_at = now
        subscription.ends_at = ends_at
        subscription.auto_renew = True
        subscription.cancelled_at = None
        subscription.payment_transaction_id = payment_transaction_id
        
        # Log the change
        change = SubscriptionChange(
            subscription_id=subscription.id,
            user_id=subscription.user_id,
            change_type="reactivated",
            old_status=SubscriptionStatus.CANCELLED.value,
            new_status=SubscriptionStatus.ACTIVE.value,
            reason="Subscription reactivated",
            initiated_by="user",
            effective_at=now,
        )
        db.add(change)
        
        db.commit()
        db.refresh(subscription)
        
        return subscription

    @staticmethod
    def get_user_subscription(
        db: Session,
        user_id: int,
        tenant_id: int,
    ) -> Optional[UserSubscription]:
        """Get user's active subscription."""
        return db.query(UserSubscription).filter(
            UserSubscription.user_id == user_id,
            UserSubscription.tenant_id == tenant_id,
            UserSubscription.status.in_([
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIAL
            ])
        ).first()

    @staticmethod
    def list_subscription_history(
        db: Session,
        user_id: int,
        limit: int = 10,
    ) -> List[SubscriptionChange]:
        """Get subscription change history for a user."""
        return db.query(SubscriptionChange).filter(
            SubscriptionChange.user_id == user_id
        ).order_by(SubscriptionChange.created_at.desc()).limit(limit).all()


subscription_service = SubscriptionService()
