"""Authentication dependencies and middleware for FastAPI."""
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
import jwt
from datetime import datetime

from backend.database import get_db
from backend.config import settings
from backend.models.user import User
from backend.models.admin import Admin, AdminSession


class AuthenticationError(HTTPException):
    """Custom authentication error."""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from Clerk JWT token.
    
    Args:
        authorization: Authorization header with Bearer token
        db: Database session
        
    Returns:
        User: Authenticated user object
        
    Raises:
        AuthenticationError: If authentication fails
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        # TODO: Implement Clerk JWT verification
        # For now, this is a placeholder
        # In production, use Clerk SDK to verify the token
        
        # Placeholder: Extract user info from token
        # payload = verify_clerk_token(token)
        # clerk_user_id = payload.get("sub")
        
        # For development, accept any token and look up user by email
        # This should be replaced with proper Clerk verification
        raise AuthenticationError("Clerk authentication not yet implemented")
        
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid or expired token")
    except Exception as e:
        raise AuthenticationError(f"Authentication error: {str(e)}")


def get_current_admin(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Admin:
    """
    Get current authenticated admin from session token.
    
    Args:
        authorization: Authorization header with Bearer token
        db: Database session
        
    Returns:
        Admin: Authenticated admin object
        
    Raises:
        AuthenticationError: If authentication fails
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid authorization header")
    
    session_token = authorization.replace("Bearer ", "")
    
    # Look up session
    session = db.query(AdminSession).filter(
        AdminSession.session_token == session_token,
        AdminSession.is_active == True,
        AdminSession.expires_at > datetime.utcnow()
    ).first()
    
    if not session:
        raise AuthenticationError("Invalid or expired session")
    
    # Get admin
    admin = db.query(Admin).filter(
        Admin.id == session.admin_id,
        Admin.is_active == True
    ).first()
    
    if not admin:
        raise AuthenticationError("Admin account not found or inactive")
    
    # Update last activity
    session.last_activity_at = datetime.utcnow()
    db.commit()
    
    return admin


# Alias for backwards compatibility
require_admin = get_current_admin


def require_admin_role(
    role: str,
    admin: Admin = Depends(get_current_admin)
) -> Admin:
    """
    Require specific admin role.
    
    Args:
        role: Required role (e.g., 'super_admin')
        admin: Current admin user
        
    Returns:
        Admin: Authenticated admin with required role
        
    Raises:
        HTTPException: If admin doesn't have required role
    """
    if admin.role != role and admin.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires {role} role"
        )
    return admin


async def get_current_tenant_id(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> int:
    """
    Get tenant ID for current user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        int: Tenant ID
        
    Raises:
        HTTPException: If user has no tenant
    """
    from backend.models.tenant import TenantUser
    
    tenant_user = db.query(TenantUser).filter(
        TenantUser.user_id == current_user.id,
        TenantUser.is_active == True
    ).first()
    
    if not tenant_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with any tenant"
        )
    
    return tenant_user.tenant_id


async def get_tenant_context(
    current_user: User = Depends(get_current_user)
) -> int:
    """
    Get tenant context (tenant ID) for current user.
    Alias for get_current_tenant_id for backwards compatibility.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        int: Tenant ID
    """
    return await get_current_tenant_id(current_user)


class TenantContext:
    """Tenant context for multi-tenant queries."""
    
    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id
    
    def filter_query(self, query, model):
        """Apply tenant filter to query."""
        return query.filter(model.tenant_id == self.tenant_id)
