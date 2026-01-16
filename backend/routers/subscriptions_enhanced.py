"""
Enhanced Subscription Management API
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_user, get_current_admin
from backend.models.user import User
from backend.models.admin import Admin
from backend.models.subscription import UserSubscription, SubscriptionPlan
from backend.models.payment import SubscriptionChange
from backend.services.subscription_service import subscription_service


# Schemas
class SubscriptionCreateRequest(BaseModel):
    plan_slug: str
    payment_transaction_id: Optional[str] = None
    trial_days: Optional[int] = None


class PlanChangeRequest(BaseModel):
    new_plan_slug: str
    reason: Optional[str] = None


class SubscriptionCancelRequest(BaseModel):
    immediate: bool = False
    reason: Optional[str] = None


class SubscriptionResponse(BaseModel):
    id: int
    plan_id: int
    status: str
    starts_at: str
    ends_at: str
    trial_ends_at: Optional[str]
    auto_renew: bool
    cancelled_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class SubscriptionChangeResponse(BaseModel):
    id: int
    change_type: str
    old_plan: Optional[str]
    new_plan: Optional[str]
    old_status: Optional[str]
    new_status: Optional[str]
    proration_amount: Optional[int]
    reason: Optional[str]
    effective_at: str
    created_at: str

    class Config:
        from_attributes = True


router = APIRouter(prefix="/api/subscriptions-v2", tags=["Subscriptions V2"])


# User endpoints
@router.get("/me", response_model=SubscriptionResponse)
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's active subscription."""
    subscription = subscription_service.get_user_subscription(
        db=db,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id
    )
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    return subscription


@router.post("/me", response_model=SubscriptionResponse)
async def create_my_subscription(
    data: SubscriptionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new subscription for current user."""
    try:
        subscription = subscription_service.create_subscription(
            db=db,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            plan_slug=data.plan_slug,
            payment_transaction_id=data.payment_transaction_id,
            trial_days=data.trial_days,
        )
        return subscription
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/me/change-plan")
async def change_my_plan(
    data: PlanChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change subscription plan (upgrade/downgrade)."""
    # Get current subscription
    subscription = subscription_service.get_user_subscription(
        db=db,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id
    )
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    try:
        result = subscription_service.change_plan(
            db=db,
            subscription_id=subscription.id,
            new_plan_slug=data.new_plan_slug,
            reason=data.reason,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/me/cancel")
async def cancel_my_subscription(
    data: SubscriptionCancelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel current subscription."""
    subscription = subscription_service.get_user_subscription(
        db=db,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id
    )
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    try:
        updated = subscription_service.cancel_subscription(
            db=db,
            subscription_id=subscription.id,
            immediate=data.immediate,
            reason=data.reason,
        )
        return updated
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/me/reactivate", response_model=SubscriptionResponse)
async def reactivate_my_subscription(
    payment_transaction_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reactivate a cancelled subscription."""
    # Find most recent subscription
    subscription = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.tenant_id == current_user.tenant_id
    ).order_by(UserSubscription.created_at.desc()).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    try:
        reactivated = subscription_service.reactivate_subscription(
            db=db,
            subscription_id=subscription.id,
            payment_transaction_id=payment_transaction_id,
        )
        return reactivated
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/me/history", response_model=List[SubscriptionChangeResponse])
async def get_my_subscription_history(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get subscription change history."""
    history = subscription_service.list_subscription_history(
        db=db,
        user_id=current_user.id,
        limit=limit
    )
    return history


# Admin endpoints
@router.get("/admin/users/{user_id}", response_model=SubscriptionResponse)
async def get_user_subscription_admin(
    user_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get user's subscription (admin only)."""
    from backend.models.user import User
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    subscription = subscription_service.get_user_subscription(
        db=db,
        user_id=user_id,
        tenant_id=user.tenant_id
    )
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    return subscription


@router.post("/admin/users/{user_id}/cancel")
async def cancel_user_subscription_admin(
    user_id: int,
    data: SubscriptionCancelRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Cancel user's subscription (admin only)."""
    from backend.models.user import User
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    subscription = subscription_service.get_user_subscription(
        db=db,
        user_id=user_id,
        tenant_id=user.tenant_id
    )
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    try:
        updated = subscription_service.cancel_subscription(
            db=db,
            subscription_id=subscription.id,
            immediate=data.immediate,
            reason=data.reason,
            admin_id=current_admin.id,
        )
        return updated
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/admin/users/{user_id}/change-plan")
async def change_user_plan_admin(
    user_id: int,
    data: PlanChangeRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Change user's plan (admin only)."""
    from backend.models.user import User
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    subscription = subscription_service.get_user_subscription(
        db=db,
        user_id=user_id,
        tenant_id=user.tenant_id
    )
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    try:
        result = subscription_service.change_plan(
            db=db,
            subscription_id=subscription.id,
            new_plan_slug=data.new_plan_slug,
            admin_id=current_admin.id,
            reason=data.reason or "Admin plan change",
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
