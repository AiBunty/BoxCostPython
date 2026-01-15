# BoxCostPro Python - Architecture Documentation

## Overview

BoxCostPro Python is a complete rebuild of the BoxCostPro SaaS platform using modern Python technologies. This document outlines the architectural decisions, design patterns, and technical implementation details.

## Technology Stack

### Backend Framework
- **FastAPI**: High-performance async web framework
- **Python 3.11+**: Modern Python with type hints
- **Uvicorn**: ASGI server for production deployment

### Database Layer
- **SQLAlchemy 2.0**: Modern ORM with async support
- **PostgreSQL**: Primary relational database
- **Alembic**: Database migration management
- **Pydantic**: Data validation and settings management

### Authentication & Security
- **Clerk SDK**: User authentication and management
- **bcrypt**: Password hashing for admin accounts
- **PyOTP**: TOTP-based 2FA implementation
- **python-jose**: JWT token handling

### External Integrations
- **Razorpay**: Payment gateway for India
- **SMTP/Gmail/AWS SES**: Multi-provider email system
- **ReportLab/WeasyPrint**: PDF generation

## Architecture Patterns

### Multi-Tenancy

The application implements **row-level multi-tenancy** with tenant isolation:

```python
class TenantMixin:
    """Mixin for multi-tenant models."""
    tenant_id = Column(Integer, nullable=False, index=True)
```

All tenant-scoped queries must filter by `tenant_id`:

```python
@app.get("/api/quotes")
async def get_quotes(
    tenant_id: int = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    quotes = db.query(Quote).filter(Quote.tenant_id == tenant_id).all()
    return quotes
```

### Dependency Injection

FastAPI's dependency injection system is used throughout:

```python
# Database session
db: Session = Depends(get_db)

# Current user
current_user: User = Depends(get_current_user)

# Tenant context
tenant_id: int = Depends(get_current_tenant)

# Admin authentication
admin: Admin = Depends(require_admin)
```

### Service Layer Pattern

Business logic is separated into service classes:

```
backend/
├── routers/           # HTTP endpoints (thin layer)
├── services/          # Business logic (thick layer)
│   ├── auth_service.py
│   ├── quote_service.py
│   ├── invoice_service.py
│   └── entitlement_service.py
└── models/            # Database models (data layer)
```

Example:

```python
# Router (thin)
@router.post("/quotes")
async def create_quote(
    data: QuoteCreate,
    tenant_id: int = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    return quote_service.create_quote(db, tenant_id, data)

# Service (thick)
class QuoteService:
    def create_quote(self, db: Session, tenant_id: int, data: QuoteCreate):
        # Complex business logic here
        # - Validate data
        # - Calculate pricing
        # - Create version
        # - Send notifications
        pass
```

### Data Validation with Pydantic

All request/response models use Pydantic:

```python
class QuoteCreate(BaseModel):
    """Schema for creating a new quote."""
    party_id: int
    items: List[QuoteItemCreate]
    terms: Optional[str] = None
    
    class Config:
        from_attributes = True
```

### Error Handling

Centralized error handling with custom exceptions:

```python
class BoxCostException(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

@app.exception_handler(BoxCostException)
async def boxcost_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message}
    )
```

## Database Schema

### Core Tables

1. **users** - User accounts (Clerk-integrated)
2. **tenants** - Company/organization records
3. **tenant_users** - User-tenant mapping with roles
4. **admins** - Platform administrators (separate auth)
5. **company_profiles** - Business identity (LOCKED after invoice)

### Business Logic Tables

6. **party_profiles** - Customers/clients
7. **quotes** - Quote master records
8. **quote_versions** - Version history
9. **quote_items** - Line items per version
10. **invoices** - GST-compliant tax invoices
11. **paper_bf_prices** - Paper base prices by BF
12. **paper_shades** - Master paper shade list
13. **shade_premiums** - Shade-specific premiums
14. **business_defaults** - GST and tax settings

### Subscription Tables

15. **subscription_plans** - Plan definitions
16. **user_subscriptions** - Active subscriptions
17. **subscription_overrides** - Admin overrides
18. **entitlement_cache** - Denormalized entitlements

### Support Tables

19. **support_tickets** - Customer support tickets
20. **support_messages** - Ticket conversations
21. **support_agents** - Agent profiles

### Audit Tables

22. **admin_audit_logs** - Admin action logging
23. **auth_audit_logs** - Authentication events
24. **platform_events** - Immutable event log

## API Design

### RESTful Conventions

```
GET    /api/quotes              # List quotes
GET    /api/quotes/{id}         # Get quote by ID
POST   /api/quotes              # Create quote
PATCH  /api/quotes/{id}         # Update quote
DELETE /api/quotes/{id}         # Delete quote
```

### Filtering & Pagination

```python
@router.get("/quotes")
async def list_quotes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    offset = (page - 1) * limit
    query = db.query(Quote)
    
    if status:
        query = query.filter(Quote.status == status)
    
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }
```

### Response Structure

Consistent response format:

```json
{
  "data": { ... },
  "message": "Success",
  "timestamp": "2026-01-15T18:00:00Z"
}
```

Error response:

```json
{
  "error": "Validation failed",
  "detail": [ ... ],
  "timestamp": "2026-01-15T18:00:00Z"
}
```

## Security

### Authentication Flow

1. **User Auth (Clerk)**:
   - Frontend sends Clerk JWT
   - Backend validates with Clerk SDK
   - User context established

2. **Admin Auth (Custom)**:
   - Username/password + 2FA
   - Session token stored in database
   - IP whitelist check

### Authorization

Role-based access control (RBAC):

```python
@router.post("/admin/users/{id}/approve")
async def approve_user(
    id: int,
    admin: Admin = Depends(require_admin_role("super_admin")),
    db: Session = Depends(get_db)
):
    # Only super_admins can approve users
    pass
```

### Data Protection

- **Environment Variables**: Sensitive config via `.env`
- **Password Hashing**: bcrypt with salt rounds=12
- **Encryption**: AES-256 for stored credentials
- **SQL Injection**: SQLAlchemy parameterized queries
- **CORS**: Whitelist-based origin validation

## Migration from TypeScript

### Port Mapping

| TypeScript/Node.js | Python |
|-------------------|--------|
| Express | FastAPI |
| Drizzle ORM | SQLAlchemy |
| Zod | Pydantic |
| bcryptjs | bcrypt |
| node-postgres | psycopg2 |
| PDFKit | ReportLab |
| nodemailer | aiosmtplib |

### Feature Parity Checklist

- [ ] User authentication (Clerk)
- [ ] Admin authentication (custom)
- [ ] Multi-tenancy
- [ ] Box cost calculator
- [ ] Paper pricing system
- [ ] Quote management
- [ ] Invoice generation
- [ ] Customer management
- [ ] Subscription system
- [ ] Entitlement service
- [ ] Support tickets
- [ ] Email system
- [ ] PDF generation
- [ ] Razorpay integration
- [ ] Audit logging

## Performance Considerations

### Database Optimization

- **Indexes**: All foreign keys and lookup fields
- **Connection Pooling**: SQLAlchemy pool management
- **Query Optimization**: Eager loading with `joinedload()`
- **Caching**: Redis for entitlement cache

### Async Operations

Use async/await for I/O-bound operations:

```python
@router.post("/quotes/{id}/send")
async def send_quote(id: int):
    # Async email sending
    await email_service.send_quote_async(id)
    return {"status": "sent"}
```

### Background Jobs

Celery for long-running tasks:

```python
@celery_app.task
def generate_monthly_reports():
    # Run as background job
    pass
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

Required for production:
- `DATABASE_URL`
- `CLERK_SECRET_KEY`
- `SESSION_SECRET`
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`

### Health Checks

```
GET /health          # Basic health
GET /health/db       # Database health
GET /health/detailed # All components
```

## Testing Strategy

### Unit Tests

```python
def test_calculate_box_cost():
    result = calculator.calculate_cost(
        length=300, width=200, height=150,
        ply=3, quantity=1000
    )
    assert result.total_cost > 0
```

### Integration Tests

```python
def test_create_quote_endpoint(client, db_session):
    response = client.post("/api/quotes", json={...})
    assert response.status_code == 201
```

### Test Coverage

Target: 80%+ code coverage

## Future Enhancements

1. **GraphQL API**: Alternative to REST
2. **Async Workers**: Celery for background jobs
3. **Caching Layer**: Redis for performance
4. **Rate Limiting**: Protection against abuse
5. **API Versioning**: `/api/v2/` endpoints
6. **Websockets**: Real-time notifications
7. **Mobile API**: Optimized endpoints for mobile apps
8. **Monitoring**: Prometheus + Grafana

## Contributing

See main README.md for contribution guidelines.
