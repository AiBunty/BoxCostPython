"""Subscription API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List
from datetime import datetime

from backend.database import get_db
from backend.middleware.auth import get_current_user, get_tenant_context
from backend.models.user import User
from backend.models.subscription import (
    SubscriptionPlan,
    UserSubscription,
    SubscriptionOverride,
    UserFeatureUsage
)
from backend.services.entitlement import entitlement_service
from shared.schemas import (
    SubscriptionPlanResponse,
    UserSubscriptionResponse,
    EntitlementResponse
)

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def list_subscription_plans(
    db: AsyncSession = Depends(get_db)
):
    """
    List all available subscription plans.
    Public endpoint - no authentication required.
    """
    result = await db.execute(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.is_active == True)
        .order_by(SubscriptionPlan.price_monthly)
    )
    plans = result.scalars().all()
    
    return [SubscriptionPlanResponse.from_orm(plan) for plan in plans]


@router.get("/plans/{plan_id}", response_model=SubscriptionPlanResponse)
async def get_subscription_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific plan.
    """
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return SubscriptionPlanResponse.from_orm(plan)


@router.get("/my-subscription", response_model=UserSubscriptionResponse)
async def get_my_subscription(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get current user's subscription details.
    """
    result = await db.execute(
        select(UserSubscription)
        .where(UserSubscription.user_id == user.id)
        .order_by(UserSubscription.created_at.desc())
        .limit(1)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    return UserSubscriptionResponse.from_orm(subscription)


@router.get("/my-entitlements", response_model=EntitlementResponse)
async def get_my_entitlements(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get computed entitlements for current user.
    Returns all features, quotas, and overrides.
    """
    # Get subscription
    subscription_result = await db.execute(
        select(UserSubscription)
        .where(UserSubscription.user_id == user.id)
        .order_by(UserSubscription.created_at.desc())
        .limit(1)
    )
    subscription = subscription_result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    # Get plan
    plan_result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == subscription.plan_id)
    )
    plan = plan_result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")
    
    # Get active overrides
    overrides_result = await db.execute(
        select(SubscriptionOverride)
        .where(
            and_(
                SubscriptionOverride.subscription_id == subscription.id,
                SubscriptionOverride.is_active == True
            )
        )
    )
    overrides = overrides_result.scalars().all()
    
    # Get usage data
    usage_result = await db.execute(
        select(UserFeatureUsage)
        .where(UserFeatureUsage.user_id == user.id)
    )
    usage_records = usage_result.scalars().all()
    usage_dict = {u.quota_key: u.usage_count for u in usage_records}
    
    # Calculate entitlements
    subscription_dict = {
        "id": subscription.id,
        "status": subscription.status,
        "ends_at": subscription.ends_at.isoformat() if subscription.ends_at else None
    }
    
    plan_dict = {
        "name": plan.name,
        "features": plan.features or {},
        "quotas": plan.quotas or {}
    }
    
    overrides_list = [
        {
            "override_type": o.override_type,
            "feature_key": o.feature_key,
            "quota_key": o.quota_key,
            "quota_value": o.quota_value,
            "expires_at": o.expires_at.isoformat() if o.expires_at else None,
            "is_active": o.is_active
        }
        for o in overrides
    ]
    
    entitlement = entitlement_service.calculate_entitlement(
        subscription=subscription_dict,
        plan=plan_dict,
        overrides=overrides_list,
        usage=usage_dict
    )
    
    return entitlement


@router.post("/check-feature/{feature_key}")
async def check_feature_access(
    feature_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Check if user has access to a specific feature.
    """
    # Get entitlements (reuse logic)
    entitlement = await get_my_entitlements(db=db, user=user)
    
    # Check feature
    decision = entitlement_service.check_feature_access(feature_key, entitlement)
    
    return {
        "feature_key": feature_key,
        "allowed": decision.allowed,
        "reason": decision.reason,
        "metadata": decision.metadata
    }


@router.post("/check-quota/{quota_key}")
async def check_quota_available(
    quota_key: str,
    amount: int = 1,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Check if user has available quota.
    """
    # Get entitlements
    entitlement = await get_my_entitlements(db=db, user=user)
    
    # Check quota
    decision = entitlement_service.check_quota_available(quota_key, entitlement, amount)
    
    return {
        "quota_key": quota_key,
        "requested_amount": amount,
        "allowed": decision.allowed,
        "reason": decision.reason,
        "metadata": decision.metadata
    }


@router.post("/increment-usage/{quota_key}")
async def increment_usage(
    quota_key: str,
    amount: int = 1,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Increment usage counter for a quota.
    Must be called after consuming a quota-limited resource.
    """
    # Check if quota is available first
    entitlement = await get_my_entitlements(db=db, user=user)
    decision = entitlement_service.check_quota_available(quota_key, entitlement, amount)
    
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
    
    # Find or create usage record
    result = await db.execute(
        select(UserFeatureUsage).where(
            and_(
                UserFeatureUsage.user_id == user.id,
                UserFeatureUsage.quota_key == quota_key
            )
        )
    )
    usage = result.scalar_one_or_none()
    
    if usage:
        usage.usage_count += amount
        usage.last_used_at = datetime.utcnow()
    else:
        usage = UserFeatureUsage(
            user_id=user.id,
            quota_key=quota_key,
            usage_count=amount,
            last_used_at=datetime.utcnow()
        )
        db.add(usage)
    
    await db.commit()
    
    return {
        "quota_key": quota_key,
        "incremented": amount,
        "new_total": usage.usage_count
    }
