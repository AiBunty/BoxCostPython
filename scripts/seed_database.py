"""Database seeding script for initial data."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from decimal import Decimal
from datetime import datetime

from backend.database import Base
from backend.models.subscription import SubscriptionPlan
from backend.models.admin import Admin
from backend.services.auth_service import auth_service
from backend.config import settings


async def seed_subscription_plans(session: AsyncSession):
    """Create default subscription plans."""
    plans = [
        SubscriptionPlan(
            name="free",
            display_name="Free Plan",
            description="Get started with basic features",
            price_monthly=Decimal("0"),
            price_yearly=Decimal("0"),
            features={
                "api_access": False,
                "whatsapp_integration": False,
                "support_24_7": False,
                "custom_branding": False,
                "analytics_dashboard": False
            },
            quotas={
                "quotes_monthly": 10,
                "customers": 5,
                "team_size": 1,
                "email_accounts": 1,
                "storage_gb": 1
            },
            is_active=True,
            sort_order=1
        ),
        SubscriptionPlan(
            name="starter",
            display_name="Starter Plan",
            description="Perfect for small businesses",
            price_monthly=Decimal("999"),
            price_yearly=Decimal("9990"),
            features={
                "api_access": True,
                "whatsapp_integration": False,
                "support_24_7": False,
                "custom_branding": False,
                "analytics_dashboard": True
            },
            quotas={
                "quotes_monthly": 100,
                "customers": 50,
                "team_size": 3,
                "email_accounts": 2,
                "storage_gb": 10
            },
            is_active=True,
            sort_order=2
        ),
        SubscriptionPlan(
            name="professional",
            display_name="Professional Plan",
            description="For growing businesses",
            price_monthly=Decimal("2999"),
            price_yearly=Decimal("29990"),
            features={
                "api_access": True,
                "whatsapp_integration": True,
                "support_24_7": True,
                "custom_branding": True,
                "analytics_dashboard": True,
                "automation": True
            },
            quotas={
                "quotes_monthly": 1000,
                "customers": 500,
                "team_size": 10,
                "email_accounts": 5,
                "storage_gb": 50
            },
            is_active=True,
            sort_order=3
        ),
        SubscriptionPlan(
            name="enterprise",
            display_name="Enterprise Plan",
            description="Unlimited power for large organizations",
            price_monthly=Decimal("9999"),
            price_yearly=Decimal("99990"),
            features={
                "api_access": True,
                "whatsapp_integration": True,
                "support_24_7": True,
                "custom_branding": True,
                "analytics_dashboard": True,
                "automation": True,
                "data_export": True
            },
            quotas={
                "quotes_monthly": 999999,
                "customers": 999999,
                "team_size": 999,
                "email_accounts": 999,
                "storage_gb": 999
            },
            is_active=True,
            sort_order=4
        )
    ]
    
    for plan in plans:
        session.add(plan)
    
    await session.commit()
    print("✅ Seeded 4 subscription plans")


async def seed_admin_user(session: AsyncSession):
    """Create default admin user."""
    admin = Admin(
        username="admin",
        email="admin@boxcostpro.com",
        password_hash=auth_service.hash_password("Admin@123"),
        is_super_admin=True,
        is_active=True
    )
    session.add(admin)
    await session.commit()
    print("✅ Seeded admin user (username: admin, password: Admin@123)")


async def main():
    """Run database seeding."""
    # Use SQLite for development if PostgreSQL not available
    database_url = settings.database_url
    if "postgresql" in database_url and "localhost" in database_url:
        # Try SQLite instead for local development
        database_url = "sqlite+aiosqlite:///./boxcostpro.db"
        print(f"⚠️  Using SQLite for development: {database_url}")
    
    engine = create_async_engine(database_url, echo=True)
    
    # Create tables
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Seed data
        print("\nSeeding initial data...")
        await seed_subscription_plans(session)
        await seed_admin_user(session)
    
    await engine.dispose()
    print("\n🎉 Database seeding complete!")
    print("\nYou can now login to admin panel with:")
    print("  Username: admin")
    print("  Password: Admin@123")


if __name__ == "__main__":
    asyncio.run(main())
