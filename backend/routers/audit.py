"""Audit logs API router."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_admin
from backend.models.admin import Admin
from backend.models.audit import AdminAuditLog, AuthAuditLog, AdminLoginAuditLog
from pydantic import BaseModel, ConfigDict


# Schemas
class AdminAuditLogResponse(BaseModel):
    id: int
    admin_id: int
    action: str
    action_category: str
    description: str
    target_type: Optional[str]
    target_id: Optional[int]
    before_state: Optional[dict]
    after_state: Optional[dict]
    ip_address: Optional[str]
    user_agent: Optional[str]
    success: str
    error_message: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthAuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    email: Optional[str]
    event_type: str
    auth_method: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    location: Optional[str]
    success: str
    failure_reason: Optional[str]
    event_metadata: Optional[dict]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminLoginAuditLogResponse(BaseModel):
    id: int
    admin_id: Optional[int]
    username: Optional[str]
    event_type: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    success: str
    failure_reason: Optional[str]
    two_factor_used: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("/admin-actions", response_model=List[AdminAuditLogResponse])
async def list_admin_actions(
    admin_id: Optional[int] = Query(None),
    action_category: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    target_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List admin action logs with optional filters."""
    query = db.query(AdminAuditLog)

    if admin_id:
        query = query.filter(AdminAuditLog.admin_id == admin_id)
    if action_category:
        query = query.filter(AdminAuditLog.action_category == action_category)
    if target_type:
        query = query.filter(AdminAuditLog.target_type == target_type)
    if target_id:
        query = query.filter(AdminAuditLog.target_id == target_id)
    if start_date:
        query = query.filter(AdminAuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AdminAuditLog.created_at <= end_date)

    logs = (
        query.order_by(AdminAuditLog.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return [AdminAuditLogResponse.model_validate(log) for log in logs]


@router.get("/auth-events", response_model=List[AuthAuditLogResponse])
async def list_auth_events(
    user_id: Optional[int] = Query(None),
    event_type: Optional[str] = Query(None),
    success: Optional[str] = Query(None),
    search: Optional[str] = Query(None, min_length=3),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List authentication events with optional filters."""
    query = db.query(AuthAuditLog)

    if user_id:
        query = query.filter(AuthAuditLog.user_id == user_id)
    if event_type:
        query = query.filter(AuthAuditLog.event_type == event_type)
    if success:
        query = query.filter(AuthAuditLog.success == success)
    if search:
        ilike_term = f"%{search}%"
        query = query.filter(
            or_(
                AuthAuditLog.email.ilike(ilike_term),
                AuthAuditLog.ip_address.ilike(ilike_term),
            )
        )
    if start_date:
        query = query.filter(AuthAuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuthAuditLog.created_at <= end_date)

    logs = (
        query.order_by(AuthAuditLog.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return [AuthAuditLogResponse.model_validate(log) for log in logs]


@router.get("/admin-logins", response_model=List[AdminLoginAuditLogResponse])
async def list_admin_logins(
    admin_id: Optional[int] = Query(None),
    event_type: Optional[str] = Query(None),
    success: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List admin login/logout events."""
    query = db.query(AdminLoginAuditLog)

    if admin_id:
        query = query.filter(AdminLoginAuditLog.admin_id == admin_id)
    if event_type:
        query = query.filter(AdminLoginAuditLog.event_type == event_type)
    if success:
        query = query.filter(AdminLoginAuditLog.success == success)
    if start_date:
        query = query.filter(AdminLoginAuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AdminLoginAuditLog.created_at <= end_date)

    logs = (
        query.order_by(AdminLoginAuditLog.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return [AdminLoginAuditLogResponse.model_validate(log) for log in logs]


@router.get("/admin-actions/{log_id}", response_model=AdminAuditLogResponse)
async def get_admin_action_detail(
    log_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get detailed information about a specific admin action."""
    log = db.query(AdminAuditLog).filter(AdminAuditLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log not found")
    return AdminAuditLogResponse.model_validate(log)
