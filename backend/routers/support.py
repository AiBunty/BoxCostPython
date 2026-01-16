"""Support ticket management API."""
from datetime import datetime
import random
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_user, get_current_tenant_id, get_current_admin
from backend.models.support import (
    SupportTicket,
    SupportMessage,
    TicketPriority,
    TicketStatus,
)
from backend.models.user import User
from shared.schemas import (
    SupportTicketCreate,
    SupportTicketUpdate,
    SupportTicketResponse,
    SupportTicketDetailResponse,
    SupportMessageCreate,
    SupportMessageResponse,
)

router = APIRouter(prefix="/api/support", tags=["Support"])


def _safe_status(value: str) -> TicketStatus:
    try:
        return TicketStatus(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticket status")


def _safe_priority(value: str) -> TicketPriority:
    try:
        return TicketPriority(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticket priority")


def _generate_ticket_number(db: Session, tenant_id: int) -> str:
    """Generate a unique ticket number scoped by tenant."""
    while True:
        candidate = f"SUP-{tenant_id}-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        exists = (
            db.query(SupportTicket)
            .filter(SupportTicket.ticket_number == candidate)
            .first()
        )
        if not exists:
            return candidate


def _get_ticket_or_404(db: Session, ticket_id: int, tenant_id: int) -> SupportTicket:
    ticket = (
        db.query(SupportTicket)
        .filter(
            SupportTicket.id == ticket_id,
            SupportTicket.tenant_id == tenant_id,
        )
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


@router.get("/tickets", response_model=List[SupportTicketResponse])
async def list_tickets(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    search: Optional[str] = Query(None, min_length=2),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """List tickets for the current tenant with simple filtering."""
    query = db.query(SupportTicket).filter(SupportTicket.tenant_id == tenant_id)

    if status_filter:
        query = query.filter(SupportTicket.status == _safe_status(status_filter))
    if priority:
        query = query.filter(SupportTicket.priority == _safe_priority(priority))
    if search:
        ilike_term = f"%{search}%"
        query = query.filter(
            or_(
                SupportTicket.subject.ilike(ilike_term),
                SupportTicket.description.ilike(ilike_term),
                SupportTicket.ticket_number.ilike(ilike_term),
            )
        )

    tickets = (
        query.order_by(SupportTicket.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return [SupportTicketResponse.model_validate(t) for t in tickets]


@router.post("/tickets", response_model=SupportTicketDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: SupportTicketCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Create a new support ticket and seed the conversation with the description."""
    ticket = SupportTicket(
        tenant_id=tenant_id,
        user_id=current_user.id,
        ticket_number=_generate_ticket_number(db, tenant_id),
        subject=data.subject,
        description=data.description,
        category=data.category,
        priority=_safe_priority(data.priority) if data.priority else TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
    )
    db.add(ticket)
    db.flush()

    initial_message = SupportMessage(
        ticket_id=ticket.id,
        message=data.description,
        message_type="text",
        sender_type="user",
        sender_id=current_user.id,
        sender_name=getattr(current_user, "full_name", None),
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
    )


@router.get("/tickets/{ticket_id}", response_model=SupportTicketDetailResponse)
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get a ticket with conversation history."""
    ticket = _get_ticket_or_404(db, ticket_id, tenant_id)
    messages = (
        db.query(SupportMessage)
        .filter(SupportMessage.ticket_id == ticket.id)
        .order_by(SupportMessage.created_at.asc())
        .all()
    )

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
    )


@router.patch("/tickets/{ticket_id}", response_model=SupportTicketDetailResponse)
async def update_ticket(
    ticket_id: int,
    data: SupportTicketUpdate,
    current_admin=Depends(get_current_admin),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Update ticket metadata such as status, priority, and assignment."""
    ticket = _get_ticket_or_404(db, ticket_id, tenant_id)

    update_data = data.model_dump(exclude_unset=True)

    if "status" in update_data:
        new_status = _safe_status(update_data["status"])
        ticket.status = new_status
        if new_status == TicketStatus.IN_PROGRESS and not ticket.first_response_at:
            ticket.first_response_at = datetime.utcnow()
        if new_status == TicketStatus.RESOLVED:
            ticket.resolved_at = datetime.utcnow()
        if new_status == TicketStatus.CLOSED:
            ticket.closed_at = datetime.utcnow()

    if "priority" in update_data and update_data["priority"] is not None:
        ticket.priority = _safe_priority(update_data["priority"])

    for field in [
        "subject",
        "description",
        "category",
        "assigned_to_agent_id",
        "sla_breached",
        "sla_breach_reason",
        "customer_rating",
        "customer_feedback",
    ]:
        if field in update_data:
            setattr(ticket, field, update_data[field])

    db.commit()
    db.refresh(ticket)

    messages = (
        db.query(SupportMessage)
        .filter(SupportMessage.ticket_id == ticket.id)
        .order_by(SupportMessage.created_at.asc())
        .all()
    )

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
    )


@router.post("/tickets/{ticket_id}/messages", response_model=SupportMessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(
    ticket_id: int,
    data: SupportMessageCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Append a message to a ticket."""
    ticket = _get_ticket_or_404(db, ticket_id, tenant_id)

    message = SupportMessage(
        ticket_id=ticket.id,
        message=data.message,
        message_type=data.message_type,
        sender_type=data.sender_type,
        sender_id=data.sender_id or current_user.id,
        sender_name=data.sender_name,
        is_internal=data.is_internal,
        attachments=data.attachments,
    )

    if ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.IN_PROGRESS
        if not ticket.first_response_at:
            ticket.first_response_at = datetime.utcnow()

    db.add(message)
    db.commit()
    db.refresh(message)
    db.refresh(ticket)

    return SupportMessageResponse.model_validate(message)


@router.get("/tickets/{ticket_id}/messages", response_model=List[SupportMessageResponse])
async def list_messages(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Return conversation history for a ticket."""
    _ = _get_ticket_or_404(db, ticket_id, tenant_id)
    messages = (
        db.query(SupportMessage)
        .filter(SupportMessage.ticket_id == ticket_id)
        .order_by(SupportMessage.created_at.asc())
        .all()
    )
    return [SupportMessageResponse.model_validate(m) for m in messages]
