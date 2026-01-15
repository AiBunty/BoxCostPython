"""Quote management API routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from backend.database import get_db
from backend.middleware.auth import get_current_user, get_current_tenant_id
from backend.models.user import User
from backend.models.quote import Quote, QuoteVersion, QuoteItem, QuoteStatus
from backend.models.party import PartyProfile
from backend.services.calculator import calculator, BoxSpecification, PaperLayer
from shared.schemas import (
    QuoteCreate, QuoteUpdate, QuoteResponse, QuoteDetailResponse,
    QuoteItemResponse, CalculateBoxRequest, CalculateBoxResponse
)

router = APIRouter()


@router.post("/calculate", response_model=CalculateBoxResponse)
async def calculate_box_cost(
    data: CalculateBoxRequest,
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Calculate box cost without creating a quote.
    Useful for real-time pricing during quote creation.
    """
    # Convert request to BoxSpecification
    paper_layers = [
        PaperLayer(
            bf=layer.bf,
            gsm=layer.gsm,
            shade=layer.shade,
            is_flute=layer.is_flute
        )
        for layer in data.paper_layers
    ]
    
    spec = BoxSpecification(
        length=data.length,
        width=data.width,
        height=data.height,
        ply=data.ply,
        quantity=data.quantity,
        paper_layers=paper_layers,
        fluting_factor=data.fluting_factor,
        conversion_rate=data.conversion_rate,
        printing_cost=data.printing_cost,
        die_cost=data.die_cost
    )
    
    # TODO: Fetch actual paper rates from database
    # For now, using dummy rates
    paper_rates = {
        (layer.bf, layer.gsm, layer.shade): 50.0
        for layer in paper_layers
    }
    
    result = calculator.calculate(spec, paper_rates)
    
    return CalculateBoxResponse(
        sheet_length=result.sheet_length,
        sheet_width=result.sheet_width,
        sheet_area=result.sheet_area,
        paper_weight=result.paper_weight,
        board_thickness=result.board_thickness,
        paper_cost=result.paper_cost,
        manufacturing_cost=result.manufacturing_cost,
        conversion_cost=result.conversion_cost,
        unit_cost=result.unit_cost,
        total_cost=result.total_cost,
        ect=result.ect,
        bct=result.bct,
        burst_strength=result.burst_strength
    )


@router.get("/quotes", response_model=List[QuoteResponse])
async def list_quotes(
    status: Optional[str] = Query(None),
    party_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """List quotes for current tenant with optional filters."""
    query = db.query(Quote).filter(
        Quote.tenant_id == tenant_id,
        Quote.is_active == True
    )
    
    if status:
        query = query.filter(Quote.status == status)
    
    if party_id:
        query = query.filter(Quote.party_id == party_id)
    
    # Pagination
    offset = (page - 1) * limit
    quotes = query.order_by(Quote.created_at.desc()).offset(offset).limit(limit).all()
    
    return quotes


@router.get("/quotes/{quote_id}", response_model=QuoteDetailResponse)
async def get_quote(
    quote_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """Get quote by ID with full details."""
    quote = db.query(Quote).filter(
        Quote.id == quote_id,
        Quote.tenant_id == tenant_id
    ).first()
    
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    
    # Get latest version items
    items = db.query(QuoteItem).filter(
        QuoteItem.quote_id == quote_id,
        QuoteItem.version_id == quote.current_version
    ).all()
    
    # Get party details
    party = db.query(PartyProfile).filter(
        PartyProfile.id == quote.party_id
    ).first()
    
    return QuoteDetailResponse(
        **quote.__dict__,
        items=[QuoteItemResponse.model_validate(item) for item in items],
        party=party
    )


@router.post("/quotes", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_quote(
    data: QuoteCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """Create new quote with items."""
    # Verify party exists
    party = db.query(PartyProfile).filter(
        PartyProfile.id == data.party_id,
        PartyProfile.tenant_id == tenant_id
    ).first()
    
    if not party:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Party not found"
        )
    
    # Create quote master record
    quote = Quote(
        tenant_id=tenant_id,
        user_id=current_user.id,
        party_id=data.party_id,
        current_version=1,
        status=QuoteStatus.DRAFT,
        valid_until=datetime.utcnow() + timedelta(days=data.validity_days)
    )
    
    db.add(quote)
    db.flush()  # Get quote.id
    
    # Create quote version
    version = QuoteVersion(
        quote_id=quote.id,
        version=1,
        created_by=current_user.id,
        payment_terms=data.payment_terms,
        delivery_terms=data.delivery_terms,
        validity_days=data.validity_days,
        notes=data.notes
    )
    
    db.add(version)
    db.flush()  # Get version.id
    
    # Create quote items with calculations
    for item_data in data.items:
        # TODO: Calculate costs using calculator service
        # For now, using dummy values
        
        item = QuoteItem(
            quote_id=quote.id,
            version_id=version.id,
            line_number=item_data.line_number,
            box_name=item_data.box_name,
            length=item_data.length,
            width=item_data.width,
            height=item_data.height,
            ply=item_data.ply,
            quantity=item_data.quantity,
            paper_specs=item_data.paper_specs,
            unit_cost=100.0,  # TODO: Calculate
            total_cost=100.0 * item_data.quantity,  # TODO: Calculate
            printing_cost=item_data.printing_cost,
            die_cost=item_data.die_cost,
            conversion_rate=item_data.conversion_rate
        )
        
        db.add(item)
    
    db.commit()
    db.refresh(quote)
    
    return quote


@router.patch("/quotes/{quote_id}", response_model=QuoteResponse)
async def update_quote(
    quote_id: int,
    data: QuoteUpdate,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """Update quote - creates new version."""
    quote = db.query(Quote).filter(
        Quote.id == quote_id,
        Quote.tenant_id == tenant_id
    ).first()
    
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    
    if quote.is_negotiated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit negotiated quote"
        )
    
    # Increment version
    new_version_number = quote.current_version + 1
    quote.current_version = new_version_number
    
    # Create new version
    # TODO: Implement version creation logic
    
    db.commit()
    db.refresh(quote)
    
    return quote


@router.delete("/quotes/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote(
    quote_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """Soft delete quote."""
    quote = db.query(Quote).filter(
        Quote.id == quote_id,
        Quote.tenant_id == tenant_id
    ).first()
    
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    
    quote.is_active = False
    db.commit()
    
    return None
