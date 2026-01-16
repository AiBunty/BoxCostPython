# 🌐 How to Access BoxCostPro - Complete Guide

## ✅ Current Status
- **Backend**: Running on `http://localhost:8000` ✓
- **Environment**: Development
- **API Endpoints**: 103 active
- **Database**: Connected (46 tables)

---

## 🚀 Access Points

### 1. **API Documentation (Interactive)**
**URL**: http://localhost:8000/docs

**What you can do**:
- 📖 Browse all 103 API endpoints
- 🧪 Test endpoints directly in browser
- 📋 View request/response schemas
- 🔍 See parameter descriptions
- 💬 Read endpoint documentation

**How to access**:
1. Open your browser
2. Go to: `http://localhost:8000/docs`
3. You'll see the Swagger UI interface

---

### 2. **Alternative API Docs (ReDoc)**
**URL**: http://localhost:8000/redoc

**What you can do**:
- 📚 Read API documentation in a different format
- 🔗 Browse organized by feature
- 📖 Detailed schema documentation

**How to access**:
1. Open your browser
2. Go to: `http://localhost:8000/redoc`

---

### 3. **Health Check**
**URL**: http://localhost:8000/health

**What you can do**:
- ✓ Verify backend is running
- 📊 See service status
- 🕐 Check server timestamp

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-16T07:45:15.268128",
  "service": "BoxCostPro Python Backend"
}
```

---

### 4. **OpenAPI Specification (JSON)**
**URL**: http://localhost:8000/openapi.json

**What you can do**:
- 📋 Download complete API specification
- 🔧 Use with tools (Postman, Insomnia, etc.)
- 🤖 Integrate with code generation tools

---

## 🎯 Frontend/Website Access

### TypeScript Frontend (If Running)
**Expected URL**: `http://localhost:3000` or `http://localhost:5173`

**Status**: Check if frontend is running on these ports

---

## 📚 Using the API Documentation

### Step 1: Open Swagger UI
```
http://localhost:8000/docs
```

### Step 2: Browse Features
Click on any feature category to expand:
- ✅ Support Tickets
- ✅ Audit Logging  
- ✅ Coupon Management
- ✅ Two-Factor Auth
- ✅ Entitlements
- ✅ Subscriptions
- ✅ Payments
- ✅ Admin Functions

### Step 3: Test an Endpoint
**Example: Health Check (No Auth Required)**

1. Click on `Health` section
2. Find `GET /health`
3. Click "Try it out"
4. Click "Execute"
5. See the response below

**Example: Support Tickets (Auth Required)**

1. Click on `Support` section
2. Find `GET /api/support/tickets`
3. Click "Try it out"
4. You'll see it requires authentication (Bearer token)
5. To test, you need to add an Authorization header

---

## 🔐 Testing Protected Endpoints

### Option 1: With Postman/Insomnia
1. Download Postman or Insomnia
2. Import OpenAPI spec: `http://localhost:8000/openapi.json`
3. Set Authorization header with Bearer token
4. Test endpoints

### Option 2: Using cURL
```bash
# Get support tickets (requires auth)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/support/tickets

# Health check (no auth needed)
curl http://localhost:8000/health
```

### Option 3: Using Python
```python
import requests

# No auth needed
response = requests.get('http://localhost:8000/health')
print(response.json())

# With auth
headers = {'Authorization': 'Bearer YOUR_TOKEN'}
response = requests.get(
    'http://localhost:8000/api/support/tickets',
    headers=headers
)
print(response.json())
```

---

## 📊 Available Features & Endpoints

### Support Tickets (12 endpoints)
```
GET    /api/support/tickets
POST   /api/support/tickets
GET    /api/support/tickets/{id}
POST   /api/support/tickets/{id}/messages
PUT    /api/support/tickets/{id}
DELETE /api/support/tickets/{id}
... and 6 more
```

### Audit Logging (8 endpoints)
```
GET    /api/audit/admin-actions
GET    /api/audit/auth-events
GET    /api/audit/admin-logins
GET    /api/audit/email-logs
... and 4 more
```

### Coupon Management (14 endpoints)
```
GET    /api/coupons
POST   /api/admin/coupons
POST   /api/coupons/validate
PUT    /api/admin/coupons/{id}
DELETE /api/admin/coupons/{id}
... and 9 more
```

### Two-Factor Auth (12 endpoints)
```
GET    /api/admin/2fa/status
POST   /api/admin/2fa/enable
POST   /api/admin/2fa/verify
POST   /api/admin/2fa/disable
GET    /api/admin/2fa/backup-codes
... and 7 more
```

### Entitlements (16 endpoints)
```
GET    /api/entitlements/features
POST   /api/entitlements/assign
GET    /api/entitlements/user
... and 13 more
```

### Subscriptions (25 endpoints)
```
GET    /api/subscriptions/plans
POST   /api/subscriptions
GET    /api/subscriptions/{id}
POST   /api/subscriptions/{id}/upgrade
... and 21 more
```

### Payments (16 endpoints)
```
GET    /api/payments/methods
POST   /api/payments/methods
POST   /api/payments/process
GET    /api/transactions
... and 12 more
```

---

## 🖥️ Quick Access Links

| Service | URL | Purpose |
|---------|-----|---------|
| **Swagger UI** | http://localhost:8000/docs | 📖 Interactive API explorer |
| **ReDoc** | http://localhost:8000/redoc | 📚 Alternative documentation |
| **Health Check** | http://localhost:8000/health | ✓ Verify server |
| **OpenAPI Spec** | http://localhost:8000/openapi.json | 📋 Raw specification |

---

## 🧪 Quick Test: No Auth Required

### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-16T07:45:15.268128",
  "service": "BoxCostPro Python Backend"
}
```

### Test 2: API Documentation
```bash
curl http://localhost:8000/openapi.json | python -m json.tool
```

---

## 📱 Frontend Access

### If Frontend is Running on Port 3000
```
http://localhost:3000
```

### If Frontend is Running on Port 5173 (Vite)
```
http://localhost:5173
```

### To Start Frontend (if not running)
```bash
cd BoxCostPro  # TypeScript frontend folder
npm install    # Install dependencies
npm run dev    # Start development server
```

---

## 🔧 Tools for API Testing

### 1. **Postman** (Recommended)
- Download: https://www.postman.com/downloads/
- Import OpenAPI spec: `http://localhost:8000/openapi.json`
- Test all endpoints with UI

### 2. **Insomnia**
- Download: https://insomnia.rest/
- Import OpenAPI spec
- Better workspace organization

### 3. **cURL** (Command Line)
```bash
# Simple request
curl http://localhost:8000/health

# With auth header
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/support/tickets
```

### 4. **Thunder Client** (VS Code)
- Install VS Code extension
- Import OpenAPI spec
- Test directly in editor

---

## 📝 Common Tasks

### View All Available Endpoints
1. Go to: http://localhost:8000/docs
2. Scroll through all sections
3. See all 103 endpoints

### Test an Endpoint
1. Go to: http://localhost:8000/docs
2. Find the endpoint
3. Click "Try it out"
4. Fill in parameters
5. Click "Execute"
6. See response

### Download API Specification
1. Go to: http://localhost:8000/openapi.json
2. Right-click → Save As
3. Save as `api-spec.json`

### Use API in Your Code
```python
import requests

# Test without auth
response = requests.get('http://localhost:8000/health')
print(response.json())

# Test with auth
headers = {'Authorization': 'Bearer YOUR_TOKEN'}
response = requests.get(
    'http://localhost:8000/api/support/tickets',
    headers=headers
)
```

---

## ✅ Verification Checklist

- [ ] Backend running on http://localhost:8000
- [ ] Health check returns 200: http://localhost:8000/health
- [ ] Swagger UI loads: http://localhost:8000/docs
- [ ] Can see 103 endpoints listed
- [ ] ReDoc works: http://localhost:8000/redoc
- [ ] OpenAPI spec accessible: http://localhost:8000/openapi.json

---

## 🆘 Troubleshooting

### Backend Not Running?
```bash
cd BoxCostPython
$env:PYTHONPATH='C:\Users\ventu\BoxCostPro\BoxCostPro\BoxCostPython'
python -m uvicorn backend.main:app --reload --port 8000
```

### Port 8000 Already in Use?
```bash
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID)
taskkill /PID <PID> /F

# Start on different port
python -m uvicorn backend.main:app --port 8001
```

### CORS Issues?
Check that frontend URL is in CORS origins in `.env`

### Connection Refused?
1. Make sure backend is running
2. Check port is correct (8000)
3. Try: http://127.0.0.1:8000 instead of localhost

---

## 📞 Summary

**To access BoxCostPro**:
1. **API Docs** → http://localhost:8000/docs ✓ (Already open)
2. **Backend** → http://localhost:8000 ✓ (Running)
3. **Frontend** → http://localhost:3000 or :5173 (If running)

**Start exploring**:
- Click on any endpoint in Swagger UI
- See the description and parameters
- Try it out to test
- View response schemas

**You're all set! 🚀**

---

*Last Updated: January 16, 2026*  
*Status: All systems operational ✓*
