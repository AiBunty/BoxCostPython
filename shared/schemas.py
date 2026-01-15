"""Pydantic schemas for API request/response validation."""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    clerk_user_id: str


class UserResponse(UserBase):
    id: int
    clerk_user_id: str
    role: str
    approval_status: str
    email_verified: bool
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Company Profile Schemas
class CompanyProfileBase(BaseModel):
    company_name: str
    gst_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


class CompanyProfileCreate(CompanyProfileBase):
    pass


class CompanyProfileResponse(CompanyProfileBase):
    id: int
    tenant_id: int
    user_id: int
    is_default: bool
    is_locked: bool
    gst_verified: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Party Profile Schemas
class PartyProfileBase(BaseModel):
    party_name: str
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gst_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class PartyProfileCreate(PartyProfileBase):
    pass


class PartyProfileUpdate(BaseModel):
    party_name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class PartyProfileResponse(PartyProfileBase):
    id: int
    tenant_id: int
    user_id: int
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Paper Pricing Schemas
class PaperBFPriceBase(BaseModel):
    bf: int = Field(gt=0, description="Bursting Factor")
    rate: Decimal = Field(gt=0, description="Rate per kg")


class PaperBFPriceCreate(PaperBFPriceBase):
    pass


class PaperBFPriceResponse(PaperBFPriceBase):
    id: int
    tenant_id: int
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PaperShadeResponse(BaseModel):
    id: int
    name: str
    abbreviation: str
    description: Optional[str] = None
    display_order: int
    
    model_config = ConfigDict(from_attributes=True)


class ShadePremiumBase(BaseModel):
    shade_id: int
    premium_amount: Decimal


class ShadePremiumCreate(ShadePremiumBase):
    pass


class ShadePremiumResponse(ShadePremiumBase):
    id: int
    tenant_id: int
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class BusinessDefaultBase(BaseModel):
    gst_rate: Decimal = Field(default=Decimal("5.00"), ge=0, le=100)
    is_gst_registered: bool = True
    enable_rounding: bool = True


class BusinessDefaultCreate(BusinessDefaultBase):
    pass


class BusinessDefaultResponse(BusinessDefaultBase):
    id: int
    tenant_id: int
    apply_igst: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Quote Schemas
class PaperLayerSchema(BaseModel):
    """Schema for a single paper layer."""
    bf: int
    gsm: int
    shade: str
    is_flute: bool = False


class QuoteItemBase(BaseModel):
    line_number: int
    box_name: Optional[str] = None
    length: Decimal = Field(gt=0, description="Length in mm")
    width: Decimal = Field(gt=0, description="Width in mm")
    height: Decimal = Field(gt=0, description="Height in mm")
    ply: int = Field(ge=3, le=9, description="Ply count")
    quantity: int = Field(gt=0)
    paper_specs: List[dict]  # List of paper layers


class QuoteItemCreate(QuoteItemBase):
    printing_cost: Optional[Decimal] = Decimal("0")
    die_cost: Optional[Decimal] = Decimal("0")
    conversion_rate: Optional[Decimal] = Decimal("15")


class QuoteItemResponse(QuoteItemBase):
    id: int
    quote_id: int
    version_id: int
    unit_cost: Decimal
    total_cost: Decimal
    negotiated_price: Optional[Decimal] = None
    sheet_length: Optional[Decimal] = None
    sheet_width: Optional[Decimal] = None
    paper_weight: Optional[Decimal] = None
    ect: Optional[Decimal] = None
    bct: Optional[Decimal] = None
    burst_strength: Optional[Decimal] = None
    
    model_config = ConfigDict(from_attributes=True)


class QuoteCreate(BaseModel):
    party_id: int
    items: List[QuoteItemCreate]
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    validity_days: int = 7
    notes: Optional[str] = None


class QuoteUpdate(BaseModel):
    items: Optional[List[QuoteItemCreate]] = None
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    notes: Optional[str] = None


class QuoteResponse(BaseModel):
    id: int
    tenant_id: int
    user_id: int
    party_id: int
    quote_number: Optional[str] = None
    current_version: int
    status: str
    valid_until: Optional[datetime] = None
    is_negotiated: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class QuoteDetailResponse(QuoteResponse):
    """Full quote with items."""
    items: List[QuoteItemResponse] = []
    party: Optional[PartyProfileResponse] = None


# Calculation Request/Response
class CalculateBoxRequest(BaseModel):
    """Request schema for box cost calculation."""
    length: float = Field(gt=0, description="Length in mm")
    width: float = Field(gt=0, description="Width in mm")
    height: float = Field(gt=0, description="Height in mm")
    ply: int = Field(ge=3, le=9)
    quantity: int = Field(gt=0)
    paper_layers: List[PaperLayerSchema]
    fluting_factor: float = 1.35
    conversion_rate: float = 15.0
    printing_cost: float = 0.0
    die_cost: float = 0.0


class CalculateBoxResponse(BaseModel):
    """Response schema for box cost calculation."""
    sheet_length: float
    sheet_width: float
    sheet_area: float
    paper_weight: float
    board_thickness: float
    paper_cost: float
    manufacturing_cost: float
    conversion_cost: float
    unit_cost: float
    total_cost: float
    ect: Optional[float] = None
    bct: Optional[float] = None
    burst_strength: Optional[float] = None


# Pagination
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    limit: int
    pages: int


# Party Schemas
class PartyBase(BaseModel):
    party_name: str
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gst_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    is_active: bool = True


class PartyCreate(PartyBase):
    pass


class PartyUpdate(BaseModel):
    party_name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gst_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    is_active: Optional[bool] = None


class PartyResponse(PartyBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Subscription Schemas
class SubscriptionPlanResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str]
    price_monthly: Decimal
    price_yearly: Decimal
    features: dict
    quotas: dict
    is_active: bool
    sort_order: int
    
    model_config = ConfigDict(from_attributes=True)


class UserSubscriptionResponse(BaseModel):
    id: int
    user_id: int
    plan_id: int
    status: str
    starts_at: datetime
    ends_at: Optional[datetime]
    billing_cycle: str
    auto_renew: bool
    
    model_config = ConfigDict(from_attributes=True)


class EntitlementResponse(BaseModel):
    subscription_id: int
    plan_name: str
    status: str
    features: dict
    quotas: dict
    overrides_applied: List[dict]
    computed_at: str


# Invoice Schemas
class InvoiceCreate(BaseModel):
    invoice_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    buyer_name: str
    buyer_address: str
    buyer_gst: Optional[str] = None
    buyer_pan: Optional[str] = None
    subtotal: Decimal
    gst_rate: Decimal = Decimal("18.0")
    notes: Optional[str] = None
    terms: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: int
    tenant_id: int
    invoice_number: str
    invoice_date: datetime
    due_date: Optional[datetime]
    seller_name: str
    seller_address: str
    seller_gst: Optional[str]
    buyer_name: str
    buyer_address: str
    buyer_gst: Optional[str]
    subtotal: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    total_gst: Decimal
    total_amount: Decimal
    status: str
    paid_at: Optional[datetime]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Admin Schemas
class AdminLoginResponse(BaseModel):
    admin_id: int
    session_token: str
    expires_at: datetime
    requires_2fa: bool = False


class SupportTicketResponse(BaseModel):
    id: int
    ticket_number: str
    user_id: int
    subject: str
    priority: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)
