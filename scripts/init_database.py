"""
Database initialization script - Creates all tables
Run this to initialize the database with all models
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from backend.database import Base
from backend.config import settings
from backend.models import (
    User, Tenant, TenantUser, CompanyProfile, Admin, AdminSession,
    PaperBFPrice, PaperShade, ShadePremium, PaperPricingRule, 
    BusinessDefault, FluteSettings, PartyProfile,
    Quote, QuoteVersion, QuoteItem, QuoteSendLog,
    SupportTicket, SupportMessage, SupportAgent, SLARule,
    AdminAuditLog, AuthAuditLog, AdminLoginAuditLog, EmailLog,
    Coupon, CouponUsage, TwoFactorAuth, TwoFactorBackupCode,
    Feature, UserEntitlement, TenantEntitlement, PlanTemplate, EntitlementLog,
    PaymentMethod, Transaction, UsageRecord, SubscriptionChange, Invoice,
)
# Import subscription models separately to ensure they're loaded
from backend.models.subscription import SubscriptionPlan, UserSubscription, SubscriptionOverride

# Create sync engine for table creation
sync_db_url = settings.database_url.replace("+aiosqlite", "")
sync_engine = create_engine(sync_db_url, echo=True)


def create_tables():
    """Create all database tables."""
    print("Creating all database tables...")
    
    try:
        Base.metadata.create_all(bind=sync_engine)
        print("[SUCCESS] All tables created successfully!")
        
        # List created tables
        print("\nCreated tables:")
        for table in Base.metadata.sorted_tables:
            print(f"  - {table.name}")
            
    except Exception as e:
        print(f"[ERROR] Error creating tables: {e}")
        raise


def drop_tables():
    """Drop all database tables (DANGEROUS!)."""
    print("[WARNING] This will drop all tables!")
    confirm = input("Type 'yes' to confirm: ")
    
    if confirm.lower() == 'yes':
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=sync_engine)
        print("[SUCCESS] All tables dropped!")
    else:
        print("[CANCELLED]")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Database initialization')
    parser.add_argument('--drop', action='store_true', help='Drop all tables')
    args = parser.parse_args()
    
    if args.drop:
        drop_tables()
    else:
        create_tables()
