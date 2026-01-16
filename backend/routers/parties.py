"""Party (Customer) management API."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Optional
from datetime import datetime

from backend.database import get_db
from backend.middleware.auth import get_current_user, get_tenant_context
from backend.models.user import User
from backend.models.party import PartyProfile
from shared.schemas import (
    PartyCreate,
    PartyUpdate,
    PartyResponse,
    PaginatedResponse
)

router = APIRouter(prefix="/api/parties", tags=["parties"])


@router.get("", response_model=PaginatedResponse)
async def list_parties(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_context)
):
    """
    List all parties (customers) for the current tenant.
    Supports search and filtering.
    """
    query = select(Party).where(Party.tenant_id == tenant_id)
    
    # Apply filters
    filters = []
    if search:
        filters.append(
            or_(
                Party.party_name.ilike(f"%{search}%"),
                Party.contact_person.ilike(f"%{search}%"),
                Party.email.ilike(f"%{search}%"),
                Party.phone.ilike(f"%{search}%")
            )
        )
    if is_active is not None:
        filters.append(Party.is_active == is_active)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Paginate and order
    query = query.order_by(Party.party_name).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    parties = result.scalars().all()
    
    return {
        "items": [PartyResponse.from_orm(p) for p in parties],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


@router.post("", response_model=PartyResponse)
async def create_party(
    party_data: PartyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_context)
):
    """
    Create a new party (customer).
    """
    # Check for duplicate party name within tenant
    existing = await db.execute(
        select(Party).where(
            and_(
                Party.tenant_id == tenant_id,
                Party.party_name == party_data.party_name
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Party with name '{party_data.party_name}' already exists"
        )
    
    party = Party(
        tenant_id=tenant_id,
        **party_data.dict()
    )
    db.add(party)
    await db.commit()
    await db.refresh(party)
    
    return PartyResponse.from_orm(party)


@router.get("/{party_id}", response_model=PartyResponse)
async def get_party(
    party_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_context)
):
    """
    Get party details by ID.
    """
    result = await db.execute(
        select(Party).where(
            and_(
                Party.id == party_id,
                Party.tenant_id == tenant_id
            )
        )
    )
    party = result.scalar_one_or_none()
    
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    return PartyResponse.from_orm(party)


@router.patch("/{party_id}", response_model=PartyResponse)
async def update_party(
    party_id: int,
    party_data: PartyUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_context)
):
    """
    Update party details.
    """
    result = await db.execute(
        select(Party).where(
            and_(
                Party.id == party_id,
                Party.tenant_id == tenant_id
            )
        )
    )
    party = result.scalar_one_or_none()
    
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Update fields
    update_data = party_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(party, field, value)
    
    await db.commit()
    await db.refresh(party)
    
    return PartyResponse.from_orm(party)


@router.delete("/{party_id}")
async def delete_party(
    party_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_context)
):
    """
    Soft delete a party (mark as inactive).
    """
    result = await db.execute(
        select(Party).where(
            and_(
                Party.id == party_id,
                Party.tenant_id == tenant_id
            )
        )
    )
    party = result.scalar_one_or_none()
    
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    party.is_active = False
    await db.commit()
    
    return {"message": "Party deleted successfully"}


@router.post("/{party_id}/activate")
async def activate_party(
    party_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_context)
):
    """
    Activate a previously deactivated party.
    """
    result = await db.execute(
        select(Party).where(
            and_(
                Party.id == party_id,
                Party.tenant_id == tenant_id
            )
        )
    )
    party = result.scalar_one_or_none()
    
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    party.is_active = True
    await db.commit()
    
    return {"message": "Party activated successfully"}
