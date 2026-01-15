# BoxCostPro - Python Backend

A comprehensive SaaS platform for the corrugated box manufacturing industry in India, rebuilt in Python with FastAPI.

## Overview

BoxCostPro helps corrugated box manufacturers:
- Calculate accurate costs for RSC boxes and sheets
- Generate professional quotations
- Manage customer relationships
- Track business analytics
- Send quotes via WhatsApp and Email
- Generate GST-compliant invoices
- Manage master data and pricing

## Tech Stack

- **Backend Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic
- **Authentication**: Clerk SDK for Python + Custom Admin Auth
- **Validation**: Pydantic v2
- **Payment Integration**: Razorpay
- **Email**: Multi-provider (Gmail, SMTP, AWS SES)
- **PDF Generation**: ReportLab / WeasyPrint

## Project Structure

```
BoxCostPython/
├── backend/                 # FastAPI application
│   ├── models/             # SQLAlchemy database models
│   ├── routers/            # API endpoint routers
│   ├── services/           # Business logic services
│   ├── middleware/         # FastAPI middleware
│   ├── utils/              # Utility functions
│   ├── main.py             # Application entry point
│   ├── config.py           # Configuration management
│   └── database.py         # Database connection setup
├── shared/                  # Shared schemas and types
├── migrations/              # Alembic database migrations
├── scripts/                 # Utility scripts
├── tests/                   # Test suite
├── docs/                    # Documentation
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── README.md               # This file
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Git

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AiBunty/BoxCostPython.git
   cd BoxCostPython
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Start the development server**:
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000`

## Environment Variables

Required environment variables (see `.env.example`):

```env
# Application
APP_URL=http://localhost:8000
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/boxcostpro

# Clerk Authentication
CLERK_SECRET_KEY=sk_test_your_key_here

# Session
SESSION_SECRET=your-secure-random-secret

# Email (Optional)
FROM_EMAIL=noreply@boxcostpro.com
FROM_NAME=BoxCostPro

# Razorpay (Optional)
RAZORPAY_KEY_ID=your_key_id
RAZORPAY_KEY_SECRET=your_key_secret
```

## API Documentation

Once the server is running, access:
- **Interactive API docs (Swagger)**: http://localhost:8000/docs
- **Alternative docs (ReDoc)**: http://localhost:8000/redoc

## Development

### Running Tests

```bash
pytest
```

### Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback last migration:
```bash
alembic downgrade -1
```

### Code Quality

Format code:
```bash
black backend/ shared/
```

Lint code:
```bash
pylint backend/ shared/
```

Type checking:
```bash
mypy backend/
```

## Features

### Core Features
- ✅ Multi-tenant architecture with complete data isolation
- ✅ User authentication via Clerk
- ✅ Admin panel with separate authentication and RBAC
- ✅ Box cost calculator with advanced formulas (ECT, BCT, GSM)
- ✅ Paper pricing system with BF, GSM, and shade premiums
- ✅ Quote management with versioning
- ✅ GST-compliant invoice generation
- ✅ Customer (party) management
- ✅ Master data management
- ✅ Subscription and entitlement system
- ✅ Support ticket system with SLA tracking
- ✅ Multi-provider email system
- ✅ Comprehensive audit logging

### Planned Features
- 🔄 WhatsApp integration for quote sending
- 🔄 AI-powered support assistant
- 🔄 Advanced analytics dashboard
- 🔄 Mobile app API support

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Proprietary - All rights reserved

## Support

For support, email support@boxcostpro.com or create an issue in the repository.

## Acknowledgments

This is a Python rebuild of the original TypeScript/Node.js BoxCostPro application, maintaining feature parity while leveraging Python's ecosystem for improved performance and maintainability.
