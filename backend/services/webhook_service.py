"""
Webhook signature verification and event processing.
Supports Stripe and Razorpay webhook validation.
"""
import hashlib
import hmac
import json
from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import HTTPException, status


class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails."""
    pass


class StripeWebhookValidator:
    """Stripe webhook signature verification."""
    
    @staticmethod
    def verify_signature(
        payload: bytes,
        signature_header: str,
        webhook_secret: str,
        tolerance: int = 300
    ) -> Dict[str, Any]:
        """
        Verify Stripe webhook signature.
        
        Args:
            payload: Raw request body bytes
            signature_header: Stripe-Signature header value
            webhook_secret: Webhook signing secret from Stripe
            tolerance: Maximum age of webhook in seconds (default 5 minutes)
            
        Returns:
            Parsed webhook event data
            
        Raises:
            WebhookVerificationError: If signature is invalid
        """
        if not signature_header or not webhook_secret:
            raise WebhookVerificationError("Missing signature or secret")
        
        # Parse signature header
        sig_data = {}
        for item in signature_header.split(','):
            key, value = item.split('=')
            sig_data[key] = value
        
        if 't' not in sig_data or 'v1' not in sig_data:
            raise WebhookVerificationError("Invalid signature format")
        
        timestamp = int(sig_data['t'])
        signatures = sig_data['v1'].split(',')
        
        # Check timestamp tolerance
        current_time = int(datetime.utcnow().timestamp())
        if abs(current_time - timestamp) > tolerance:
            raise WebhookVerificationError("Webhook timestamp too old")
        
        # Compute expected signature
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected_sig = hmac.new(
            webhook_secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        if not any(hmac.compare_digest(expected_sig, sig) for sig in signatures):
            raise WebhookVerificationError("Signature verification failed")
        
        # Parse and return event data
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            raise WebhookVerificationError("Invalid JSON payload")


class RazorpayWebhookValidator:
    """Razorpay webhook signature verification."""
    
    @staticmethod
    def verify_signature(
        payload: bytes,
        signature_header: str,
        webhook_secret: str
    ) -> Dict[str, Any]:
        """
        Verify Razorpay webhook signature.
        
        Args:
            payload: Raw request body bytes
            signature_header: X-Razorpay-Signature header value
            webhook_secret: Webhook secret from Razorpay
            
        Returns:
            Parsed webhook event data
            
        Raises:
            WebhookVerificationError: If signature is invalid
        """
        if not signature_header or not webhook_secret:
            raise WebhookVerificationError("Missing signature or secret")
        
        # Compute expected signature
        expected_sig = hmac.new(
            webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        if not hmac.compare_digest(expected_sig, signature_header):
            raise WebhookVerificationError("Signature verification failed")
        
        # Parse and return event data
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            raise WebhookVerificationError("Invalid JSON payload")


class WebhookProcessor:
    """Process verified webhook events."""
    
    def __init__(self, db):
        self.db = db
    
    async def process_stripe_event(self, event: Dict[str, Any]) -> Dict[str, str]:
        """
        Process Stripe webhook event.
        
        Args:
            event: Verified Stripe event data
            
        Returns:
            Processing result
        """
        event_type = event.get('type')
        event_data = event.get('data', {}).get('object', {})
        
        handlers = {
            'payment_intent.succeeded': self._handle_payment_succeeded,
            'payment_intent.failed': self._handle_payment_failed,
            'payment_intent.canceled': self._handle_payment_canceled,
            'charge.succeeded': self._handle_charge_succeeded,
            'charge.failed': self._handle_charge_failed,
            'charge.refunded': self._handle_charge_refunded,
            'invoice.payment_succeeded': self._handle_invoice_paid,
            'invoice.payment_failed': self._handle_invoice_failed,
            'customer.subscription.created': self._handle_subscription_created,
            'customer.subscription.updated': self._handle_subscription_updated,
            'customer.subscription.deleted': self._handle_subscription_canceled,
        }
        
        handler = handlers.get(event_type)
        if handler:
            return await handler(event_data)
        
        return {"status": "ignored", "message": f"No handler for event type: {event_type}"}
    
    async def process_razorpay_event(self, event: Dict[str, Any]) -> Dict[str, str]:
        """
        Process Razorpay webhook event.
        
        Args:
            event: Verified Razorpay event data
            
        Returns:
            Processing result
        """
        event_type = event.get('event')
        event_data = event.get('payload', {})
        
        handlers = {
            'payment.authorized': self._handle_razorpay_payment_authorized,
            'payment.captured': self._handle_razorpay_payment_captured,
            'payment.failed': self._handle_razorpay_payment_failed,
            'order.paid': self._handle_razorpay_order_paid,
            'subscription.charged': self._handle_razorpay_subscription_charged,
            'subscription.cancelled': self._handle_razorpay_subscription_cancelled,
            'subscription.activated': self._handle_razorpay_subscription_activated,
        }
        
        handler = handlers.get(event_type)
        if handler:
            return await handler(event_data)
        
        return {"status": "ignored", "message": f"No handler for event type: {event_type}"}
    
    # Stripe event handlers
    async def _handle_payment_succeeded(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle successful payment intent."""
        from backend.models.payment import Transaction, TransactionStatus
        
        payment_intent_id = data.get('id')
        amount = data.get('amount')
        currency = data.get('currency', 'usd').upper()
        
        # Find and update transaction
        transaction = self.db.query(Transaction).filter(
            Transaction.stripe_payment_intent_id == payment_intent_id
        ).first()
        
        if transaction:
            transaction.status = TransactionStatus.SUCCEEDED.value
            transaction.paid_at = datetime.utcnow()
            self.db.commit()
            return {"status": "processed", "transaction_id": transaction.id}
        
        return {"status": "not_found", "message": f"Transaction not found for payment intent {payment_intent_id}"}
    
    async def _handle_payment_failed(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle failed payment intent."""
        from backend.models.payment import Transaction, TransactionStatus
        
        payment_intent_id = data.get('id')
        error = data.get('last_payment_error', {})
        
        transaction = self.db.query(Transaction).filter(
            Transaction.stripe_payment_intent_id == payment_intent_id
        ).first()
        
        if transaction:
            transaction.status = TransactionStatus.FAILED.value
            transaction.failure_code = error.get('code')
            transaction.failure_message = error.get('message')
            self.db.commit()
            return {"status": "processed", "transaction_id": transaction.id}
        
        return {"status": "not_found"}
    
    async def _handle_payment_canceled(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle canceled payment intent."""
        from backend.models.payment import Transaction, TransactionStatus
        
        payment_intent_id = data.get('id')
        
        transaction = self.db.query(Transaction).filter(
            Transaction.stripe_payment_intent_id == payment_intent_id
        ).first()
        
        if transaction:
            transaction.status = TransactionStatus.CANCELED.value
            self.db.commit()
            return {"status": "processed", "transaction_id": transaction.id}
        
        return {"status": "not_found"}
    
    async def _handle_charge_succeeded(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle successful charge."""
        charge_id = data.get('id')
        receipt_url = data.get('receipt_url')
        
        from backend.models.payment import Transaction
        
        transaction = self.db.query(Transaction).filter(
            Transaction.stripe_charge_id == charge_id
        ).first()
        
        if transaction:
            transaction.receipt_url = receipt_url
            self.db.commit()
            return {"status": "processed", "transaction_id": transaction.id}
        
        return {"status": "not_found"}
    
    async def _handle_charge_failed(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle failed charge."""
        return {"status": "processed", "message": "Charge failure logged"}
    
    async def _handle_charge_refunded(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle charge refund."""
        from backend.models.payment import Transaction, TransactionStatus
        
        charge_id = data.get('id')
        
        transaction = self.db.query(Transaction).filter(
            Transaction.stripe_charge_id == charge_id
        ).first()
        
        if transaction:
            transaction.status = TransactionStatus.REFUNDED.value
            transaction.refunded_at = datetime.utcnow()
            self.db.commit()
            return {"status": "processed", "transaction_id": transaction.id}
        
        return {"status": "not_found"}
    
    async def _handle_invoice_paid(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle paid invoice."""
        invoice_id = data.get('id')
        subscription_id = data.get('subscription')
        
        # Update subscription status if needed
        if subscription_id:
            from backend.models.subscription import UserSubscription, SubscriptionStatus
            
            subscription = self.db.query(UserSubscription).filter(
                UserSubscription.razorpay_subscription_id == subscription_id
            ).first()
            
            if subscription and subscription.status != SubscriptionStatus.ACTIVE:
                subscription.status = SubscriptionStatus.ACTIVE
                self.db.commit()
        
        return {"status": "processed", "invoice_id": invoice_id}
    
    async def _handle_invoice_failed(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle failed invoice payment."""
        invoice_id = data.get('id')
        subscription_id = data.get('subscription')
        
        # Mark subscription for attention
        if subscription_id:
            from backend.models.subscription import UserSubscription, SubscriptionStatus
            
            subscription = self.db.query(UserSubscription).filter(
                UserSubscription.razorpay_subscription_id == subscription_id
            ).first()
            
            if subscription:
                # Don't immediately cancel, but mark for follow-up
                # In production, implement retry logic
                pass
        
        return {"status": "processed", "invoice_id": invoice_id, "action": "payment_failed_logged"}
    
    async def _handle_subscription_created(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle subscription creation."""
        return {"status": "processed", "message": "Subscription created"}
    
    async def _handle_subscription_updated(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle subscription update."""
        subscription_id = data.get('id')
        status = data.get('status')
        
        from backend.models.subscription import UserSubscription, SubscriptionStatus
        
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.razorpay_subscription_id == subscription_id
        ).first()
        
        if subscription:
            # Map Stripe status to internal status
            status_map = {
                'active': SubscriptionStatus.ACTIVE,
                'canceled': SubscriptionStatus.CANCELLED,
                'past_due': SubscriptionStatus.SUSPENDED,
                'unpaid': SubscriptionStatus.SUSPENDED,
            }
            
            new_status = status_map.get(status)
            if new_status:
                subscription.status = new_status
                self.db.commit()
        
        return {"status": "processed", "subscription_id": subscription_id}
    
    async def _handle_subscription_canceled(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle subscription cancellation."""
        subscription_id = data.get('id')
        
        from backend.models.subscription import UserSubscription, SubscriptionStatus
        
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.razorpay_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = datetime.utcnow()
            self.db.commit()
        
        return {"status": "processed", "subscription_id": subscription_id}
    
    # Razorpay event handlers
    async def _handle_razorpay_payment_authorized(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle Razorpay payment authorization."""
        payment_entity = data.get('payment', {}).get('entity', {})
        payment_id = payment_entity.get('id')
        
        return {"status": "processed", "payment_id": payment_id}
    
    async def _handle_razorpay_payment_captured(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle Razorpay payment capture."""
        from backend.models.payment import Transaction, TransactionStatus
        
        payment_entity = data.get('payment', {}).get('entity', {})
        payment_id = payment_entity.get('id')
        
        transaction = self.db.query(Transaction).filter(
            Transaction.razorpay_payment_id == payment_id
        ).first()
        
        if transaction:
            transaction.status = TransactionStatus.SUCCEEDED.value
            transaction.paid_at = datetime.utcnow()
            self.db.commit()
            return {"status": "processed", "transaction_id": transaction.id}
        
        return {"status": "not_found"}
    
    async def _handle_razorpay_payment_failed(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle Razorpay payment failure."""
        from backend.models.payment import Transaction, TransactionStatus
        
        payment_entity = data.get('payment', {}).get('entity', {})
        payment_id = payment_entity.get('id')
        error = payment_entity.get('error_description')
        
        transaction = self.db.query(Transaction).filter(
            Transaction.razorpay_payment_id == payment_id
        ).first()
        
        if transaction:
            transaction.status = TransactionStatus.FAILED.value
            transaction.failure_message = error
            self.db.commit()
            return {"status": "processed", "transaction_id": transaction.id}
        
        return {"status": "not_found"}
    
    async def _handle_razorpay_order_paid(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle Razorpay order payment."""
        order_entity = data.get('order', {}).get('entity', {})
        order_id = order_entity.get('id')
        
        return {"status": "processed", "order_id": order_id}
    
    async def _handle_razorpay_subscription_charged(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle Razorpay subscription charge."""
        subscription_entity = data.get('subscription', {}).get('entity', {})
        subscription_id = subscription_entity.get('id')
        
        from backend.models.subscription import UserSubscription, SubscriptionStatus
        
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.razorpay_subscription_id == subscription_id
        ).first()
        
        if subscription and subscription.status != SubscriptionStatus.ACTIVE:
            subscription.status = SubscriptionStatus.ACTIVE
            self.db.commit()
        
        return {"status": "processed", "subscription_id": subscription_id}
    
    async def _handle_razorpay_subscription_cancelled(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle Razorpay subscription cancellation."""
        subscription_entity = data.get('subscription', {}).get('entity', {})
        subscription_id = subscription_entity.get('id')
        
        from backend.models.subscription import UserSubscription, SubscriptionStatus
        
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.razorpay_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = datetime.utcnow()
            self.db.commit()
        
        return {"status": "processed", "subscription_id": subscription_id}
    
    async def _handle_razorpay_subscription_activated(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Handle Razorpay subscription activation."""
        subscription_entity = data.get('subscription', {}).get('entity', {})
        subscription_id = subscription_entity.get('id')
        
        from backend.models.subscription import UserSubscription, SubscriptionStatus
        
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.razorpay_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = SubscriptionStatus.ACTIVE
            self.db.commit()
        
        return {"status": "processed", "subscription_id": subscription_id}
