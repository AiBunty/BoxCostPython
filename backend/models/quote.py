"""Quote management models - versioned quote system."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from backend.database import Base, BaseMixin, TenantMixin


class QuoteStatus(str, enum.Enum):
    """Quote status enumeration."""
    DRAFT = "draft"
    SENT = "sent"
    NEGOTIATED = "negotiated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Quote(Base, BaseMixin, TenantMixin):
    """
    Quote master record - header information.
    Supports versioning - every edit creates a new version.
    """
    __tablename__ = "quotes"
    
    user_id = Column(Integer, nullable=False, index=True)
    party_id = Column(Integer, nullable=False, index=True)
    
    # Quote Identification
    quote_number = Column(String(50), nullable=True, index=True)
    
    # Current Version Info
    current_version = Column(Integer, default=1, nullable=False)
    status = Column(SQLEnum(QuoteStatus), default=QuoteStatus.DRAFT, nullable=False)
    
    # Validity
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    # Negotiation
    is_negotiated = Column(Boolean, default=False, nullable=False)
    negotiated_at = Column(DateTime(timezone=True), nullable=True)
    negotiation_notes = Column(Text, nullable=True)
    
    # Snapshots (SSOT at time of quote creation)
    company_snapshot = Column(JSON, nullable=True)  # Company profile at creation
    party_snapshot = Column(JSON, nullable=True)  # Party profile at creation
    
    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<Quote(id={self.id}, number={self.quote_number}, status={self.status})>"


class QuoteVersion(Base, BaseMixin):
    """
    Quote version - stores complete state at each version.
    Immutable once created (except for negotiated version).
    """
    __tablename__ = "quote_versions"
    
    quote_id = Column(Integer, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    
    # Version Metadata
    created_by = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    
    # Terms
    payment_terms = Column(Text, nullable=True)
    delivery_terms = Column(Text, nullable=True)
    validity_days = Column(Integer, default=7, nullable=False)
    
    # Pricing Snapshots
    pricing_rules_snapshot = Column(JSON, nullable=True)
    paper_prices_snapshot = Column(JSON, nullable=True)
    
    # Status
    is_locked = Column(Boolean, default=False, nullable=False)  # Locked after negotiation
    
    def __repr__(self):
        return f"<QuoteVersion(quote_id={self.quote_id}, version={self.version})>"


class QuoteItem(Base, BaseMixin):
    """
    Quote line items for a specific version.
    One quote can have multiple items.
    """
    __tablename__ = "quote_items"
    
    quote_id = Column(Integer, nullable=False, index=True)
    version_id = Column(Integer, nullable=False, index=True)
    
    # Item Order
    line_number = Column(Integer, nullable=False)
    
    # Box Specifications
    box_name = Column(String(255), nullable=True)
    length = Column(Numeric(10, 2), nullable=False)  # mm
    width = Column(Numeric(10, 2), nullable=False)  # mm
    height = Column(Numeric(10, 2), nullable=False)  # mm
    ply = Column(Integer, nullable=False)  # 3-ply, 5-ply, 7-ply
    
    # Paper Specifications (JSON for each layer)
    paper_specs = Column(JSON, nullable=False)  # [{bf, gsm, shade}, ...]
    
    # Quantity & Pricing
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(10, 4), nullable=False)  # Cost per box
    total_cost = Column(Numeric(12, 2), nullable=False)  # quantity * unit_cost
    
    # Negotiation
    negotiated_price = Column(Numeric(10, 4), nullable=True)
    discount_percentage = Column(Numeric(5, 2), nullable=True)
    
    # Manufacturing Details
    printing_cost = Column(Numeric(10, 2), default=0, nullable=False)
    die_cost = Column(Numeric(10, 2), default=0, nullable=False)
    conversion_rate = Column(Numeric(10, 2), default=15, nullable=False)  # Rs/Kg
    
    # Calculated Values (stored for historical accuracy)
    sheet_length = Column(Numeric(10, 2), nullable=True)
    sheet_width = Column(Numeric(10, 2), nullable=True)
    paper_weight = Column(Numeric(10, 4), nullable=True)  # kg per box
    board_thickness = Column(Numeric(5, 3), nullable=True)  # mm
    
    # Strength Calculations
    ect = Column(Numeric(10, 2), nullable=True)  # Edge Crush Test
    bct = Column(Numeric(10, 2), nullable=True)  # Box Compression Test
    burst_strength = Column(Numeric(10, 2), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<QuoteItem(quote_id={self.quote_id}, line={self.line_number})>"


class QuoteSendLog(Base, BaseMixin):
    """
    Audit trail for quote sending.
    Tracks when and how quotes were sent to customers.
    """
    __tablename__ = "quote_send_logs"
    
    quote_id = Column(Integer, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    
    # Sending Details
    sent_by = Column(Integer, nullable=False)
    sent_via = Column(String(50), nullable=False)  # email, whatsapp
    recipient = Column(String(255), nullable=False)  # email or phone
    
    # Status
    status = Column(String(50), default="sent", nullable=False)  # sent, delivered, failed
    error_message = Column(Text, nullable=True)
    
    # Tracking
    message_id = Column(String(255), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<QuoteSendLog(quote_id={self.quote_id}, via={self.sent_via})>"
