"""Party (Customer) profile model."""
from sqlalchemy import Column, Integer, String, Boolean, Text
from backend.database import Base, BaseMixin, TenantMixin


class PartyProfile(Base, BaseMixin, TenantMixin):
    """
    Party Profile model - Customer/client information.
    """
    __tablename__ = "party_profiles"
    
    user_id = Column(Integer, nullable=False, index=True)
    
    # Basic Information
    party_name = Column(String(255), nullable=False)
    contact_person = Column(String(255), nullable=True)
    
    # Contact Details
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    alternate_phone = Column(String(20), nullable=True)
    
    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    country = Column(String(100), default="India", nullable=False)
    
    # Business Details
    gst_number = Column(String(15), nullable=True, index=True)
    pan_number = Column(String(10), nullable=True)
    state_code = Column(String(2), nullable=True)
    
    # Payment Terms
    payment_terms = Column(Text, nullable=True)
    credit_days = Column(Integer, nullable=True)
    credit_limit = Column(Integer, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<PartyProfile(id={self.id}, name={self.party_name})>"
