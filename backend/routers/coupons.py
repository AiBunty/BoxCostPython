"""Coupon management API router."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_admin, get_current_user, get_current_tenant_id
from backend.models.admin import Admin
from backend.models.coupon import Coupon, CouponUsage, CouponType, CouponStatus
from backend.models.user import User


# Schemas
class CouponCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    coupon_type: CouponType
    discount_value: Decimal = Field(gt=0)
    max_uses: Optional[int] = None
    max_uses_per_user: Optional[int] = None
    min_purchase_amount: Optional[Decimal] = None
    valid_from: datetime
    valid_until: Optional[datetime] = None
    applies_to: Optional[str] = None
    plan_ids: Optional[str] = None
    is_public: bool = False


class CouponUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_value: Optional[Decimal] = None
    max_uses: Optional[int] = None
    max_uses_per_user: Optional[int] = None
    min_purchase_amount: Optional[Decimal] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    status: Optional[CouponStatus] = None
    is_public: Optional[bool] = None


class CouponResponse(BaseModel):
    id: int
    tenant_id: int
    code: str
    name: str
    description: Optional[str]
    coupon_type: CouponType
    discount_value: Decimal
    max_uses: Optional[int]
    uses_count: int
    max_uses_per_user: Optional[int]
    min_purchase_amount: Optional[Decimal]
    valid_from: datetime
    valid_until: Optional[datetime]
    applies_to: Optional[str]
    plan_ids: Optional[str]
    status: CouponStatus
    is_public: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CouponValidateRequest(BaseModel):
    code: str
    purchase_amount: Optional[Decimal] = None
    plan_id: Optional[int] = None


class CouponValidateResponse(BaseModel):
    valid: bool
    coupon: Optional[CouponResponse] = None
    discount_amount: Optional[Decimal] = None
    final_amount: Optional[Decimal] = None
    error: Optional[str] = None


class CouponUsageResponse(BaseModel):
    id: int
    coupon_id: int
    user_id: int
    tenant_id: int
    applied_to_type: str
    applied_to_id: int
    original_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    used_at: datetime

    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix="/api/coupons", tags=["Coupons"])


@router.get("", response_model=List[CouponResponse])
async def list_coupons(
    status_filter: Optional[CouponStatus] = Query(None, alias="status"),
    is_public: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_admin: Admin = Depends(get_current_admin),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """List all coupons (admin only)."""
    query = db.query(Coupon).filter(Coupon.tenant_id == tenant_id)

    if status_filter:
        query = query.filter(Coupon.status == status_filter)
    if is_public is not None:
        query = query.filter(Coupon.is_public == is_public)

    coupons = (
        query.order_by(Coupon.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return [CouponResponse.model_validate(c) for c in coupons]


@router.post("", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
async def create_coupon(
    data: CouponCreate,
    current_admin: Admin = Depends(get_current_admin),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Create a new coupon (admin only)."""
    existing = db.query(Coupon).filter(Coupon.code == data.code.upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Coupon code '{data.code}' already exists"
        )

    coupon = Coupon(
        tenant_id=tenant_id,
        code=data.code.upper(),
        name=data.name,
        description=data.description,
        coupon_type=data.coupon_type,
        discount_value=data.discount_value,
        max_uses=data.max_uses,
        max_uses_per_user=data.max_uses_per_user,
        min_purchase_amount=data.min_purchase_amount,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        applies_to=data.applies_to,
        plan_ids=data.plan_ids,
        is_public=data.is_public,
        status=CouponStatus.ACTIVE,
        created_by_admin_id=current_admin.id,
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return CouponResponse.model_validate(coupon)


@router.get("/{coupon_id}", response_model=CouponResponse)
async def get_coupon(
    coupon_id: int,
    current_admin: Admin = Depends(get_current_admin),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get coupon details (admin only)."""
    coupon = db.query(Coupon).filter(
        and_(Coupon.id == coupon_id, Coupon.tenant_id == tenant_id)
    ).first()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")
    return CouponResponse.model_validate(coupon)


@router.patch("/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    coupon_id: int,
    data: CouponUpdate,
    current_admin: Admin = Depends(get_current_admin),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Update coupon (admin only)."""
    coupon = db.query(Coupon).filter(
        and_(Coupon.id == coupon_id, Coupon.tenant_id == tenant_id)
    ).first()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(coupon, field, value)

    db.commit()
    db.refresh(coupon)
    return CouponResponse.model_validate(coupon)


@router.delete("/{coupon_id}")
async def delete_coupon(
    coupon_id: int,
    current_admin: Admin = Depends(get_current_admin),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Disable a coupon (admin only)."""
    coupon = db.query(Coupon).filter(
        and_(Coupon.id == coupon_id, Coupon.tenant_id == tenant_id)
    ).first()
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found")

    coupon.status = CouponStatus.DISABLED
    db.commit()
    return {"message": "Coupon disabled successfully"}


@router.post("/validate", response_model=CouponValidateResponse)
async def validate_coupon(
    data: CouponValidateRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Validate a coupon code for a user."""
    coupon = db.query(Coupon).filter(
        and_(
            Coupon.code == data.code.upper(),
            Coupon.tenant_id == tenant_id
        )
    ).first()

    if not coupon:
        return CouponValidateResponse(valid=False, error="Invalid coupon code")

    if not coupon.is_valid():
        return CouponValidateResponse(valid=False, error="Coupon is expired or inactive")

    # Check per-user limit
    if coupon.max_uses_per_user:
        usage_count = db.query(CouponUsage).filter(
            and_(
                CouponUsage.coupon_id == coupon.id,
                CouponUsage.user_id == current_user.id
            )
        ).count()
        if usage_count >= coupon.max_uses_per_user:
            return CouponValidateResponse(valid=False, error="Coupon usage limit reached")

    # Check min purchase amount
    if data.purchase_amount and coupon.min_purchase_amount:
        if data.purchase_amount < coupon.min_purchase_amount:
            return CouponValidateResponse(
                valid=False,
                error=f"Minimum purchase amount is {coupon.min_purchase_amount}"
            )

    # Calculate discount
    discount_amount = Decimal("0")
    final_amount = data.purchase_amount or Decimal("0")

    if data.purchase_amount:
        if coupon.coupon_type == CouponType.PERCENTAGE:
            discount_amount = (data.purchase_amount * coupon.discount_value) / Decimal("100")
        else:
            discount_amount = coupon.discount_value
        
        discount_amount = min(discount_amount, data.purchase_amount)
        final_amount = data.purchase_amount - discount_amount

    return CouponValidateResponse(
        valid=True,
        coupon=CouponResponse.model_validate(coupon),
        discount_amount=discount_amount,
        final_amount=final_amount,
    )


@router.get("/usage/history", response_model=List[CouponUsageResponse])
async def get_coupon_usage_history(
    coupon_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_admin: Admin = Depends(get_current_admin),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Get coupon usage history (admin only)."""
    query = db.query(CouponUsage).filter(CouponUsage.tenant_id == tenant_id)

    if coupon_id:
        query = query.filter(CouponUsage.coupon_id == coupon_id)
    if user_id:
        query = query.filter(CouponUsage.user_id == user_id)

    usages = (
        query.order_by(CouponUsage.used_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return [CouponUsageResponse.model_validate(u) for u in usages]
