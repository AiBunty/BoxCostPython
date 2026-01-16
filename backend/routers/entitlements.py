"""
Entitlement API - Feature access management
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_admin, get_current_user
from backend.models.admin import Admin
from backend.models.user import User
from backend.models.entitlement import Feature, UserEntitlement, TenantEntitlement
from backend.services.entitlement_service import entitlement_service


# Schemas
class FeatureResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str]
    category: str
    is_default: bool
    min_plan_level: int

    class Config:
        from_attributes = True


class QuotaInfo(BaseModel):
    limit: Optional[int]
    used: int
    remaining: Optional[int]


class UserFeatureResponse(BaseModel):
    name: str
    display_name: str
    category: str
    quota: Optional[QuotaInfo]


class GrantFeatureRequest(BaseModel):
    feature_name: str
    quota_limit: Optional[int] = None
    expires_at: Optional[datetime] = None


class CheckAccessRequest(BaseModel):
    feature_name: str


class CheckAccessResponse(BaseModel):
    has_access: bool
    quota_available: bool
    quota_info: Optional[QuotaInfo] = None


router = APIRouter(prefix="/api/entitlements", tags=["Entitlements"])


# User endpoints
@router.get("/me/features", response_model=List[UserFeatureResponse])
async def get_my_features(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all features available to the current user."""
    features = entitlement_service.get_user_features(
        db=db,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    return features


@router.post("/me/check-access", response_model=CheckAccessResponse)
async def check_my_access(
    data: CheckAccessRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if current user has access to a feature."""
    has_access = entitlement_service.check_feature_access(
        db=db,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        feature_name=data.feature_name,
    )
    
    quota_available = entitlement_service.check_quota_available(
        db=db,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        feature_name=data.feature_name,
    )
    
    return CheckAccessResponse(
        has_access=has_access,
        quota_available=quota_available,
    )


# Admin endpoints
@router.get("/features", response_model=List[FeatureResponse])
async def list_features(
    category: Optional[str] = Query(None),
    is_default: Optional[bool] = Query(None),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all available features (admin only)."""
    query = db.query(Feature)
    
    if category:
        query = query.filter(Feature.category == category)
    if is_default is not None:
        query = query.filter(Feature.is_default == is_default)
    
    features = query.all()
    return features


@router.post("/features")
async def create_feature(
    name: str,
    display_name: str,
    category: str,
    description: Optional[str] = None,
    is_default: bool = False,
    min_plan_level: int = 0,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create a new feature (admin only)."""
    # Check if feature already exists
    existing = db.query(Feature).filter(Feature.name == name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feature already exists"
        )
    
    feature = Feature(
        name=name,
        display_name=display_name,
        description=description,
        category=category,
        is_default=is_default,
        min_plan_level=min_plan_level,
    )
    db.add(feature)
    db.commit()
    db.refresh(feature)
    
    return feature


@router.post("/users/{user_id}/grant")
async def grant_user_feature(
    user_id: int,
    data: GrantFeatureRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Grant a feature to a specific user (admin only)."""
    from backend.models.user import User
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        entitlement = entitlement_service.grant_user_feature(
            db=db,
            user_id=user_id,
            tenant_id=user.tenant_id,
            feature_name=data.feature_name,
            admin_id=current_admin.id,
            quota_limit=data.quota_limit,
            expires_at=data.expires_at,
        )
        return {"message": "Feature granted successfully", "entitlement_id": entitlement.id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/tenants/{tenant_id}/grant")
async def grant_tenant_feature(
    tenant_id: int,
    data: GrantFeatureRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Grant a feature to all users in a tenant (admin only)."""
    from backend.models.tenant import Tenant
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    try:
        entitlement = entitlement_service.grant_tenant_feature(
            db=db,
            tenant_id=tenant_id,
            feature_name=data.feature_name,
            admin_id=current_admin.id,
            quota_limit=data.quota_limit,
            expires_at=data.expires_at,
        )
        return {"message": "Feature granted to tenant", "entitlement_id": entitlement.id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/users/{user_id}/features", response_model=List[UserFeatureResponse])
async def get_user_features(
    user_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get all features for a specific user (admin only)."""
    from backend.models.user import User
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    features = entitlement_service.get_user_features(
        db=db,
        user_id=user_id,
        tenant_id=user.tenant_id,
    )
    return features


@router.delete("/users/{user_id}/features/{feature_name}")
async def revoke_user_feature(
    user_id: int,
    feature_name: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Revoke a feature from a user (admin only)."""
    feature = db.query(Feature).filter(Feature.name == feature_name).first()
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature not found"
        )
    
    entitlement = db.query(UserEntitlement).filter(
        UserEntitlement.user_id == user_id,
        UserEntitlement.feature_id == feature.id,
    ).first()
    
    if not entitlement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entitlement not found"
        )
    
    entitlement.is_enabled = False
    db.commit()
    
    return {"message": "Feature revoked successfully"}
