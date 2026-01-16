"""Invoice models for GST-compliant billing."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric, JSON, Enum as SQLEnum
import enum
from backend.database import Base, BaseMixin, TenantMixin


class InvoiceStatus(str, enum.Enum):
    """Invoice status."""
    DRAFT = "draft"
    GENERATED = "generated"
    SENT = "sent"
    PAID = "paid"
    CANCELLED = "cancelled"


class Invoice(Base, BaseMixin, TenantMixin):
    """
    GST-compliant tax invoice.
    Immutable once generated.
    """
    __tablename__ = "invoices"
    
    user_id = Column(Integer, nullable=False, index=True)
    quote_id = Column(Integer, nullable=True, index=True)  # Link to quote if applicable
    
    # Invoice Identity
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    financial_year = Column(String(10), nullable=False)  # e.g., "2024-25"
    
    # Parties
    seller_profile = Column(JSON, nullable=False)  # Company profile snapshot
    buyer_profile = Column(JSON, nullable=False)  # Party profile snapshot
    
    # Invoice Details
    invoice_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    
    # Line Items
    items = Column(JSON, nullable=False)  # Array of line items
    
    # Amounts
    subtotal = Column(Numeric(12, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), default=0, nullable=False)
    cgst_amount = Column(Numeric(12, 2), default=0, nullable=False)
    sgst_amount = Column(Numeric(12, 2), default=0, nullable=False)
    igst_amount = Column(Numeric(12, 2), default=0, nullable=False)
    total_gst = Column(Numeric(12, 2), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    
    # GST Details
    gst_rate = Column(Numeric(5, 2), nullable=False)
    is_inter_state = Column(Boolean, nullable=False)
    place_of_supply = Column(String(100), nullable=False)
    
    # Payment
    payment_terms = Column(Text, nullable=True)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    payment_reference = Column(String(255), nullable=True)
    
    # PDF
    pdf_url = Column(String(500), nullable=True)
    pdf_generated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    is_locked = Column(Boolean, default=False, nullable=False)
    
    def __repr__(self):
        return f"<Invoice(number={self.invoice_number}, total={self.total_amount})>"


class SubscriptionInvoice(Base, BaseMixin):
    """
    Platform subscription invoices.
    Separate from business invoices.
    """
    __tablename__ = "subscription_invoices"
    
    subscription_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Invoice Identity
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    invoice_date = Column(DateTime(timezone=True), nullable=False)
    
    # Subscription Details
    plan_name = Column(String(100), nullable=False)
    plan_price = Column(Numeric(10, 2), nullable=False)
    billing_period_start = Column(DateTime(timezone=True), nullable=False)
    billing_period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Amounts
    subtotal = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0, nullable=False)
    gst_amount = Column(Numeric(10, 2), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    # Payment
    payment_status = Column(String(20), default="pending", nullable=False)
    payment_method = Column(String(50), nullable=True)
    razorpay_payment_id = Column(String(255), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # PDF
    pdf_url = Column(String(500), nullable=True)
    
    def __repr__(self):
        return f"<SubscriptionInvoice(number={self.invoice_number}, user_id={self.user_id})>"


class PaymentTransaction(Base, BaseMixin):
    """
    Payment transaction records.
    Links to Razorpay or other payment gateways.
    """
    __tablename__ = "payment_transactions"
    
    user_id = Column(Integer, nullable=False, index=True)
    invoice_id = Column(Integer, nullable=True, index=True)
    
    # Transaction Identity
    transaction_id = Column(String(255), unique=True, nullable=False, index=True)
    gateway = Column(String(50), nullable=False)  # razorpay, stripe, etc.
    
    # Gateway IDs
    gateway_order_id = Column(String(255), nullable=True)
    gateway_payment_id = Column(String(255), nullable=True, index=True)
    gateway_signature = Column(String(500), nullable=True)
    
    # Amount
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    
    # Status
    status = Column(String(20), nullable=False)  # pending, success, failed
    payment_method = Column(String(50), nullable=True)
    
    # Timestamps
    initiated_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    payment_metadata = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<PaymentTransaction(id={self.transaction_id}, status={self.status})>"
