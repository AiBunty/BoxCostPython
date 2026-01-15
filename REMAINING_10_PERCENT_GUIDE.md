# Remaining 10% - Implementation Guide

## Quick Status
**Completed:** 90% feature parity ✅  
**Remaining:** Database migrations, integrations, testing

---

## Priority 1: Database Setup (Required to run)

### Generate Initial Migration
```bash
cd C:\Users\ventu\BoxCostPro\BoxCostPython
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Generate migration from models
alembic revision --autogenerate -m "Initial schema with all 28 models"

# Review the migration file in migrations/versions/
# Make sure all 28 tables are included:
# - users, tenants, admins, admin_sessions, company_profiles
# - bf_prices, shade_prices, premium_prices, business_default_prices
# - parties
# - quotes, quote_items, quote_versions, quote_approvals
# - subscription_plans, user_subscriptions, subscription_overrides
# - entitlement_cache, user_feature_usage, platform_events, subscription_coupons
# - invoices, subscription_invoices, payment_transactions
# - support_tickets, support_messages, support_agents, sla_rules
# - admin_audit_logs, auth_audit_logs, admin_login_audit_logs, email_logs

# Apply migration
alembic upgrade head
```

### Seed Initial Data
Create `scripts/seed_data.py`:
```python
"""Seed initial data for development."""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import async_session, Base, engine
from backend.models.subscription import SubscriptionPlan
from backend.models.admin import Admin
from backend.services.auth_service import auth_service
from decimal import Decimal

async def seed_subscription_plans():
    """Create default subscription plans."""
    async with async_session() as session:
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
                    "custom_branding": False
                },
                quotas={
                    "quotes_monthly": 10,
                    "customers": 5,
                    "team_size": 1
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
                    "custom_branding": False
                },
                quotas={
                    "quotes_monthly": 100,
                    "customers": 50,
                    "team_size": 3
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
                    "custom_branding": True
                },
                quotas={
                    "quotes_monthly": 1000,
                    "customers": 500,
                    "team_size": 10
                },
                is_active=True,
                sort_order=3
            )
        ]
        
        for plan in plans:
            session.add(plan)
        await session.commit()
        print("✅ Seeded subscription plans")

async def seed_admin_user():
    """Create default admin user."""
    async with async_session() as session:
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
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed data
    await seed_subscription_plans()
    await seed_admin_user()
    
    print("\n✅ Database seeding complete!")

if __name__ == "__main__":
    asyncio.run(main())
```

Run seeding:
```bash
python scripts/seed_data.py
```

---

## Priority 2: Authentication Integration

### Clerk User Authentication
Update `backend/middleware/auth.py`:

```python
from clerk_backend_api import Clerk
from backend.config import settings

clerk_client = Clerk(bearer_auth=settings.clerk_secret_key)

async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Validate Clerk token and return user."""
    try:
        # Extract token
        token = authorization.replace("Bearer ", "")
        
        # Verify with Clerk
        session = clerk_client.sessions.verify_session(token)
        clerk_user_id = session.user_id
        
        # Get or create user in our database
        result = await db.execute(
            select(User).where(User.clerk_user_id == clerk_user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User deactivated")
        
        return user
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication")
```

---

## Priority 3: Payment Integration

### Razorpay Webhook Handler
Create `backend/routers/webhooks.py`:

```python
"""Webhook handlers for external integrations."""
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import razorpay
import hmac
import hashlib

from backend.config import settings
from backend.database import get_db
from backend.models.invoice import PaymentTransaction, SubscriptionInvoice
from backend.models.subscription import UserSubscription

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

razorpay_client = razorpay.Client(
    auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
)

@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Razorpay payment webhooks."""
    # Get webhook signature
    signature = request.headers.get("X-Razorpay-Signature")
    body = await request.body()
    
    # Verify signature
    expected_signature = hmac.new(
        settings.razorpay_webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if signature != expected_signature:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Parse event
    event = await request.json()
    event_type = event.get("event")
    
    if event_type == "payment.captured":
        # Handle successful payment
        payment_data = event.get("payload", {}).get("payment", {}).get("entity", {})
        
        # Update transaction
        # ... implementation
        pass
    
    return {"status": "ok"}
```

---

## Priority 4: PDF Generation

### Invoice PDF Service
Create `backend/services/pdf.py`:

```python
"""PDF generation service for invoices and quotes."""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from io import BytesIO
from decimal import Decimal

class InvoicePDFGenerator:
    """Generate GST-compliant invoice PDFs."""
    
    def generate_invoice_pdf(self, invoice_data: dict) -> bytes:
        """Generate invoice PDF and return bytes."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Header
        header = Paragraph(
            f"<b>INVOICE</b><br/>{invoice_data['invoice_number']}",
            styles['Title']
        )
        elements.append(header)
        
        # Seller/Buyer details table
        details_data = [
            ['Seller:', invoice_data['seller_name']],
            ['Address:', invoice_data['seller_address']],
            ['GSTIN:', invoice_data['seller_gst']],
            ['', ''],
            ['Buyer:', invoice_data['buyer_name']],
            ['Address:', invoice_data['buyer_address']],
            ['GSTIN:', invoice_data['buyer_gst']]
        ]
        
        details_table = Table(details_data)
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(details_table)
        
        # Line items (if available)
        # ... implementation
        
        # GST breakdown table
        gst_data = [
            ['Subtotal:', f"₹{invoice_data['subtotal']}"],
            ['CGST:', f"₹{invoice_data['cgst']}"],
            ['SGST:', f"₹{invoice_data['sgst']}"],
            ['IGST:', f"₹{invoice_data['igst']}"],
            ['Total GST:', f"₹{invoice_data['total_gst']}"],
            ['<b>Total Amount:</b>', f"<b>₹{invoice_data['total_amount']}</b>"]
        ]
        
        gst_table = Table(gst_data)
        gst_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        elements.append(gst_table)
        
        # Build PDF
        doc.build(elements)
        
        # Return bytes
        buffer.seek(0)
        return buffer.read()

pdf_generator = InvoicePDFGenerator()
```

Add endpoint in `backend/routers/invoices.py`:
```python
@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_context)
):
    """Download invoice as PDF."""
    from fastapi.responses import StreamingResponse
    from backend.services.pdf import pdf_generator
    
    # Get invoice
    result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id
            )
        )
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Generate PDF
    invoice_dict = {
        "invoice_number": invoice.invoice_number,
        "seller_name": invoice.seller_name,
        # ... map all fields
    }
    
    pdf_bytes = pdf_generator.generate_invoice_pdf(invoice_dict)
    
    # Return as downloadable file
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice_{invoice.invoice_number}.pdf"
        }
    )
```

---

## Priority 5: Email Service

### Multi-Provider Email Service
Create `backend/services/email.py`:

```python
"""Email service with multi-provider support."""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from backend.config import settings
from backend.models.audit import EmailLog
from sqlalchemy.ext.asyncio import AsyncSession

class EmailService:
    """Send emails via SMTP."""
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str = None,
        db: AsyncSession = None
    ) -> bool:
        """Send an email."""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = settings.smtp_from_email
            message["To"] = to_email
            message["Subject"] = subject
            
            # Add text and HTML parts
            if body_text:
                part1 = MIMEText(body_text, "plain")
                message.attach(part1)
            
            part2 = MIMEText(body_html, "html")
            message.attach(part2)
            
            # Send via SMTP
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                use_tls=True
            )
            
            # Log success
            if db:
                log = EmailLog(
                    to_email=to_email,
                    subject=subject,
                    status="sent",
                    provider="smtp"
                )
                db.add(log)
                await db.commit()
            
            return True
            
        except Exception as e:
            # Log failure
            if db:
                log = EmailLog(
                    to_email=to_email,
                    subject=subject,
                    status="failed",
                    provider="smtp",
                    error_message=str(e)
                )
                db.add(log)
                await db.commit()
            
            return False

email_service = EmailService()
```

### Email Templates
Create `backend/templates/email/`:
- `invoice_generated.html`
- `subscription_renewed.html`
- `support_ticket_created.html`

---

## Testing Guide

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_calculator.py -v

# Run specific test
pytest tests/test_calculator.py::test_basic_calculation -v
```

### Test Structure
```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from backend.database import Base

@pytest.fixture
async def db_session():
    """Create test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        yield session
    
    await engine.dispose()
```

---

## Deployment Checklist

### 1. Environment Setup
```bash
# Production .env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/boxcostpro
CLERK_SECRET_KEY=sk_live_...
RAZORPAY_KEY_ID=rzp_live_...
RAZORPAY_KEY_SECRET=...
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=...
SMTP_PASSWORD=...
```

### 2. Install Production Server
```bash
pip install gunicorn
```

### 3. Run with Gunicorn
```bash
gunicorn backend.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -
```

### 4. Nginx Configuration
```nginx
server {
    listen 80;
    server_name api.boxcostpro.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Performance Optimization

### Database Indexing
Add to migration:
```python
# Add indexes for frequently queried fields
op.create_index('ix_quotes_tenant_created', 'quotes', ['tenant_id', 'created_at'])
op.create_index('ix_invoices_tenant_status', 'invoices', ['tenant_id', 'status'])
op.create_index('ix_users_clerk_user', 'users', ['clerk_user_id'])
```

### Caching Layer
```python
# Add Redis caching for entitlements
from redis import asyncio as aioredis

redis_client = aioredis.from_url(settings.redis_url)

async def get_cached_entitlement(user_id: int):
    """Get entitlement from cache."""
    key = f"entitlement:{user_id}"
    cached = await redis_client.get(key)
    if cached:
        return json.loads(cached)
    return None

async def cache_entitlement(user_id: int, data: dict):
    """Cache entitlement for 5 minutes."""
    key = f"entitlement:{user_id}"
    await redis_client.setex(key, 300, json.dumps(data))
```

---

## Monitoring Setup

### Sentry Error Tracking
```python
# backend/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    integrations=[FastApiIntegration()],
    environment=settings.environment
)
```

### Logging to File
```python
# backend/config.py
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "logs/app.log",
    maxBytes=10485760,  # 10MB
    backupCount=10
)
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))
logging.getLogger().addHandler(handler)
```

---

## Quick Commands Reference

```bash
# Development
python start.py

# Run migrations
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "description"

# Testing
pytest -v
pytest --cov

# Code quality
black backend/ shared/
pylint backend/
mypy backend/

# Production
gunicorn backend.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

---

**That's the remaining 10%! Focus on migrations first, then authentication, then the rest in order of priority.**
