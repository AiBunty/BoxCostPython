"""Paper pricing API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend.middleware.auth import get_current_user, get_current_tenant_id
from backend.models.user import User
from backend.models.pricing import (
    PaperBFPrice, PaperShade, ShadePremium,
    PaperPricingRule, BusinessDefault, FluteSettings
)
from shared.schemas import (
    PaperBFPriceCreate, PaperBFPriceResponse,
    PaperShadeResponse,
    ShadePremiumCreate, ShadePremiumResponse,
    BusinessDefaultCreate, BusinessDefaultResponse
)

router = APIRouter()


@router.get("/paper-bf-prices", response_model=List[PaperBFPriceResponse])
async def list_paper_bf_prices(
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """Get all BF-based paper prices for tenant."""
    prices = db.query(PaperBFPrice).filter(
        PaperBFPrice.tenant_id == tenant_id,
        PaperBFPrice.is_active == True
    ).order_by(PaperBFPrice.bf).all()
    
    return prices


@router.post("/paper-bf-prices", response_model=PaperBFPriceResponse, status_code=status.HTTP_201_CREATED)
async def create_paper_bf_price(
    data: PaperBFPriceCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """Create new BF price entry."""
    # Check if BF already exists for tenant
    existing = db.query(PaperBFPrice).filter(
        PaperBFPrice.tenant_id == tenant_id,
        PaperBFPrice.bf == data.bf
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"BF {data.bf} already exists"
        )
    
    price = PaperBFPrice(
        tenant_id=tenant_id,
        bf=data.bf,
        rate=data.rate
    )
    
    db.add(price)
    db.commit()
    db.refresh(price)
    
    return price


@router.get("/paper-shades", response_model=List[PaperShadeResponse])
async def list_paper_shades(db: Session = Depends(get_db)):
    """Get all available paper shades (global list)."""
    shades = db.query(PaperShade).filter(
        PaperShade.is_active == True
    ).order_by(PaperShade.display_order).all()
    
    return shades


@router.get("/shade-premiums", response_model=List[ShadePremiumResponse])
async def list_shade_premiums(
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """Get shade premiums for tenant."""
    premiums = db.query(ShadePremium).filter(
        ShadePremium.tenant_id == tenant_id,
        ShadePremium.is_active == True
    ).all()
    
    return premiums


@router.post("/shade-premiums", response_model=ShadePremiumResponse, status_code=status.HTTP_201_CREATED)
async def create_shade_premium(
    data: ShadePremiumCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """Create shade premium."""
    premium = ShadePremium(
        tenant_id=tenant_id,
        shade_id=data.shade_id,
        premium_amount=data.premium_amount
    )
    
    db.add(premium)
    db.commit()
    db.refresh(premium)
    
    return premium


@router.get("/business-defaults", response_model=BusinessDefaultResponse)
async def get_business_defaults(
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """Get business defaults for tenant."""
    defaults = db.query(BusinessDefault).filter(
        BusinessDefault.tenant_id == tenant_id
    ).first()
    
    if not defaults:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business defaults not configured"
        )
    
    return defaults


@router.post("/business-defaults", response_model=BusinessDefaultResponse)
async def create_or_update_business_defaults(
    data: BusinessDefaultCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """Create or update business defaults."""
    defaults = db.query(BusinessDefault).filter(
        BusinessDefault.tenant_id == tenant_id
    ).first()
    
    if defaults:
        # Update existing
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(defaults, field, value)
    else:
        # Create new
        defaults = BusinessDefault(
            tenant_id=tenant_id,
            **data.model_dump()
        )
        db.add(defaults)
    
    db.commit()
    db.refresh(defaults)
    
    return defaults
