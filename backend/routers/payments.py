"""
Payment Management API
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_user, get_current_admin
from backend.models.user import User
from backend.models.admin import Admin
from backend.models.payment import PaymentMethod, Transaction
from backend.services.payment_service import payment_service


# Schemas
class PaymentMethodCreate(BaseModel):
    payment_type: str  # card, bank_account, upi, wallet
    gateway: str = "stripe"  # stripe, razorpay
    gateway_payment_method_id: str
    gateway_customer_id: Optional[str] = None
    last4: Optional[str] = None
    brand: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    is_default: bool = False


class PaymentMethodResponse(BaseModel):
    id: int
    type: str
    last4: Optional[str]
    brand: Optional[str]
    exp_month: Optional[int]
    exp_year: Optional[int]
    is_default: bool
    is_verified: bool
    created_at: str

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    id: int
    amount: int
    currency: str
    type: str
    status: str
    description: Optional[str]
    paid_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


router = APIRouter(prefix="/api/payments", tags=["Payments"])


# Payment Methods
@router.post("/methods", response_model=PaymentMethodResponse)
async def add_payment_method(
    data: PaymentMethodCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new payment method."""
    try:
        payment_method = payment_service.create_payment_method(
            db=db,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            payment_type=data.payment_type,
            gateway=data.gateway,
            gateway_payment_method_id=data.gateway_payment_method_id,
            gateway_customer_id=data.gateway_customer_id,
            last4=data.last4,
            brand=data.brand,
            exp_month=data.exp_month,
            exp_year=data.exp_year,
            is_default=data.is_default,
        )
        return payment_method
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/methods", response_model=List[PaymentMethodResponse])
async def list_payment_methods(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all payment methods for current user."""
    methods = db.query(PaymentMethod).filter(
        PaymentMethod.user_id == current_user.id
    ).all()
    return methods


@router.get("/methods/default", response_model=PaymentMethodResponse)
async def get_default_payment_method(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get default payment method."""
    method = payment_service.get_default_payment_method(
        db=db,
        user_id=current_user.id
    )
    
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No default payment method found"
        )
    
    return method


@router.post("/methods/{method_id}/default")
async def set_default_payment_method(
    method_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set a payment method as default."""
    # Verify ownership
    method = db.query(PaymentMethod).filter(
        PaymentMethod.id == method_id,
        PaymentMethod.user_id == current_user.id
    ).first()
    
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    # Unset other defaults
    db.query(PaymentMethod).filter(
        PaymentMethod.user_id == current_user.id,
        PaymentMethod.is_default == True
    ).update({"is_default": False})
    
    # Set this as default
    method.is_default = True
    db.commit()
    
    return {"message": "Default payment method updated"}


@router.delete("/methods/{method_id}")
async def delete_payment_method(
    method_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a payment method."""
    success = payment_service.delete_payment_method(
        db=db,
        payment_method_id=method_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    return {"message": "Payment method deleted"}


# Transactions
@router.get("/transactions", response_model=List[TransactionResponse])
async def list_transactions(
    limit: int = 20,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List transaction history."""
    transactions = payment_service.get_user_transactions(
        db=db,
        user_id=current_user.id,
        limit=limit,
        status=status_filter
    )
    return transactions


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get transaction details."""
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return transaction


# Admin endpoints
@router.get("/admin/transactions", response_model=List[TransactionResponse])
async def list_all_transactions(
    user_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all transactions (admin only)."""
    query = db.query(Transaction)
    
    if user_id:
        query = query.filter(Transaction.user_id == user_id)
    if status_filter:
        query = query.filter(Transaction.status == status_filter)
    
    transactions = query.order_by(Transaction.created_at.desc()).limit(limit).all()
    return transactions
