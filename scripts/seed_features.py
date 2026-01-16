"""
Seed script for initial features and entitlements
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config import settings
from backend.models.entitlement import Feature, PlanTemplate

# Create sync engine
sync_db_url = settings.database_url.replace("+aiosqlite", "")
sync_engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=sync_engine)


def seed_features():
    """Seed initial features."""
    db = SessionLocal()
    
    try:
        features = [
            # Core features
            {"name": "basic_quotes", "display_name": "Basic Quotes", "category": "quotes", 
             "description": "Create and manage basic quotes", "is_default": True, "min_plan_level": 0},
            {"name": "advanced_quotes", "display_name": "Advanced Quotes", "category": "quotes",
             "description": "Advanced quote features with versions", "min_plan_level": 1},
            {"name": "quote_templates", "display_name": "Quote Templates", "category": "quotes",
             "description": "Save and reuse quote templates", "min_plan_level": 2},
            
            # Party management
            {"name": "basic_parties", "display_name": "Basic Party Management", "category": "parties",
             "description": "Manage customers and suppliers", "is_default": True, "min_plan_level": 0},
            {"name": "party_analytics", "display_name": "Party Analytics", "category": "parties",
             "description": "Analytics and insights for parties", "min_plan_level": 2},
            
            # Invoicing
            {"name": "basic_invoices", "display_name": "Basic Invoicing", "category": "invoices",
             "description": "Create and send invoices", "min_plan_level": 1},
            {"name": "recurring_invoices", "display_name": "Recurring Invoices", "category": "invoices",
             "description": "Set up recurring invoices", "min_plan_level": 2},
            {"name": "invoice_customization", "display_name": "Invoice Customization", "category": "invoices",
             "description": "Customize invoice templates", "min_plan_level": 2},
            
            # Support
            {"name": "basic_support", "display_name": "Basic Support", "category": "support",
             "description": "Email support access", "is_default": True, "min_plan_level": 0},
            {"name": "priority_support", "display_name": "Priority Support", "category": "support",
             "description": "Priority ticket handling", "min_plan_level": 2},
            {"name": "dedicated_support", "display_name": "Dedicated Support", "category": "support",
             "description": "Dedicated support agent", "min_plan_level": 3},
            
            # Analytics
            {"name": "basic_reports", "display_name": "Basic Reports", "category": "analytics",
             "description": "Standard reports and metrics", "min_plan_level": 1},
            {"name": "custom_reports", "display_name": "Custom Reports", "category": "analytics",
             "description": "Create custom reports", "min_plan_level": 2},
            {"name": "api_access", "display_name": "API Access", "category": "integrations",
             "description": "Full API access for integrations", "min_plan_level": 2},
            
            # Admin features
            {"name": "multi_user", "display_name": "Multi-User Access", "category": "admin",
             "description": "Add multiple team members", "min_plan_level": 1},
            {"name": "role_management", "display_name": "Role Management", "category": "admin",
             "description": "Manage user roles and permissions", "min_plan_level": 2},
            {"name": "audit_logs", "display_name": "Audit Logs", "category": "admin",
             "description": "View detailed audit logs", "min_plan_level": 2},
        ]
        
        for feature_data in features:
            existing = db.query(Feature).filter(Feature.name == feature_data["name"]).first()
            if not existing:
                feature = Feature(**feature_data)
                db.add(feature)
                print(f"Added feature: {feature_data['name']}")
        
        db.commit()
        print(f"\n[SUCCESS] Seeded {len(features)} features")
        
    except Exception as e:
        print(f"[ERROR] Failed to seed features: {e}")
        db.rollback()
    finally:
        db.close()


def seed_plan_templates():
    """Seed subscription plan templates."""
    db = SessionLocal()
    
    try:
        plans = [
            {
                "name": "free",
                "display_name": "Free Plan",
                "description": "Basic features for small businesses",
                "level": 0,
                "monthly_price": 0,
                "annual_price": 0,
                "included_features": ["basic_quotes", "basic_parties", "basic_support"],
                "default_quotas": {
                    "basic_quotes": 10,  # 10 quotes per month
                    "basic_parties": 50,  # 50 parties
                },
            },
            {
                "name": "basic",
                "display_name": "Basic Plan",
                "description": "Core features for growing businesses",
                "level": 1,
                "monthly_price": 2900,  # $29/month
                "annual_price": 29000,  # $290/year (2 months free)
                "included_features": [
                    "basic_quotes", "advanced_quotes", "basic_parties",
                    "basic_invoices", "multi_user", "basic_reports", "basic_support"
                ],
                "default_quotas": {
                    "basic_quotes": None,  # Unlimited
                    "basic_parties": None,
                    "multi_user": 5,  # 5 team members
                },
            },
            {
                "name": "professional",
                "display_name": "Professional Plan",
                "description": "Advanced features for established businesses",
                "level": 2,
                "monthly_price": 7900,  # $79/month
                "annual_price": 79000,  # $790/year
                "included_features": [
                    "basic_quotes", "advanced_quotes", "quote_templates",
                    "basic_parties", "party_analytics",
                    "basic_invoices", "recurring_invoices", "invoice_customization",
                    "multi_user", "role_management", "audit_logs",
                    "basic_reports", "custom_reports", "api_access",
                    "priority_support",
                ],
                "default_quotas": {
                    "multi_user": 15,
                },
            },
            {
                "name": "enterprise",
                "display_name": "Enterprise Plan",
                "description": "Full features with dedicated support",
                "level": 3,
                "monthly_price": None,  # Custom pricing
                "annual_price": None,
                "included_features": "all",  # All features
                "default_quotas": {},  # All unlimited
            },
        ]
        
        for plan_data in plans:
            existing = db.query(PlanTemplate).filter(PlanTemplate.name == plan_data["name"]).first()
            if not existing:
                plan = PlanTemplate(**plan_data)
                db.add(plan)
                print(f"Added plan: {plan_data['name']}")
        
        db.commit()
        print(f"\n[SUCCESS] Seeded {len(plans)} plan templates")
        
    except Exception as e:
        print(f"[ERROR] Failed to seed plans: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding database with features and plan templates...\n")
    seed_features()
    seed_plan_templates()
    print("\nDatabase seeding complete!")
