"""Admin panel APIs with RBAC, staff, tickets, coupons, and analytics."""
from __future__ import annotations

import csv
import io
import json
import random
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session
from passlib.hash import bcrypt

from backend.database import get_db
from backend.middleware.auth import get_current_admin
from backend.models.admin import Admin, AdminSession
from backend.models.audit import AdminAuditLog
from backend.models.coupon import Coupon, CouponStatus, CouponType, CouponUsage
from backend.models.payment import Transaction, TransactionStatus
from backend.models.subscription import SubscriptionStatus, UserSubscription
from backend.models.support import (
	SupportMessage,
	SupportTicket,
	TicketPriority,
	TicketStatus,
)
from backend.models.user import User
from shared.schemas import (
	PaginatedResponse,
	SupportMessageResponse,
	SupportTicketDetailResponse,
	SupportTicketResponse,
)


router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# RBAC Helpers
# ---------------------------------------------------------------------------
PERMISSION_MATRIX: Dict[str, set] = {
	"SUPER_ADMIN": {
		"create_staff",
		"list_staff",
		"disable_staff",
		"list_users",
		"view_user",
		"activate_user",
		"deactivate_user",
		"create_ticket",
		"list_tickets",
		"view_ticket",
		"assign_ticket",
		"resolve_ticket",
		"add_ticket_note",
		"create_coupon",
		"list_coupons",
		"assign_coupon",
		"view_staff_analytics",
		"view_ticket_analytics",
		"view_revenue_analytics",
		"view_audit_logs",
		"export_audit_logs",
	},
	"SUPPORT_STAFF": {
		"list_tickets",
		"view_ticket",
		"assign_ticket",
		"resolve_ticket",
		"add_ticket_note",
	},
	"MARKETING_STAFF": {
		"create_coupon",
		"list_coupons",
		"assign_coupon",
		"view_staff_analytics",
	},
	"FINANCE_ADMIN": {
		"view_staff_analytics",
		"view_ticket_analytics",
		"view_revenue_analytics",
		"view_audit_logs",
	},
}


def _normalize_role(role: Optional[str]) -> str:
	return (role or "").upper()


def _get_permissions(admin: Admin) -> set:
	perms = set(PERMISSION_MATRIX.get(_normalize_role(admin.role), set()))
	if admin.permissions:
		try:
			custom = json.loads(admin.permissions)
			if isinstance(custom, list):
				perms.update(str(p) for p in custom)
		except Exception:
			# Ignore malformed permission payloads but keep base permissions
			pass
	return perms


def _require_permission(admin: Admin, action: str) -> None:
	if action not in _get_permissions(admin):
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail=f"Missing permission: {action}",
		)


def _log_admin_action(
	db: Session,
	admin: Admin,
	action: str,
	description: str,
	*,
	target_type: Optional[str] = None,
	target_id: Optional[int] = None,
	before: Optional[dict] = None,
	after: Optional[dict] = None,
	success: bool = True,
	request: Optional[Request] = None,
	error: Optional[str] = None,
) -> None:
	log = AdminAuditLog(
		admin_id=admin.id,
		action=action,
		action_category=action.split(".")[0] if "." in action else "admin",
		description=description,
		target_type=target_type,
		target_id=target_id,
		before_state=before,
		after_state=after,
		ip_address=request.client.host if request and request.client else None,
		user_agent=request.headers.get("user-agent") if request else None,
		success="true" if success else "false",
		error_message=error,
	)
	db.add(log)
	db.commit()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class StaffCreate(BaseModel):
	username: str
	email: EmailStr
	full_name: str
	role: str = "SUPER_ADMIN"
	password: str = Field(min_length=8)
	permissions: Optional[List[str]] = None


class StaffResponse(BaseModel):
	id: int
	username: str
	email: EmailStr
	full_name: str
	role: str
	is_active: bool
	created_at: datetime
	last_login_at: Optional[datetime] = None

	model_config = ConfigDict(from_attributes=True)


class StaffDisableRequest(BaseModel):
	reason: Optional[str] = None


class TicketCreateRequest(BaseModel):
    user_id: int
    tenant_id: int
    subject: str
    description: str
    category: Optional[str] = None
    priority: Optional[str] = None


class TicketAssignRequest(BaseModel):
    agent_id: int


class TicketResolveRequest(BaseModel):
    resolution: str
    status: Optional[str] = None


class TicketNoteCreate(BaseModel):
	message: str
	is_internal: bool = True


class CouponCreate(BaseModel):
	tenant_id: int
	code: str
	name: str
	description: Optional[str] = None
	coupon_type: CouponType
	discount_value: Decimal = Field(gt=0)
	max_uses: Optional[int] = None
	max_uses_per_user: Optional[int] = None
	valid_from: datetime
	valid_until: Optional[datetime] = None
	applies_to: Optional[str] = None
	plan_ids: Optional[str] = None
	is_public: bool = False


class CouponAdminResponse(BaseModel):
	id: int
	tenant_id: int
	code: str
	name: str
	description: Optional[str]
	coupon_type: CouponType
	discount_value: Decimal
	max_uses: Optional[int]
	uses_count: int
	max_uses_per_user: Optional[int]
	valid_from: datetime
	valid_until: Optional[datetime]
	applies_to: Optional[str]
	plan_ids: Optional[str]
	is_public: bool
	status: CouponStatus
	created_at: datetime

	model_config = ConfigDict(from_attributes=True)


class CouponAssignRequest(BaseModel):
	user_id: int
	tenant_id: int
	applied_to_type: str = "subscription"
	applied_to_id: int
	original_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
	discount_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


class DashboardAnalytics(BaseModel):
	total_users: int
	active_subscriptions: int
	open_tickets: int
	revenue_this_month: Decimal


class StaffAnalyticsItem(BaseModel):
	staff_id: Optional[int]
	name: Optional[str]
	assigned: int
	resolved: int
	avg_resolution_hours: float


class TicketAnalytics(BaseModel):
	total: int
	open: int
	in_progress: int
	resolved: int
	closed: int
	breaches: int
	avg_resolution_hours: float


class CouponAnalytics(BaseModel):
	total: int
	active: int
	expired: int
	disabled: int
	total_redemptions: int


class RevenueAnalytics(BaseModel):
	total_revenue: Decimal
	successful_transactions: int
	failed_transactions: int
	active_subscriptions: int


# Authentication Schemas
class AdminLoginRequest(BaseModel):
	email: EmailStr
	password: str


class AdminLoginResponse(BaseModel):
	success: bool
	message: str
	user: Optional[dict] = None
	token: Optional[str] = None


class AdminChangePasswordRequest(BaseModel):
	email: EmailStr
	current_password: str
	new_password: str = Field(min_length=8)
	confirm_password: str


class AdminChangePasswordResponse(BaseModel):
	success: bool
	message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_priority(value: Optional[str]) -> Optional[TicketPriority]:
	if value is None:
		return None
	try:
		return TicketPriority(value)
	except ValueError:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticket priority")


def _safe_status(value: Optional[str]) -> Optional[TicketStatus]:
	if value is None:
		return None
	try:
		return TicketStatus(value)
	except ValueError:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticket status")


def _generate_ticket_number(db: Session, tenant_id: int) -> str:
	while True:
		candidate = f"SUP-{tenant_id}-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
		exists = (
			db.query(SupportTicket)
			.filter(SupportTicket.ticket_number == candidate)
			.first()
		)
		if not exists:
			return candidate


def _ticket_to_response(ticket: SupportTicket) -> dict:
	return SupportTicketResponse.model_validate(ticket).model_dump()


def _ticket_detail(ticket: SupportTicket, messages: List[SupportMessage]) -> dict:
	return SupportTicketDetailResponse(
		**SupportTicketResponse.model_validate(ticket).model_dump(),
		description=ticket.description,
		category=ticket.category,
		assigned_to_agent_id=ticket.assigned_to_agent_id,
		first_response_at=ticket.first_response_at,
		closed_at=ticket.closed_at,
		sla_breached=ticket.sla_breached,
		sla_breach_reason=ticket.sla_breach_reason,
		customer_rating=ticket.customer_rating,
		customer_feedback=ticket.customer_feedback,
		messages=[SupportMessageResponse.model_validate(m) for m in messages],
	).model_dump()


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
@router.post("/auth/login", response_model=AdminLoginResponse)
def admin_login(
	data: AdminLoginRequest,
	request: Request,
	db: Session = Depends(get_db),
):
	"""
	Admin login endpoint - authenticate with email and password.
	Returns session token and admin profile.
	"""
	# Find admin by email
	admin = db.query(Admin).filter(Admin.email == data.email).first()
	
	if not admin:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid email or password"
		)
	
	if not admin.is_active:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Admin account is inactive"
		)
	
	# Check if account is locked
	if admin.locked_until and admin.locked_until > datetime.utcnow():
		raise HTTPException(
			status_code=status.HTTP_423_LOCKED,
			detail="Account is temporarily locked due to failed login attempts"
		)
	
	# Verify password
	try:
		if not bcrypt.verify(data.password, admin.password_hash):
			# Increment failed login attempts
			admin.failed_login_attempts = (admin.failed_login_attempts or 0) + 1
			
			# Lock account after 5 failed attempts
			if admin.failed_login_attempts >= 5:
				admin.locked_until = datetime.utcnow() + timedelta(minutes=30)
			
			db.commit()
			
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail="Invalid email or password"
			)
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Password verification error: {str(e)}"
		)
	
	# Reset failed login attempts
	admin.failed_login_attempts = 0
	admin.locked_until = None
	admin.last_login_at = datetime.utcnow()
	admin.last_login_ip = request.client.host if request and request.client else None
	db.commit()
	
	# Create session token (32 bytes = 64 hex characters)
	session_token = secrets.token_hex(32)
	
	# Create admin session
	admin_session = AdminSession(
		admin_id=admin.id,
		session_token=session_token,
		ip_address=request.client.host if request and request.client else None,
		user_agent=request.headers.get("user-agent"),
		expires_at=datetime.utcnow() + timedelta(days=30),
		is_active=True
	)
	db.add(admin_session)
	db.commit()
	
	# Return success response
	return AdminLoginResponse(
		success=True,
		message="Login successful",
		user={
			"id": admin.id,
			"email": admin.email,
			"username": admin.username,
			"full_name": admin.full_name,
			"role": admin.role,
			"passwordChanged": admin.password_changed
		},
		token=session_token
	)


@router.post("/auth/change-password", response_model=AdminChangePasswordResponse)
def admin_change_password(
	data: AdminChangePasswordRequest,
	db: Session = Depends(get_db),
):
	"""
	Admin change password endpoint - change admin password.
	"""
	# Find admin by email
	admin = db.query(Admin).filter(Admin.email == data.email).first()
	
	if not admin:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid email or password"
		)
	
	if not admin.is_active:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Admin account is inactive"
		)
	
	# Verify current password
	try:
		if not bcrypt.verify(data.current_password, admin.password_hash):
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail="Current password is incorrect"
			)
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Password verification error: {str(e)}"
		)
	
	# Validate new password
	if data.new_password != data.confirm_password:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="New password and confirm password do not match"
		)
	
	if data.new_password == data.current_password:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="New password must be different from current password"
		)
	
	# Hash and update password
	try:
		admin.password_hash = bcrypt.hash(data.new_password)
		admin.password_changed = True
		db.commit()
	except Exception as e:
		db.rollback()
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Password update error: {str(e)}"
		)
	
	return AdminChangePasswordResponse(
		success=True,
		message="Password changed successfully"
	)


# ---------------------------------------------------------------------------
# Staff Management
# ---------------------------------------------------------------------------
@router.get("/staff", response_model=List[StaffResponse])
def list_staff(
	search: Optional[str] = Query(None, min_length=2),
	role: Optional[str] = None,
	is_active: Optional[bool] = None,
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "list_staff")

	query = db.query(Admin)
	if search:
		ilike_term = f"%{search}%"
		query = query.filter(or_(Admin.username.ilike(ilike_term), Admin.email.ilike(ilike_term)))
	if role:
		query = query.filter(Admin.role == role)
	if is_active is not None:
		query = query.filter(Admin.is_active == is_active)

	staff = query.order_by(Admin.created_at.desc()).all()
	return [StaffResponse.model_validate(s) for s in staff]


@router.post("/staff", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
def create_staff(
	data: StaffCreate,
	request: Request,
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "create_staff")

	if db.query(Admin).filter(or_(Admin.username == data.username, Admin.email == data.email)).first():
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists")

	staff = Admin(
		username=data.username,
		email=data.email,
		full_name=data.full_name,
		role=_normalize_role(data.role),
		password_hash=bcrypt.hash(data.password),
		permissions=json.dumps(data.permissions or []),
		is_active=True,
	)
	db.add(staff)
	db.commit()
	db.refresh(staff)

	_log_admin_action(
		db,
		admin,
		"create_staff",
		f"Created staff {staff.username}",
		target_type="staff",
		target_id=staff.id,
		after={"role": staff.role, "email": staff.email},
		request=request,
	)
	return StaffResponse.model_validate(staff)


@router.patch("/staff/{staff_id}/disable")
def disable_staff(
	staff_id: int,
	data: StaffDisableRequest,
	request: Request,
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "disable_staff")
	staff = db.query(Admin).filter(Admin.id == staff_id).first()
	if not staff:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")

	staff.is_active = False
	db.commit()

	_log_admin_action(
		db,
		admin,
		"disable_staff",
		f"Disabled staff {staff.username}",
		target_type="staff",
		target_id=staff.id,
		after={"is_active": False, "reason": data.reason},
		request=request,
	)
	return {"message": "Staff disabled"}


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------
@router.get("/users", response_model=PaginatedResponse)
def list_users(
	page: int = Query(1, ge=1),
	limit: int = Query(50, ge=1, le=100),
	search: Optional[str] = None,
	status_filter: Optional[str] = Query(None, alias="status"),
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "list_users")

	query = db.query(User)
	if search:
		ilike_term = f"%{search}%"
		query = query.filter(
			or_(
				User.email.ilike(ilike_term),
				User.full_name.ilike(ilike_term),
				User.clerk_user_id.ilike(ilike_term),
			)
		)
	if status_filter:
		query = query.filter(User.is_active == (status_filter == "active"))

	total = query.count()
	users = (
		query.order_by(User.created_at.desc())
		.offset((page - 1) * limit)
		.limit(limit)
		.all()
	)

	return {
		"items": users,
		"total": total,
		"page": page,
		"limit": limit,
		"pages": (total + limit - 1) // limit,
	}


@router.get("/users/{user_id}")
def get_user_details(
	user_id: int,
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "view_user")
	user = db.query(User).filter(User.id == user_id).first()
	if not user:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

	subscription = (
		db.query(UserSubscription)
		.filter(UserSubscription.user_id == user_id)
		.order_by(UserSubscription.created_at.desc())
		.first()
	)

	return {
		"user": user,
		"subscription": subscription,
	}


@router.patch("/users/{user_id}/activate")
def activate_user(
	user_id: int,
	request: Request,
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "activate_user")
	user = db.query(User).filter(User.id == user_id).first()
	if not user:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

	user.is_active = True
	db.commit()
	_log_admin_action(
		db,
		admin,
		"activate_user",
		f"Activated user {user.email}",
		target_type="user",
		target_id=user.id,
		after={"is_active": True},
		request=request,
	)
	return {"message": "User activated"}


@router.patch("/users/{user_id}/deactivate")
def deactivate_user(
	user_id: int,
	reason: Optional[str] = None,
	request: Request = None,
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "deactivate_user")
	user = db.query(User).filter(User.id == user_id).first()
	if not user:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

	user.is_active = False
	db.commit()
	_log_admin_action(
		db,
		admin,
		"deactivate_user",
		f"Deactivated user {user.email}",
		target_type="user",
		target_id=user.id,
		after={"is_active": False, "reason": reason},
		request=request,
	)
	return {"message": "User deactivated"}


# ---------------------------------------------------------------------------
# Support Tickets
# ---------------------------------------------------------------------------
@router.get("/tickets", response_model=PaginatedResponse)
def list_support_tickets(
	page: int = Query(1, ge=1),
	limit: int = Query(50, ge=1, le=100),
	status_filter: Optional[str] = Query(None, alias="status"),
	priority: Optional[str] = None,
	assigned_to: Optional[int] = None,
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "list_tickets")

	query = db.query(SupportTicket)
	if status_filter:
		query = query.filter(SupportTicket.status == _safe_status(status_filter))
	if priority:
		query = query.filter(SupportTicket.priority == _safe_priority(priority))
	if assigned_to:
		query = query.filter(SupportTicket.assigned_to_agent_id == assigned_to)

	total = query.count()
	tickets = (
		query.order_by(SupportTicket.created_at.desc())
		.offset((page - 1) * limit)
		.limit(limit)
		.all()
	)

	return {
		"items": [_ticket_to_response(t) for t in tickets],
		"total": total,
		"page": page,
		"limit": limit,
		"pages": (total + limit - 1) // limit,
	}


@router.post("/tickets", response_model=SupportTicketDetailResponse, status_code=status.HTTP_201_CREATED)
def create_support_ticket(
    data: TicketCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    _require_permission(admin, "create_ticket")

    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    ticket = SupportTicket(
        tenant_id=data.tenant_id,
        user_id=data.user_id,
        ticket_number=_generate_ticket_number(db, data.tenant_id),
        subject=data.subject,
        description=data.description,
        category=data.category,
        priority=_safe_priority(data.priority) or TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
    )
    db.add(ticket)
    db.flush()

    initial_message = SupportMessage(
        ticket_id=ticket.id,
        message=data.description,
        message_type="text",
        sender_type="admin",
        sender_id=admin.id,
        sender_name=admin.full_name,
        is_internal=False,
    )
    db.add(initial_message)
    db.commit()
    db.refresh(ticket)

    messages = (
        db.query(SupportMessage)
        .filter(SupportMessage.ticket_id == ticket.id)
        .order_by(SupportMessage.created_at.asc())
        .all()
    )

    _log_admin_action(
        db,
        admin,
        "create_ticket",
        f"Created ticket {ticket.ticket_number}",
        target_type="ticket",
        target_id=ticket.id,
        after={"status": ticket.status.value, "priority": ticket.priority.value},
        request=request,
    )
    return SupportTicketDetailResponse(**_ticket_detail(ticket, messages))


@router.get("/tickets/{ticket_id}", response_model=SupportTicketDetailResponse)
def get_ticket_detail(
	ticket_id: int,
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "view_ticket")
	ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
	if not ticket:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

	messages = (
		db.query(SupportMessage)
		.filter(SupportMessage.ticket_id == ticket.id)
		.order_by(SupportMessage.created_at.asc())
		.all()
	)
	return SupportTicketDetailResponse(**_ticket_detail(ticket, messages))


@router.patch("/tickets/{ticket_id}/assign")
def assign_ticket(
	ticket_id: int,
	data: TicketAssignRequest,
	request: Request,
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "assign_ticket")
	ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
	if not ticket:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

	ticket.assigned_to_agent_id = data.agent_id
	if ticket.status == TicketStatus.OPEN:
		ticket.status = TicketStatus.IN_PROGRESS
		ticket.first_response_at = ticket.first_response_at or datetime.utcnow()
	db.commit()

	_log_admin_action(
		db,
		admin,
		"assign_ticket",
		f"Assigned ticket {ticket.ticket_number} to agent {data.agent_id}",
		target_type="ticket",
		target_id=ticket.id,
		after={"assigned_to_agent_id": data.agent_id, "status": ticket.status.value},
		request=request,
	)
	return {"message": "Ticket assigned"}


@router.patch("/tickets/{ticket_id}/resolve")
def resolve_ticket(
	ticket_id: int,
	data: TicketResolveRequest,
	request: Request,
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "resolve_ticket")
	ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
	if not ticket:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

	ticket.status = _safe_status(data.status) or TicketStatus.RESOLVED
	ticket.resolved_at = datetime.utcnow()
	if ticket.closed_at is None and ticket.status == TicketStatus.CLOSED:
		ticket.closed_at = datetime.utcnow()
	db.commit()

	resolution_message = SupportMessage(
		ticket_id=ticket.id,
		message=f"Resolution: {data.resolution}",
		message_type="text",
		sender_type="admin",
		sender_id=admin.id,
		sender_name=admin.full_name,
		is_internal=False,
	)
	db.add(resolution_message)
	db.commit()

	_log_admin_action(
		db,
		admin,
		"resolve_ticket",
		f"Resolved ticket {ticket.ticket_number}",
		target_type="ticket",
		target_id=ticket.id,
		after={"status": ticket.status.value},
		request=request,
	)
	return {"message": "Ticket resolved"}


@router.post("/tickets/{ticket_id}/notes", response_model=SupportMessageResponse, status_code=status.HTTP_201_CREATED)
def add_ticket_note(
	ticket_id: int,
	data: TicketNoteCreate,
	request: Request,
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "add_ticket_note")
	ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
	if not ticket:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

	message = SupportMessage(
		ticket_id=ticket.id,
		message=data.message,
		message_type="text",
		sender_type="admin",
		sender_id=admin.id,
		sender_name=admin.full_name,
		is_internal=data.is_internal,
	)
	db.add(message)
	db.commit()
	db.refresh(message)

	_log_admin_action(
		db,
		admin,
		"add_ticket_note",
		f"Added note to ticket {ticket.ticket_number}",
		target_type="ticket",
		target_id=ticket.id,
		request=request,
	)
	return SupportMessageResponse.model_validate(message)


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------
def _enforce_coupon_limits(admin: Admin, data: CouponCreate) -> None:
	role = _normalize_role(admin.role)
	if role != "MARKETING_STAFF":
		return

	if data.coupon_type == CouponType.PERCENTAGE and data.discount_value > Decimal("30"):
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Marketing staff can create coupons up to 30%")
	if data.max_uses and data.max_uses > 100:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Marketing staff coupon usage limit is 100")
	if data.valid_until and (data.valid_until - data.valid_from).days > 90:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Marketing staff coupons can be valid for up to 90 days")


@router.post("/coupons", response_model=CouponAdminResponse, status_code=status.HTTP_201_CREATED)
def create_coupon(
    data: CouponCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    _require_permission(admin, "create_coupon")
    _enforce_coupon_limits(admin, data)

    if db.query(Coupon).filter(Coupon.code == data.code.upper()).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon code already exists")

    coupon = Coupon(
        tenant_id=data.tenant_id,
        code=data.code.upper(),
        name=data.name,
        description=data.description,
        coupon_type=data.coupon_type,
        discount_value=data.discount_value,
        max_uses=data.max_uses,
        max_uses_per_user=data.max_uses_per_user,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        applies_to=data.applies_to,
        plan_ids=data.plan_ids,
        is_public=data.is_public,
        status=CouponStatus.ACTIVE,
        created_by_admin_id=admin.id,
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)

    _log_admin_action(
        db,
        admin,
        "create_coupon",
        f"Created coupon {coupon.code}",
        target_type="coupon",
        target_id=coupon.id,
        after={"status": coupon.status.value, "discount_value": str(coupon.discount_value)},
        request=request,
    )
    return CouponAdminResponse.model_validate(coupon)


@router.get("/coupons", response_model=List[CouponAdminResponse])
def list_coupons(
    status_filter: Optional[CouponStatus] = Query(None, alias="status"),
    tenant_id: Optional[int] = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    _require_permission(admin, "list_coupons")
    query = db.query(Coupon)
    if status_filter:
        query = query.filter(Coupon.status == status_filter)
    if tenant_id:
        query = query.filter(Coupon.tenant_id == tenant_id)
    coupons = query.order_by(Coupon.created_at.desc()).all()
    return [CouponAdminResponse.model_validate(c) for c in coupons]


@router.post("/coupons/{coupon_id}/assign")
def assign_coupon(
	coupon_id: int,
	data: CouponAssignRequest,
	request: Request,
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "assign_coupon")
	coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
	if not coupon:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
	if not coupon.is_valid():
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon is not active or valid")

	usage = CouponUsage(
		coupon_id=coupon.id,
		user_id=data.user_id,
		tenant_id=data.tenant_id,
		applied_to_type=data.applied_to_type,
		applied_to_id=data.applied_to_id,
		original_amount=data.original_amount,
		discount_amount=data.discount_amount,
		final_amount=max(Decimal("0"), data.original_amount - data.discount_amount),
	)
	coupon.uses_count = (coupon.uses_count or 0) + 1
	db.add(usage)
	db.commit()

	_log_admin_action(
		db,
		admin,
		"assign_coupon",
		f"Assigned coupon {coupon.code} to user {data.user_id}",
		target_type="coupon",
		target_id=coupon.id,
		after={"uses_count": coupon.uses_count},
		request=request,
	)
	return {"message": "Coupon assigned"}


# ---------------------------------------------------------------------------
# Analytics & Reports
# ---------------------------------------------------------------------------
def _staff_metrics(db: Session) -> List[StaffAnalyticsItem]:
	tickets = db.query(SupportTicket).all()
	staff_map: Dict[Optional[int], Dict[str, float]] = {}
	for ticket in tickets:
		key = ticket.assigned_to_agent_id
		if key not in staff_map:
			staff_map[key] = {
				"assigned": 0,
				"resolved": 0,
				"resolution_hours_total": 0.0,
			}
		staff_map[key]["assigned"] += 1
		if ticket.resolved_at:
			staff_map[key]["resolved"] += 1
			staff_map[key]["resolution_hours_total"] += max(
				0.0,
				(ticket.resolved_at - ticket.created_at).total_seconds() / 3600,
			)

	admin_lookup = {a.id: a.full_name or a.username for a in db.query(Admin).all()}
	analytics: List[StaffAnalyticsItem] = []
	for staff_id, metrics in staff_map.items():
		resolved = metrics["resolved"]
		avg_hours = metrics["resolution_hours_total"] / resolved if resolved else 0.0
		analytics.append(
			StaffAnalyticsItem(
				staff_id=staff_id,
				name=admin_lookup.get(staff_id),
				assigned=int(metrics["assigned"]),
				resolved=int(resolved),
				avg_resolution_hours=round(avg_hours, 2),
			)
		)
	return analytics


def _ticket_metrics(db: Session) -> TicketAnalytics:
	tickets = db.query(SupportTicket).all()
	status_counts = {
		TicketStatus.OPEN: 0,
		TicketStatus.IN_PROGRESS: 0,
		TicketStatus.RESOLVED: 0,
		TicketStatus.CLOSED: 0,
	}
	breaches = 0
	resolution_hours: List[float] = []

	for ticket in tickets:
		status_counts[ticket.status] = status_counts.get(ticket.status, 0) + 1
		if ticket.sla_breached:
			breaches += 1
		if ticket.resolved_at:
			resolution_hours.append((ticket.resolved_at - ticket.created_at).total_seconds() / 3600)

	avg_resolution = round(sum(resolution_hours) / len(resolution_hours), 2) if resolution_hours else 0.0
	return TicketAnalytics(
		total=len(tickets),
		open=status_counts.get(TicketStatus.OPEN, 0),
		in_progress=status_counts.get(TicketStatus.IN_PROGRESS, 0),
		resolved=status_counts.get(TicketStatus.RESOLVED, 0),
		closed=status_counts.get(TicketStatus.CLOSED, 0),
		breaches=breaches,
		avg_resolution_hours=avg_resolution,
	)


def _coupon_metrics(db: Session) -> CouponAnalytics:
	coupons = db.query(Coupon).all()
	usages = db.query(CouponUsage).count()
	return CouponAnalytics(
		total=len(coupons),
		active=len([c for c in coupons if c.status == CouponStatus.ACTIVE]),
		expired=len([c for c in coupons if c.status == CouponStatus.EXPIRED]),
		disabled=len([c for c in coupons if c.status == CouponStatus.DISABLED]),
		total_redemptions=usages,
	)


def _revenue_metrics(db: Session) -> RevenueAnalytics:
	succeeded = db.query(Transaction).filter(Transaction.status == TransactionStatus.SUCCEEDED.value).all()
	failed_count = db.query(Transaction).filter(Transaction.status == TransactionStatus.FAILED.value).count()
	total_revenue = sum(t.amount for t in succeeded)
	active_subscriptions = db.query(UserSubscription).filter(UserSubscription.status == SubscriptionStatus.ACTIVE).count()
	return RevenueAnalytics(
		total_revenue=Decimal(total_revenue) / Decimal("100"),
		successful_transactions=len(succeeded),
		failed_transactions=failed_count,
		active_subscriptions=active_subscriptions,
	)


@router.get("/analytics/dashboard", response_model=DashboardAnalytics)
def get_admin_dashboard(
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "view_staff_analytics")
	start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

	total_users = db.query(func.count(User.id)).scalar() or 0
	active_subscriptions = (
		db.query(func.count(UserSubscription.id))
		.filter(UserSubscription.status == SubscriptionStatus.ACTIVE)
		.scalar()
		or 0
	)
	open_tickets = (
		db.query(func.count(SupportTicket.id))
		.filter(SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]))
		.scalar()
		or 0
	)
	revenue_this_month = (
		db.query(func.coalesce(func.sum(Transaction.amount), 0))
		.filter(
			Transaction.status == TransactionStatus.SUCCEEDED.value,
			Transaction.created_at >= start_of_month,
		)
		.scalar()
		or 0
	)

	return DashboardAnalytics(
		total_users=total_users,
		active_subscriptions=active_subscriptions,
		open_tickets=open_tickets,
		revenue_this_month=Decimal(revenue_this_month) / Decimal("100"),
	)


@router.get("/analytics/staff", response_model=List[StaffAnalyticsItem])
def get_staff_analytics(
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "view_staff_analytics")
	return _staff_metrics(db)


@router.get("/analytics/tickets", response_model=TicketAnalytics)
def get_ticket_analytics(
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "view_ticket_analytics")
	return _ticket_metrics(db)


@router.get("/analytics/coupons", response_model=CouponAnalytics)
def get_coupon_analytics(
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "view_staff_analytics")
	return _coupon_metrics(db)


@router.get("/analytics/revenue", response_model=RevenueAnalytics)
def get_revenue_analytics(
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "view_revenue_analytics")
	return _revenue_metrics(db)


@router.get("/audit-logs/export")
def export_audit_logs(
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "export_audit_logs")
	logs = db.query(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).all()

	buffer = io.StringIO()
	writer = csv.writer(buffer)
	writer.writerow([
		"id",
		"admin_id",
		"action",
		"description",
		"target_type",
		"target_id",
		"success",
		"created_at",
	])
	for log in logs:
		writer.writerow([
			log.id,
			log.admin_id,
			log.action,
			log.description,
			log.target_type,
			log.target_id,
			log.success,
			log.created_at.isoformat() if log.created_at else None,
		])

	buffer.seek(0)
	return StreamingResponse(
		buffer,
		media_type="text/csv",
		headers={"Content-Disposition": "attachment; filename=audit-logs.csv"},
	)


@router.get("/analytics/export/{export_type}")
def export_analytics_csv(
	export_type: str,
	db: Session = Depends(get_db),
	admin: Admin = Depends(get_current_admin),
):
	_require_permission(admin, "view_staff_analytics")
	buffer = io.StringIO()
	writer = csv.writer(buffer)

	if export_type == "staff":
		data = _staff_metrics(db)
		writer.writerow(["staff_id", "name", "assigned", "resolved", "avg_resolution_hours"])
		for row in data:
			writer.writerow([row.staff_id, row.name, row.assigned, row.resolved, row.avg_resolution_hours])
	elif export_type == "tickets":
		metrics = _ticket_metrics(db)
		writer.writerow(["total", "open", "in_progress", "resolved", "closed", "breaches", "avg_resolution_hours"])
		writer.writerow([
			metrics.total,
			metrics.open,
			metrics.in_progress,
			metrics.resolved,
			metrics.closed,
			metrics.breaches,
			metrics.avg_resolution_hours,
		])
	elif export_type == "coupons":
		metrics = _coupon_metrics(db)
		writer.writerow(["total", "active", "expired", "disabled", "total_redemptions"])
		writer.writerow([
			metrics.total,
			metrics.active,
			metrics.expired,
			metrics.disabled,
			metrics.total_redemptions,
		])
	elif export_type == "revenue":
		metrics = _revenue_metrics(db)
		writer.writerow(["total_revenue", "successful_transactions", "failed_transactions", "active_subscriptions"])
		writer.writerow([
			metrics.total_revenue,
			metrics.successful_transactions,
			metrics.failed_transactions,
			metrics.active_subscriptions,
		])
	else:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown export type")

	buffer.seek(0)
	return StreamingResponse(
		buffer,
		media_type="text/csv",
		headers={"Content-Disposition": f"attachment; filename={export_type}-analytics.csv"},
	)


