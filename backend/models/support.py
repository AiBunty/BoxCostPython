"""Support ticket system models."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SQLEnum
import enum
from backend.database import Base, BaseMixin, TenantMixin


class TicketPriority(str, enum.Enum):
    """Ticket priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(str, enum.Enum):
    """Ticket status."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportTicket(Base, BaseMixin, TenantMixin):
    """
    Support ticket for customer issues.
    """
    __tablename__ = "support_tickets"
    
    user_id = Column(Integer, nullable=False, index=True)
    
    # Ticket Identity
    ticket_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Ticket Details
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=True)  # technical, billing, feature_request
    
    # Priority & Status
    priority = Column(SQLEnum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False)
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    
    # Assignment
    assigned_to_agent_id = Column(Integer, nullable=True, index=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    
    # SLA Tracking
    first_response_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # SLA Status
    sla_breached = Column(Boolean, default=False, nullable=False)
    sla_breach_reason = Column(Text, nullable=True)
    
    # Ratings
    customer_rating = Column(Integer, nullable=True)  # 1-5
    customer_feedback = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<SupportTicket(number={self.ticket_number}, status={self.status})>"


class SupportMessage(Base, BaseMixin):
    """
    Messages in support ticket conversations.
    """
    __tablename__ = "support_messages"
    
    ticket_id = Column(Integer, nullable=False, index=True)
    
    # Message Details
    message = Column(Text, nullable=False)
    message_type = Column(String(20), default="text", nullable=False)  # text, attachment
    
    # Sender
    sender_type = Column(String(20), nullable=False)  # user, agent, system
    sender_id = Column(Integer, nullable=True)
    sender_name = Column(String(255), nullable=True)
    
    # Metadata
    is_internal = Column(Boolean, default=False, nullable=False)  # Internal note
    attachments = Column(Text, nullable=True)  # JSON array of file URLs
    
    def __repr__(self):
        return f"<SupportMessage(ticket_id={self.ticket_id}, sender={self.sender_type})>"


class SupportAgent(Base, BaseMixin):
    """
    Support agent profiles.
    """
    __tablename__ = "support_agents"
    
    admin_id = Column(Integer, unique=True, nullable=False, index=True)
    
    # Agent Details
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    
    # Specialization
    specializations = Column(Text, nullable=True)  # JSON array
    languages = Column(Text, nullable=True)  # JSON array
    
    # Capacity
    max_tickets = Column(Integer, default=20, nullable=False)
    current_tickets = Column(Integer, default=0, nullable=False)
    
    # Performance
    avg_response_time = Column(Integer, nullable=True)  # minutes
    tickets_resolved = Column(Integer, default=0, nullable=False)
    avg_customer_rating = Column(Integer, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<SupportAgent(name={self.name}, tickets={self.current_tickets}/{self.max_tickets})>"


class SLARule(Base, BaseMixin):
    """
    SLA (Service Level Agreement) rules.
    Defines response and resolution time targets.
    """
    __tablename__ = "sla_rules"
    
    priority = Column(SQLEnum(TicketPriority), unique=True, nullable=False)
    
    # Time Limits (minutes)
    first_response_time = Column(Integer, nullable=False)  # minutes
    resolution_time = Column(Integer, nullable=False)  # minutes
    
    # Business Hours
    applies_business_hours_only = Column(Boolean, default=True, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<SLARule(priority={self.priority}, response={self.first_response_time}min)>"
