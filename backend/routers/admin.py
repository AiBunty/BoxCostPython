"""Admin panel API routers."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from datetime import datetime

from backend.database import get_db
from backend.middleware.auth import require_admin
from backend.models.admin import Admin
from backend.models.user import User
from backend.models.tenant import Tenant
from backend.models.subscription import UserSubscription, SubscriptionPlan, SubscriptionOverride
from backend.models.support import SupportTicket, SupportMessage, SupportAgent
from backend.models.audit import AdminAuditLog
from shared.schemas import (
    AdminLoginResponse,
    UserResponse,
    SubscriptionResponse,
    SupportTicketResponse,
    PaginatedResponse
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ============================================================================
# USER MANAGEMENT
# ============================================================================

@router.get("/users", response_model=PaginatedResponse)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """List all users with pagination and filters."""
    query = select(User)
    
    # Apply filters
    filters = []
    if search:
        filters.append(
            or_(
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
                User.clerk_user_id.ilike(f"%{search}%")
            )
        )
    if status:
        filters.append(User.is_active == (status == "active"))
    
    if filters:
        query = query.where(and_(*filters))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Paginate
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return {
        "items": users,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """Get detailed user information."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get tenant info
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    # Get subscription info
    subscription_result = await db.execute(
        select(UserSubscription)
        .where(UserSubscription.user_id == user_id)
        .order_by(UserSubscription.created_at.desc())
        .limit(1)
    )
    subscription = subscription_result.scalar_one_or_none()
    
    return {
        "user": user,
        "tenant": tenant,
        "subscription": subscription
    }


@router.patch("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """Activate a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    await db.commit()
    
    # Audit log
    audit_log = AdminAuditLog(
        admin_id=admin.id,
        action="user.activate",
        resource_type="user",
        resource_id=user_id,
        after_state={"is_active": True}
    )
    db.add(audit_log)
    await db.commit()
    
    return {"message": "User activated successfully"}


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    reason: str,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """Deactivate a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    await db.commit()
    
    # Audit log
    audit_log = AdminAuditLog(
        admin_id=admin.id,
        action="user.deactivate",
        resource_type="user",
        resource_id=user_id,
        after_state={"is_active": False, "reason": reason}
    )
    db.add(audit_log)
    await db.commit()
    
    return {"message": "User deactivated successfully"}


# ============================================================================
# SUBSCRIPTION MANAGEMENT
# ============================================================================

@router.get("/subscriptions", response_model=PaginatedResponse)
async def list_subscriptions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    plan_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """List all subscriptions with pagination."""
    query = select(UserSubscription)
    
    filters = []
    if status:
        filters.append(UserSubscription.status == status)
    if plan_id:
        filters.append(UserSubscription.plan_id == plan_id)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Paginate
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    subscriptions = result.scalars().all()
    
    return {
        "items": subscriptions,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


@router.post("/subscriptions/{subscription_id}/grant-override")
async def grant_subscription_override(
    subscription_id: int,
    override_type: str,
    feature_key: Optional[str] = None,
    quota_key: Optional[str] = None,
    quota_value: Optional[int] = None,
    expires_days: int = 30,
    reason: str = "",
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """Grant temporary subscription override."""
    result = await db.execute(
        select(UserSubscription).where(UserSubscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    expires_at = datetime.utcnow() + timedelta(days=expires_days)
    
    override = SubscriptionOverride(
        subscription_id=subscription_id,
        override_type=override_type,
        feature_key=feature_key,
        quota_key=quota_key,
        quota_value=quota_value,
        reason=reason,
        granted_by_admin_id=admin.id,
        expires_at=expires_at
    )
    db.add(override)
    await db.commit()
    
    # Audit log
    audit_log = AdminAuditLog(
        admin_id=admin.id,
        action="subscription.grant_override",
        resource_type="subscription",
        resource_id=subscription_id,
        after_state={
            "override_type": override_type,
            "feature_key": feature_key,
            "quota_key": quota_key,
            "expires_at": expires_at.isoformat()
        }
    )
    db.add(audit_log)
    await db.commit()
    
    return {"message": "Override granted successfully", "override_id": override.id}


@router.delete("/subscriptions/overrides/{override_id}")
async def revoke_subscription_override(
    override_id: int,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """Revoke a subscription override."""
    result = await db.execute(
        select(SubscriptionOverride).where(SubscriptionOverride.id == override_id)
    )
    override = result.scalar_one_or_none()
    
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")
    
    override.is_active = False
    await db.commit()
    
    # Audit log
    audit_log = AdminAuditLog(
        admin_id=admin.id,
        action="subscription.revoke_override",
        resource_type="subscription_override",
        resource_id=override_id
    )
    db.add(audit_log)
    await db.commit()
    
    return {"message": "Override revoked successfully"}


# ============================================================================
# SUPPORT TICKET MANAGEMENT
# ============================================================================

@router.get("/support/tickets", response_model=PaginatedResponse)
async def list_support_tickets(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """List support tickets."""
    query = select(SupportTicket)
    
    filters = []
    if status:
        filters.append(SupportTicket.status == status)
    if priority:
        filters.append(SupportTicket.priority == priority)
    if assigned_to:
        filters.append(SupportTicket.assigned_to == assigned_to)
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.order_by(SupportTicket.created_at.desc())
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Paginate
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    tickets = result.scalars().all()
    
    return {
        "items": tickets,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


@router.post("/support/tickets/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: int,
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """Assign ticket to support agent."""
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket.assigned_to = agent_id
    ticket.status = "in_progress"
    await db.commit()
    
    return {"message": "Ticket assigned successfully"}


@router.post("/support/tickets/{ticket_id}/close")
async def close_ticket(
    ticket_id: int,
    resolution: str,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """Close a support ticket."""
    result = await db.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket.status = "resolved"
    ticket.resolved_at = datetime.utcnow()
    await db.commit()
    
    # Add resolution message
    message = SupportMessage(
        ticket_id=ticket_id,
        sender_type="agent",
        sender_id=admin.id,
        message=f"Ticket resolved: {resolution}",
        is_internal=False
    )
    db.add(message)
    await db.commit()
    
    return {"message": "Ticket closed successfully"}


# ============================================================================
# ANALYTICS & REPORTS
# ============================================================================

@router.get("/analytics/dashboard")
async def get_admin_dashboard(
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """Get admin dashboard analytics."""
    # Total users
    total_users = await db.scalar(select(func.count(User.id)))
    
    # Active subscriptions
    active_subscriptions = await db.scalar(
        select(func.count(UserSubscription.id))
        .where(UserSubscription.status == "active")
    )
    
    # Open tickets
    open_tickets = await db.scalar(
        select(func.count(SupportTicket.id))
        .where(SupportTicket.status.in_(["open", "in_progress"]))
    )
    
    # Revenue this month (mock for now)
    revenue_this_month = 0  # TODO: Calculate from invoice data
    
    return {
        "total_users": total_users,
        "active_subscriptions": active_subscriptions,
        "open_tickets": open_tickets,
        "revenue_this_month": revenue_this_month
    }


from datetime import timedelta

