"""Paper pricing models - BF prices, shades, and premiums."""
from sqlalchemy import Column, Integer, String, Numeric, Boolean, Text, UniqueConstraint
from backend.database import Base, BaseMixin, TenantMixin


class PaperBFPrice(Base, BaseMixin, TenantMixin):
    """
    Paper Base Price by Bursting Factor (BF).
    Single source of truth for paper base pricing.
    """
    __tablename__ = "paper_bf_prices"
    
    bf = Column(Integer, nullable=False)  # Bursting Factor (e.g., 10, 12, 14)
    rate = Column(Numeric(10, 2), nullable=False)  # Rate per kg
    
    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'bf', name='unique_tenant_bf'),
    )
    
    def __repr__(self):
        return f"<PaperBFPrice(bf={self.bf}, rate={self.rate})>"


class PaperShade(Base, BaseMixin):
    """
    Master list of paper shades with canonical abbreviations.
    Global table (not tenant-specific).
    """
    __tablename__ = "paper_shades"
    
    name = Column(String(100), unique=True, nullable=False)  # Full name (e.g., "Kraft")
    abbreviation = Column(String(10), unique=True, nullable=False)  # Short code (e.g., "KRA")
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<PaperShade(name={self.name}, abbr={self.abbreviation})>"


class ShadePremium(Base, BaseMixin, TenantMixin):
    """
    Premium pricing for specific paper shades.
    Added to base BF price for premium shades like White, Golden.
    """
    __tablename__ = "shade_premiums"
    
    shade_id = Column(Integer, nullable=False, index=True)  # FK to paper_shades
    premium_amount = Column(Numeric(10, 2), nullable=False)  # Premium per kg
    
    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'shade_id', name='unique_tenant_shade'),
    )
    
    def __repr__(self):
        return f"<ShadePremium(shade_id={self.shade_id}, premium={self.premium_amount})>"


class PaperPricingRule(Base, BaseMixin, TenantMixin):
    """
    Pricing rules for GSM adjustments and market factors.
    Single source of truth for pricing logic.
    """
    __tablename__ = "paper_pricing_rules"
    
    # GSM Adjustment Rules
    low_gsm_threshold = Column(Integer, default=101, nullable=False)  # GSM <= this gets adjustment
    low_gsm_adjustment = Column(Numeric(10, 2), default=0, nullable=False)  # Amount to add/subtract
    
    high_gsm_threshold = Column(Integer, default=201, nullable=False)  # GSM >= this gets adjustment
    high_gsm_adjustment = Column(Numeric(10, 2), default=0, nullable=False)
    
    # Market Adjustment
    market_adjustment = Column(Numeric(10, 2), default=0, nullable=False)  # Global +/- adjustment
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<PaperPricingRule(tenant_id={self.tenant_id})>"


class BusinessDefault(Base, BaseMixin, TenantMixin):
    """
    Business defaults for GST and tax settings.
    Single source of truth for tax configuration.
    """
    __tablename__ = "business_defaults"
    
    # GST Configuration
    gst_rate = Column(Numeric(5, 2), default=5.00, nullable=False)  # GST percentage (5% for boxes in India)
    is_gst_registered = Column(Boolean, default=True, nullable=False)
    apply_igst = Column(Boolean, default=False, nullable=False)  # Inter-state GST
    
    # Rounding
    enable_rounding = Column(Boolean, default=True, nullable=False)
    
    # Default Values
    default_payment_terms = Column(Text, nullable=True)
    default_delivery_time = Column(String(100), nullable=True)
    
    # Column Visibility (for quote templates)
    show_deckle = Column(Boolean, default=True, nullable=False)
    show_unit_price = Column(Boolean, default=True, nullable=False)
    show_total_price = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<BusinessDefault(tenant_id={self.tenant_id}, gst_rate={self.gst_rate})>"


class FluteSettings(Base, BaseMixin, TenantMixin):
    """
    Fluting factors for corrugated board calculations.
    Used in paper weight and thickness calculations.
    """
    __tablename__ = "flute_settings"
    
    flute_type = Column(String(1), nullable=False)  # A, B, C, E, F
    fluting_factor = Column(Numeric(5, 4), nullable=False)  # e.g., 1.35 for A-flute
    flute_height = Column(Numeric(5, 3), nullable=True)  # Height in mm
    
    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'flute_type', name='unique_tenant_flute'),
    )
    
    def __repr__(self):
        return f"<FluteSettings(flute={self.flute_type}, factor={self.fluting_factor})>"
