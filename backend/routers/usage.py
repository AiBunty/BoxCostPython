"""
Usage tracking and reporting API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from decimal import Decimal

from backend.database import get_db
from backend.middleware.auth import get_current_user, get_current_tenant_id
from backend.services.usage_tracking_service import UsageTrackingService, UsageMetrics
from backend.models.subscription import UserSubscription
from backend.models.user import User

router = APIRouter(prefix="/api/usage", tags=["Usage Tracking"])


class UsageRecordCreate(BaseModel):
    """Schema for creating a usage record."""
    metric_name: str
    quantity: float
    metadata: Optional[dict] = None


class UsageSummaryResponse(BaseModel):
    """Schema for usage summary response."""
    user_id: int
    period: dict
    metrics: list


class OverageChargesResponse(BaseModel):
    """Schema for overage charges response."""
    subscription_id: int
    billing_period: dict
    charges: list
    total_overage: float


class UsageAlertsResponse(BaseModel):
    """Schema for usage alerts response."""
    subscription_id: int
    alerts: list


@router.post("/record", status_code=status.HTTP_201_CREATED)
def record_usage(
    record: UsageRecordCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Record a usage event for metered billing.
    
    **Requires authentication**
    
    Common metric names:
    - `quotes_generated`
    - `invoices_generated`
    - `api_calls`
    - `storage_gb`
    - `email_sent`
    - `pdf_generated`
    """
    service = UsageTrackingService(db)
    
    usage_record = service.record_usage(
        user_id=current_user.id,
        tenant_id=tenant_id,
        metric_name=record.metric_name,
        quantity=Decimal(str(record.quantity)),
        metadata=record.metadata
    )
    
    return {
        "id": usage_record.id,
        "metric_name": usage_record.metric_name,
        "quantity": float(usage_record.quantity),
        "recorded_at": usage_record.recorded_at.isoformat(),
        "message": "Usage recorded successfully"
    }


@router.get("/summary", response_model=UsageSummaryResponse)
def get_usage_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    metric_name: Optional[str] = Query(None, description="Filter by specific metric"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get usage summary for current user within a date range.
    
    **Requires authentication**
    
    If no dates provided, returns current month's usage.
    """
    service = UsageTrackingService(db)
    
    # Default to current month if no dates provided
    if not start_date:
        now = datetime.utcnow()
        start_dt = datetime(now.year, now.month, 1)
    else:
        start_dt = datetime.fromisoformat(start_date)
    
    if not end_date:
        now = datetime.utcnow()
        end_dt = now
    else:
        end_dt = datetime.fromisoformat(end_date)
    
    summary = service.get_usage_summary(
        user_id=current_user.id,
        start_date=start_dt,
        end_date=end_dt,
        metric_name=metric_name
    )
    
    return summary


@router.get("/current-period")
def get_current_period_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get usage for current billing period based on user's subscription.
    
    **Requires authentication**
    """
    service = UsageTrackingService(db)
    
    # Get user's active subscription
    subscription = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == 'ACTIVE'
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Get current billing period
    start_date, end_date = service.get_current_billing_period(subscription)
    
    # Get usage summary
    summary = service.get_usage_summary(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )
    
    return {
        "subscription_id": subscription.id,
        "plan_name": subscription.plan.name,
        "billing_cycle": subscription.billing_cycle,
        "current_period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "usage": summary
    }


@router.get("/overage-charges", response_model=OverageChargesResponse)
def get_overage_charges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate overage charges for current billing period.
    
    **Requires authentication**
    
    Returns charges for usage exceeding plan limits.
    """
    service = UsageTrackingService(db)
    
    # Get user's active subscription
    subscription = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == 'ACTIVE'
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Get current period usage
    start_date, end_date = service.get_current_billing_period(subscription)
    usage_summary = service.get_usage_summary(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )
    
    # Calculate overages
    overages = service.calculate_overage_charges(subscription, usage_summary)
    
    return overages


@router.get("/alerts", response_model=UsageAlertsResponse)
def get_usage_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get usage alerts for current billing period.
    
    **Requires authentication**
    
    Returns alerts when usage exceeds 80%, 90%, 100%, or 110% of plan limits.
    """
    service = UsageTrackingService(db)
    
    # Get user's active subscription
    subscription = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == 'ACTIVE'
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Check alerts
    alerts = service.check_usage_alerts(subscription)
    
    return {
        "subscription_id": subscription.id,
        "alerts": alerts
    }


@router.get("/billing-estimate")
def get_billing_estimate(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get estimated billing amount for current period including overages.
    
    **Requires authentication**
    """
    service = UsageTrackingService(db)
    
    # Get user's active subscription
    subscription = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == 'ACTIVE'
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Get complete billing data
    billing_data = service.aggregate_usage_for_billing(subscription.id)
    
    return billing_data


@router.get("/metrics")
def get_available_metrics():
    """
    Get list of available usage metrics.
    
    Returns metric names and descriptions for tracking.
    """
    metrics = [
        {
            "name": UsageMetrics.QUOTES_GENERATED,
            "description": "Number of quotes generated",
            "unit": "count"
        },
        {
            "name": UsageMetrics.INVOICES_GENERATED,
            "description": "Number of invoices generated",
            "unit": "count"
        },
        {
            "name": UsageMetrics.API_CALLS,
            "description": "Number of API calls made",
            "unit": "count"
        },
        {
            "name": UsageMetrics.STORAGE_GB,
            "description": "Storage used in gigabytes",
            "unit": "GB"
        },
        {
            "name": UsageMetrics.USERS_ACTIVE,
            "description": "Number of active users",
            "unit": "count"
        },
        {
            "name": UsageMetrics.SUPPORT_TICKETS,
            "description": "Number of support tickets created",
            "unit": "count"
        },
        {
            "name": UsageMetrics.EMAIL_SENT,
            "description": "Number of emails sent",
            "unit": "count"
        },
        {
            "name": UsageMetrics.PDF_GENERATED,
            "description": "Number of PDFs generated",
            "unit": "count"
        },
        {
            "name": UsageMetrics.WEBHOOK_CALLS,
            "description": "Number of webhook calls received",
            "unit": "count"
        },
        {
            "name": UsageMetrics.EXPORT_OPERATIONS,
            "description": "Number of data exports",
            "unit": "count"
        }
    ]
    
    return {"metrics": metrics}
