"""
Advanced reporting and analytics endpoints.
Includes revenue, subscriptions, invoices, and usage insights.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from backend.database import get_db
from backend.middleware.auth import get_current_user
from backend.models.payment import Transaction, TransactionStatus
from backend.models.subscription import UserSubscription, SubscriptionStatus, UserFeatureUsage
from backend.models.invoice import Invoice, InvoiceStatus
from backend.services.cache_service import cache_service
from backend.routers.realtime import manager
from backend.models.user import User

router = APIRouter(prefix="/api/reports", tags=["Reports"])

CACHE_TTL = 300  # seconds


def _decimal_or_zero(value) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _get_date_range(days: int) -> tuple[datetime, datetime]:
    now = datetime.utcnow()
    return now - timedelta(days=days), now


def _serialize_decimal(value: Decimal) -> float:
    return float(round(value, 2))


@router.get("/summary")
def get_report_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get aggregated business metrics (cached for 5 minutes).
    """
    cache_key = "reports:summary"
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    start_30d, now = _get_date_range(30)

    # Revenue metrics
    revenue_q = db.query(
        func.sum(Transaction.amount).label("gross"),
        func.count(Transaction.id).label("count")
    ).filter(
        Transaction.status == TransactionStatus.SUCCEEDED.value,
        Transaction.type == "payment",
        Transaction.created_at >= start_30d
    )
    revenue_row = revenue_q.first()
    gross_revenue = _decimal_or_zero(revenue_row.gross)
    payment_count = revenue_row.count or 0
    avg_payment = gross_revenue / payment_count if payment_count else Decimal("0")

    refunds_q = db.query(func.sum(Transaction.amount)).filter(
        Transaction.status == TransactionStatus.REFUNDED.value,
        Transaction.created_at >= start_30d
    )
    refunds = _decimal_or_zero(refunds_q.scalar())

    # Subscription metrics
    active_subscriptions = db.query(UserSubscription).filter(
        UserSubscription.status == SubscriptionStatus.ACTIVE
    ).count()

    new_subscriptions = db.query(UserSubscription).filter(
        UserSubscription.created_at >= start_30d
    ).count()

    churned = db.query(UserSubscription).filter(
        and_(
            UserSubscription.status == SubscriptionStatus.CANCELLED,
            UserSubscription.updated_at != None,
            UserSubscription.updated_at >= start_30d
        )
    ).count()

    # Invoice metrics
    invoices_total = db.query(Invoice).count()
    invoices_paid = db.query(Invoice).filter(Invoice.status == InvoiceStatus.PAID).count()
    invoices_overdue = db.query(Invoice).filter(
        and_(
            Invoice.due_date != None,
            Invoice.due_date < now,
            Invoice.status != InvoiceStatus.PAID
        )
    ).count()
    avg_invoice_amount = _decimal_or_zero(db.query(func.avg(Invoice.total_amount)).scalar())

    # Usage metrics (top features)
    top_usage = db.query(
        UserFeatureUsage.feature_key,
        func.sum(UserFeatureUsage.usage_count).label("usage")
    ).group_by(UserFeatureUsage.feature_key).order_by(func.sum(UserFeatureUsage.usage_count).desc()).limit(5).all()
    usage_trends = [
        {"feature": row.feature_key, "usage": int(row.usage)}
        for row in top_usage
    ]

    result = {
        "generated_at": datetime.utcnow().isoformat(),
        "revenue": {
            "gross_30d": _serialize_decimal(gross_revenue / 100),
            "refunds_30d": _serialize_decimal(refunds / 100),
            "net_30d": _serialize_decimal((gross_revenue - refunds) / 100),
            "average_payment_30d": _serialize_decimal(avg_payment / 100),
            "payments_count_30d": payment_count,
        },
        "subscriptions": {
            "active": active_subscriptions,
            "new_30d": new_subscriptions,
            "churned_30d": churned,
        },
        "invoices": {
            "total": invoices_total,
            "paid": invoices_paid,
            "overdue": invoices_overdue,
            "average_amount": _serialize_decimal(avg_invoice_amount),
        },
        "usage": {
            "top_features": usage_trends
        }
    }

    cache_service.set(cache_key, result, ttl_seconds=CACHE_TTL)
    return result


@router.post("/refresh", status_code=status.HTTP_202_ACCEPTED)
def refresh_reports(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger report cache refresh in background and notify websocket clients.
    """
    def _refresh():
        cache_service.clear_prefix("reports:")
        summary = get_report_summary(db=db, current_user=current_user)
        # Notify active WebSocket clients
        try:
            import asyncio
            asyncio.run(manager.broadcast({"type": "reports:refreshed", "timestamp": datetime.utcnow().isoformat()}))
        except Exception:
            pass
        return summary

    background_tasks.add_task(_refresh)
    return {"message": "Report refresh scheduled"}


@router.get("/financials")
def financial_report(
    months: int = 6,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Financial report with monthly revenue and refunds.
    """
    if months < 1 or months > 24:
        raise HTTPException(status_code=400, detail="months must be between 1 and 24")

    now = datetime.utcnow()
    start_date = now - timedelta(days=30 * months)

    rows = db.query(
        func.date_trunc('month', Transaction.created_at).label('month'),
        func.sum(Transaction.amount).label('revenue'),
        func.sum(func.case([(Transaction.status == TransactionStatus.REFUNDED.value, Transaction.amount)], else_=0)).label('refunds'),
        func.count(Transaction.id).label('payments')
    ).filter(
        Transaction.created_at >= start_date,
        Transaction.type == "payment"
    ).group_by('month').order_by('month').all()

    data = []
    for row in rows:
        data.append({
            "month": row.month.date().isoformat() if row.month else None,
            "revenue": _serialize_decimal(_decimal_or_zero(row.revenue) / 100),
            "refunds": _serialize_decimal(_decimal_or_zero(row.refunds) / 100),
            "payments": row.payments,
        })

    return {"period_months": months, "series": data}
