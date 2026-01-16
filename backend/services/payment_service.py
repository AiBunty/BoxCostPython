"""
Payment Processing Service
"""
from datetime import datetime
from typing import Optional, Dict, List

from sqlalchemy.orm import Session

from backend.models.payment import (
    PaymentMethod,
    Transaction,
    TransactionType,
    TransactionStatus,
    PaymentMethodType,
)
from backend.models.subscription import UserSubscription


class PaymentService:
    """Service for managing payments and transactions."""

    @staticmethod
    def create_payment_method(
        db: Session,
        user_id: int,
        tenant_id: int,
        payment_type: str,
        gateway: str = "stripe",
        gateway_payment_method_id: Optional[str] = None,
        gateway_customer_id: Optional[str] = None,
        last4: Optional[str] = None,
        brand: Optional[str] = None,
        exp_month: Optional[int] = None,
        exp_year: Optional[int] = None,
        billing_details: Optional[Dict] = None,
        is_default: bool = False,
    ) -> PaymentMethod:
        """
        Add a payment method for a user.
        
        Args:
            db: Database session
            user_id: User ID
            tenant_id: Tenant ID
            payment_type: card, bank_account, upi, wallet
            gateway: stripe, razorpay
            gateway_payment_method_id: Payment method ID from gateway
            gateway_customer_id: Customer ID from gateway
            last4: Last 4 digits
            brand: Card brand (visa, mastercard, etc.)
            exp_month: Expiration month
            exp_year: Expiration year
            billing_details: Billing address and info
            is_default: Set as default payment method
            
        Returns:
            Created PaymentMethod
        """
        # If setting as default, unset other defaults
        if is_default:
            db.query(PaymentMethod).filter(
                PaymentMethod.user_id == user_id,
                PaymentMethod.is_default == True
            ).update({"is_default": False})
        
        payment_method = PaymentMethod(
            user_id=user_id,
            tenant_id=tenant_id,
            type=payment_type,
            last4=last4,
            brand=brand,
            exp_month=exp_month,
            exp_year=exp_year,
            is_default=is_default,
            is_verified=True,  # Assume verified if from gateway
            billing_details=billing_details or {},
        )
        
        # Set gateway-specific ID
        if gateway == "stripe":
            payment_method.stripe_payment_method_id = gateway_payment_method_id
        elif gateway == "razorpay":
            payment_method.razorpay_token_id = gateway_payment_method_id
        
        payment_method.gateway_customer_id = gateway_customer_id
        
        db.add(payment_method)
        db.commit()
        db.refresh(payment_method)
        
        return payment_method

    @staticmethod
    def create_transaction(
        db: Session,
        user_id: int,
        tenant_id: int,
        amount: int,
        transaction_type: str = TransactionType.PAYMENT.value,
        status: str = TransactionStatus.PENDING.value,
        description: Optional[str] = None,
        subscription_id: Optional[int] = None,
        payment_method_id: Optional[int] = None,
        currency: str = "INR",
        metadata: Optional[Dict] = None,
    ) -> Transaction:
        """
        Create a transaction record.
        
        Args:
            db: Database session
            user_id: User ID
            tenant_id: Tenant ID
            amount: Amount in cents/paise
            transaction_type: payment, refund, adjustment
            status: pending, succeeded, failed
            description: Transaction description
            subscription_id: Related subscription ID
            payment_method_id: Payment method used
            currency: Currency code
            metadata: Additional metadata
            
        Returns:
            Created Transaction
        """
        transaction = Transaction(
            user_id=user_id,
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            amount=amount,
            currency=currency,
            description=description,
            type=transaction_type,
            status=status,
            payment_method_id=payment_method_id,
            metadata=metadata or {},
        )
        
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        return transaction

    @staticmethod
    def update_transaction_status(
        db: Session,
        transaction_id: int,
        status: str,
        gateway_charge_id: Optional[str] = None,
        gateway_payment_intent_id: Optional[str] = None,
        failure_code: Optional[str] = None,
        failure_message: Optional[str] = None,
    ) -> Transaction:
        """Update transaction status after payment processing."""
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()
        
        if not transaction:
            raise ValueError("Transaction not found")
        
        transaction.status = status
        
        if status == TransactionStatus.SUCCEEDED.value:
            transaction.paid_at = datetime.utcnow()
        elif status == TransactionStatus.REFUNDED.value:
            transaction.refunded_at = datetime.utcnow()
        
        # Update gateway IDs
        if gateway_charge_id:
            if "stripe" in str(gateway_charge_id):
                transaction.stripe_charge_id = gateway_charge_id
            else:
                transaction.razorpay_payment_id = gateway_charge_id
        
        if gateway_payment_intent_id:
            transaction.stripe_payment_intent_id = gateway_payment_intent_id
        
        # Update failure details
        if failure_code:
            transaction.failure_code = failure_code
            transaction.failure_message = failure_message
        
        db.commit()
        db.refresh(transaction)
        
        return transaction

    @staticmethod
    def get_user_transactions(
        db: Session,
        user_id: int,
        limit: int = 20,
        status: Optional[str] = None,
    ) -> List[Transaction]:
        """Get transaction history for a user."""
        query = db.query(Transaction).filter(
            Transaction.user_id == user_id
        )
        
        if status:
            query = query.filter(Transaction.status == status)
        
        return query.order_by(Transaction.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_default_payment_method(
        db: Session,
        user_id: int,
    ) -> Optional[PaymentMethod]:
        """Get user's default payment method."""
        return db.query(PaymentMethod).filter(
            PaymentMethod.user_id == user_id,
            PaymentMethod.is_default == True
        ).first()

    @staticmethod
    def delete_payment_method(
        db: Session,
        payment_method_id: int,
        user_id: int,
    ) -> bool:
        """Delete a payment method."""
        payment_method = db.query(PaymentMethod).filter(
            PaymentMethod.id == payment_method_id,
            PaymentMethod.user_id == user_id
        ).first()
        
        if not payment_method:
            return False
        
        db.delete(payment_method)
        db.commit()
        return True

    @staticmethod
    def calculate_proration(
        old_amount: int,
        new_amount: int,
        days_remaining: int,
        total_days: int,
    ) -> int:
        """
        Calculate prorated amount for plan changes.
        
        Returns:
            Proration amount in cents/paise (positive = charge, negative = credit)
        """
        if total_days == 0:
            return 0
        
        # Calculate daily rates
        old_daily = old_amount / total_days
        new_daily = new_amount / total_days
        
        # Calculate unused credit and new charge
        unused_credit = old_daily * days_remaining
        new_charge = new_daily * days_remaining
        
        return int(new_charge - unused_credit)


payment_service = PaymentService()
