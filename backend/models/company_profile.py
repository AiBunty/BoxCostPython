"""Company Profile model - Business identity and branding."""
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.orm import relationship
from backend.database import Base, BaseMixin, TenantMixin


class CompanyProfile(Base, BaseMixin, TenantMixin):
    """
    CompanyProfile model - Single source of truth for company branding.
    Locked after first financial document is generated.
    """
    __tablename__ = "company_profiles"
    
    user_id = Column(Integer, nullable=False, index=True)
    
    # Business Identity
    company_name = Column(String(255), nullable=False)
    gst_number = Column(String(15), nullable=True, index=True)
    pan_number = Column(String(10), nullable=True)
    state_code = Column(String(2), nullable=True)
    
    # Contact Information
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    alternate_phone = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    country = Column(String(100), default="India", nullable=False)
    
    # Branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True)  # Hex color
    secondary_color = Column(String(7), nullable=True)
    
    # Banking Details
    bank_name = Column(String(255), nullable=True)
    account_number = Column(String(50), nullable=True)
    ifsc_code = Column(String(11), nullable=True)
    branch_name = Column(String(255), nullable=True)
    
    # Business Terms
    payment_terms = Column(Text, nullable=True)
    delivery_terms = Column(Text, nullable=True)
    
    # Status & Verification
    is_default = Column(Boolean, default=False, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)  # Locked after invoice
    gst_verified = Column(Boolean, default=False, nullable=False)
    verification_date = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    # user = relationship("User", back_populates="company_profiles")
    # tenant = relationship("Tenant", back_populates="company_profiles")
    
    def __repr__(self):
        return f"<CompanyProfile(id={self.id}, company_name={self.company_name}, gst={self.gst_number})>"
