"""
Usage tracking and metered billing automation service.
Handles automatic usage recording, aggregation, and billing calculations.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal
import logging
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from backend.models.payment import UsageRecord
from backend.models.subscription import UserSubscription, SubscriptionPlan, SubscriptionStatus
from backend.models.user import User

logger = logging.getLogger(__name__)


class UsageTrackingService:
    """Service for tracking and calculating usage-based billing."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_usage(
        self,
        user_id: int,
        tenant_id: int,
        metric_name: str,
        quantity: Decimal,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UsageRecord:
        """
        Record a usage event for metered billing.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            metric_name: Name of the metric (e.g., 'api_calls', 'storage_gb', 'quotes_generated')
            quantity: Amount of usage
            timestamp: Time of usage (defaults to now)
            metadata: Additional usage metadata
            
        Returns:
            Created UsageRecord
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        usage_record = UsageRecord(
            user_id=user_id,
            tenant_id=tenant_id,
            metric_name=metric_name,
            quantity=quantity,
            recorded_at=timestamp,
            metadata=metadata or {}
        )
        
        self.db.add(usage_record)
        self.db.commit()
        self.db.refresh(usage_record)
        
        logger.info(f"Recorded usage: user={user_id}, metric={metric_name}, quantity={quantity}")
        return usage_record
    
    def get_usage_summary(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        metric_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated usage summary for a user within a date range.
        
        Args:
            user_id: User ID
            start_date: Start of date range
            end_date: End of date range
            metric_name: Optional specific metric to filter by
            
        Returns:
            Dictionary with usage summary by metric
        """
        query = self.db.query(
            UsageRecord.metric_name,
            func.sum(UsageRecord.quantity).label('total_quantity'),
            func.count(UsageRecord.id).label('event_count'),
            func.min(UsageRecord.recorded_at).label('first_usage'),
            func.max(UsageRecord.recorded_at).label('last_usage')
        ).filter(
            and_(
                UsageRecord.user_id == user_id,
                UsageRecord.recorded_at >= start_date,
                UsageRecord.recorded_at <= end_date
            )
        )
        
        if metric_name:
            query = query.filter(UsageRecord.metric_name == metric_name)
        
        results = query.group_by(UsageRecord.metric_name).all()
        
        summary = {
            'user_id': user_id,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'metrics': []
        }
        
        for row in results:
            summary['metrics'].append({
                'metric_name': row.metric_name,
                'total_quantity': float(row.total_quantity),
                'event_count': row.event_count,
                'first_usage': row.first_usage.isoformat(),
                'last_usage': row.last_usage.isoformat()
            })
        
        return summary
    
    def calculate_overage_charges(
        self,
        subscription: UserSubscription,
        usage_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate overage charges based on usage and subscription limits.
        
        Args:
            subscription: User's subscription
            usage_summary: Usage summary from get_usage_summary()
            
        Returns:
            Dictionary with overage calculations
        """
        plan = subscription.plan
        overages = {
            'subscription_id': subscription.id,
            'billing_period': usage_summary['period'],
            'charges': [],
            'total_overage': Decimal('0.00')
        }
        
        # Define usage limits and overage rates per plan
        # This would typically come from a database table or plan configuration
        usage_limits = self._get_usage_limits(plan.name)
        
        for metric in usage_summary['metrics']:
            metric_name = metric['metric_name']
            total_quantity = Decimal(str(metric['total_quantity']))
            
            if metric_name in usage_limits:
                limit_config = usage_limits[metric_name]
                included_quantity = Decimal(str(limit_config.get('included', 0)))
                overage_rate = Decimal(str(limit_config.get('overage_rate', 0)))
                
                if total_quantity > included_quantity:
                    overage_quantity = total_quantity - included_quantity
                    overage_amount = overage_quantity * overage_rate
                    
                    overages['charges'].append({
                        'metric_name': metric_name,
                        'included_quantity': float(included_quantity),
                        'used_quantity': float(total_quantity),
                        'overage_quantity': float(overage_quantity),
                        'overage_rate': float(overage_rate),
                        'overage_amount': float(overage_amount)
                    })
                    
                    overages['total_overage'] += overage_amount
        
        overages['total_overage'] = float(overages['total_overage'])
        return overages
    
    def _get_usage_limits(self, plan_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Get usage limits and overage rates for a plan.
        
        This is a simplified version - in production, this would be stored in database.
        """
        plans_config = {
            'FREE': {
                'quotes_generated': {'included': 10, 'overage_rate': 0.50},
                'invoices_generated': {'included': 5, 'overage_rate': 0.25},
                'api_calls': {'included': 1000, 'overage_rate': 0.001},
                'storage_gb': {'included': 1, 'overage_rate': 0.10}
            },
            'STARTER': {
                'quotes_generated': {'included': 100, 'overage_rate': 0.30},
                'invoices_generated': {'included': 50, 'overage_rate': 0.15},
                'api_calls': {'included': 10000, 'overage_rate': 0.0005},
                'storage_gb': {'included': 10, 'overage_rate': 0.08}
            },
            'PROFESSIONAL': {
                'quotes_generated': {'included': 500, 'overage_rate': 0.20},
                'invoices_generated': {'included': 250, 'overage_rate': 0.10},
                'api_calls': {'included': 50000, 'overage_rate': 0.0003},
                'storage_gb': {'included': 50, 'overage_rate': 0.05}
            },
            'ENTERPRISE': {
                'quotes_generated': {'included': 99999, 'overage_rate': 0.10},
                'invoices_generated': {'included': 99999, 'overage_rate': 0.05},
                'api_calls': {'included': 999999, 'overage_rate': 0.0001},
                'storage_gb': {'included': 500, 'overage_rate': 0.03}
            }
        }
        
        return plans_config.get(plan_name, {})
    
    def get_current_billing_period(
        self,
        subscription: UserSubscription
    ) -> tuple[datetime, datetime]:
        """
        Calculate the current billing period for a subscription.
        
        Args:
            subscription: User's subscription
            
        Returns:
            Tuple of (start_date, end_date) for current billing period
        """
        now = datetime.utcnow()
        
        # For monthly subscriptions
        if subscription.billing_cycle == 'monthly':
            # Get the day of month when subscription started
            billing_day = subscription.start_date.day
            
            # Calculate current billing period
            if now.day >= billing_day:
                # Current month billing period
                start_date = datetime(now.year, now.month, billing_day)
                
                # Calculate next month
                if now.month == 12:
                    next_month = datetime(now.year + 1, 1, billing_day)
                else:
                    next_month = datetime(now.year, now.month + 1, billing_day)
                
                end_date = next_month - timedelta(seconds=1)
            else:
                # Previous month billing period
                if now.month == 1:
                    start_date = datetime(now.year - 1, 12, billing_day)
                else:
                    start_date = datetime(now.year, now.month - 1, billing_day)
                
                end_date = datetime(now.year, now.month, billing_day) - timedelta(seconds=1)
        
        # For annual subscriptions
        elif subscription.billing_cycle == 'yearly':
            # Annual billing starting from subscription start date
            years_since_start = (now.year - subscription.start_date.year)
            
            start_date = datetime(
                subscription.start_date.year + years_since_start,
                subscription.start_date.month,
                subscription.start_date.day
            )
            
            end_date = datetime(
                subscription.start_date.year + years_since_start + 1,
                subscription.start_date.month,
                subscription.start_date.day
            ) - timedelta(seconds=1)
        
        else:
            # Default to current month
            start_date = datetime(now.year, now.month, 1)
            if now.month == 12:
                end_date = datetime(now.year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(now.year, now.month + 1, 1) - timedelta(seconds=1)
        
        return start_date, end_date
    
    def check_usage_alerts(
        self,
        subscription: UserSubscription
    ) -> List[Dict[str, Any]]:
        """
        Check if usage has exceeded alert thresholds.
        
        Args:
            subscription: User's subscription
            
        Returns:
            List of alerts for usage that exceeds thresholds
        """
        start_date, end_date = self.get_current_billing_period(subscription)
        usage_summary = self.get_usage_summary(
            subscription.user_id,
            start_date,
            end_date
        )
        
        alerts = []
        usage_limits = self._get_usage_limits(subscription.plan.name)
        
        # Alert thresholds: 80%, 90%, 100%, 110%
        thresholds = [0.8, 0.9, 1.0, 1.1]
        
        for metric in usage_summary['metrics']:
            metric_name = metric['metric_name']
            total_quantity = Decimal(str(metric['total_quantity']))
            
            if metric_name in usage_limits:
                limit_config = usage_limits[metric_name]
                included_quantity = Decimal(str(limit_config.get('included', 0)))
                
                if included_quantity > 0:
                    usage_percent = float(total_quantity / included_quantity)
                    
                    for threshold in thresholds:
                        if usage_percent >= threshold:
                            alert_level = 'warning' if threshold < 1.0 else 'critical'
                            
                            alerts.append({
                                'subscription_id': subscription.id,
                                'user_id': subscription.user_id,
                                'metric_name': metric_name,
                                'threshold_percent': int(threshold * 100),
                                'usage_percent': int(usage_percent * 100),
                                'used_quantity': float(total_quantity),
                                'included_quantity': float(included_quantity),
                                'alert_level': alert_level,
                                'message': f"{metric_name} usage at {int(usage_percent * 100)}% of limit"
                            })
                            break  # Only report highest threshold crossed
        
        return alerts
    
    def aggregate_usage_for_billing(
        self,
        subscription_id: int
    ) -> Dict[str, Any]:
        """
        Aggregate all usage data for billing purposes.
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            Complete billing data including base price and usage charges
        """
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.id == subscription_id
        ).first()
        
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        start_date, end_date = self.get_current_billing_period(subscription)
        usage_summary = self.get_usage_summary(
            subscription.user_id,
            start_date,
            end_date
        )
        
        overage_charges = self.calculate_overage_charges(subscription, usage_summary)
        
        base_price = subscription.price
        total_amount = Decimal(str(base_price)) + Decimal(str(overage_charges['total_overage']))
        
        return {
            'subscription_id': subscription_id,
            'user_id': subscription.user_id,
            'tenant_id': subscription.tenant_id,
            'billing_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'base_price': float(base_price),
            'usage_charges': overage_charges['charges'],
            'total_usage_charges': overage_charges['total_overage'],
            'total_amount': float(total_amount),
            'currency': subscription.currency,
            'usage_summary': usage_summary
        }


class UsageMetrics:
    """Constants for standard usage metric names."""
    
    QUOTES_GENERATED = 'quotes_generated'
    INVOICES_GENERATED = 'invoices_generated'
    API_CALLS = 'api_calls'
    STORAGE_GB = 'storage_gb'
    USERS_ACTIVE = 'users_active'
    SUPPORT_TICKETS = 'support_tickets'
    EMAIL_SENT = 'email_sent'
    PDF_GENERATED = 'pdf_generated'
    WEBHOOK_CALLS = 'webhook_calls'
    EXPORT_OPERATIONS = 'export_operations'


def track_quote_generation(db: Session, user_id: int, tenant_id: int, quote_id: int):
    """Helper to track quote generation usage."""
    service = UsageTrackingService(db)
    service.record_usage(
        user_id=user_id,
        tenant_id=tenant_id,
        metric_name=UsageMetrics.QUOTES_GENERATED,
        quantity=Decimal('1.0'),
        metadata={'quote_id': quote_id}
    )


def track_invoice_generation(db: Session, user_id: int, tenant_id: int, invoice_id: int):
    """Helper to track invoice generation usage."""
    service = UsageTrackingService(db)
    service.record_usage(
        user_id=user_id,
        tenant_id=tenant_id,
        metric_name=UsageMetrics.INVOICES_GENERATED,
        quantity=Decimal('1.0'),
        metadata={'invoice_id': invoice_id}
    )


def track_api_call(db: Session, user_id: int, tenant_id: int, endpoint: str):
    """Helper to track API call usage."""
    service = UsageTrackingService(db)
    service.record_usage(
        user_id=user_id,
        tenant_id=tenant_id,
        metric_name=UsageMetrics.API_CALLS,
        quantity=Decimal('1.0'),
        metadata={'endpoint': endpoint}
    )


def track_storage_usage(db: Session, user_id: int, tenant_id: int, size_gb: float):
    """Helper to track storage usage."""
    service = UsageTrackingService(db)
    service.record_usage(
        user_id=user_id,
        tenant_id=tenant_id,
        metric_name=UsageMetrics.STORAGE_GB,
        quantity=Decimal(str(size_gb)),
        metadata={'type': 'storage_update'}
    )


def track_email_sent(db: Session, user_id: int, tenant_id: int, email_type: str):
    """Helper to track email sending usage."""
    service = UsageTrackingService(db)
    service.record_usage(
        user_id=user_id,
        tenant_id=tenant_id,
        metric_name=UsageMetrics.EMAIL_SENT,
        quantity=Decimal('1.0'),
        metadata={'email_type': email_type}
    )


def track_pdf_generation(db: Session, user_id: int, tenant_id: int, document_type: str):
    """Helper to track PDF generation usage."""
    service = UsageTrackingService(db)
    service.record_usage(
        user_id=user_id,
        tenant_id=tenant_id,
        metric_name=UsageMetrics.PDF_GENERATED,
        quantity=Decimal('1.0'),
        metadata={'document_type': document_type}
    )
