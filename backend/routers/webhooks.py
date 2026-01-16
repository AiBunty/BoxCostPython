"""
Webhook endpoints for payment gateway integrations.
Handles Stripe and Razorpay webhook events.
"""
from fastapi import APIRouter, Request, HTTPException, status, Header
from typing import Optional
import logging

from backend.database import get_db
from backend.services.webhook_service import (
    StripeWebhookValidator,
    RazorpayWebhookValidator,
    WebhookProcessor,
    WebhookVerificationError
)
from backend.config import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature")
):
    """
    Handle Stripe webhook events.
    
    Verifies signature and processes payment/subscription events.
    """
    # Get raw body
    body = await request.body()
    
    if not stripe_signature:
        logger.error("Stripe webhook missing signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header"
        )
    
    # Get webhook secret from settings
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured"
        )
    
    try:
        # Verify signature and parse event
        event = StripeWebhookValidator.verify_signature(
            payload=body,
            signature_header=stripe_signature,
            webhook_secret=webhook_secret
        )
        
        logger.info(f"Verified Stripe webhook: {event.get('type')} - {event.get('id')}")
        
        # Process event
        db = next(get_db())
        processor = WebhookProcessor(db)
        
        try:
            result = await processor.process_stripe_event(event)
            logger.info(f"Processed Stripe event: {result}")
            
            return {
                "received": True,
                "event_id": event.get('id'),
                "event_type": event.get('type'),
                "processing_result": result
            }
        except Exception as e:
            logger.error(f"Error processing Stripe event: {e}", exc_info=True)
            db.rollback()
            
            # Still return 200 to acknowledge receipt
            return {
                "received": True,
                "event_id": event.get('id'),
                "error": str(e)
            }
        finally:
            db.close()
            
    except WebhookVerificationError as e:
        logger.error(f"Stripe webhook verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook verification failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in Stripe webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature")
):
    """
    Handle Razorpay webhook events.
    
    Verifies signature and processes payment/subscription events.
    """
    # Get raw body
    body = await request.body()
    
    if not x_razorpay_signature:
        logger.error("Razorpay webhook missing signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header"
        )
    
    # Get webhook secret from settings
    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', None)
    if not webhook_secret:
        logger.error("RAZORPAY_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured"
        )
    
    try:
        # Verify signature and parse event
        event = RazorpayWebhookValidator.verify_signature(
            payload=body,
            signature_header=x_razorpay_signature,
            webhook_secret=webhook_secret
        )
        
        logger.info(f"Verified Razorpay webhook: {event.get('event')} - {event.get('account_id')}")
        
        # Process event
        db = next(get_db())
        processor = WebhookProcessor(db)
        
        try:
            result = await processor.process_razorpay_event(event)
            logger.info(f"Processed Razorpay event: {result}")
            
            return {
                "received": True,
                "event": event.get('event'),
                "account_id": event.get('account_id'),
                "processing_result": result
            }
        except Exception as e:
            logger.error(f"Error processing Razorpay event: {e}", exc_info=True)
            db.rollback()
            
            # Still return 200 to acknowledge receipt
            return {
                "received": True,
                "event": event.get('event'),
                "error": str(e)
            }
        finally:
            db.close()
            
    except WebhookVerificationError as e:
        logger.error(f"Razorpay webhook verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook verification failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in Razorpay webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoints."""
    return {
        "status": "healthy",
        "stripe_webhook": "/webhooks/stripe",
        "razorpay_webhook": "/webhooks/razorpay"
    }
