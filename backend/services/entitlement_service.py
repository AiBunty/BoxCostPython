"""
Entitlement Service - Feature access and quota management
"""
from datetime import datetime
from typing import List, Optional, Dict

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.models.entitlement import (
    Feature,
    UserEntitlement,
    TenantEntitlement,
    PlanTemplate,
    EntitlementLog,
)


class EntitlementService:
    """Service for managing user and tenant feature entitlements."""

    @staticmethod
    def check_feature_access(
        db: Session,
        user_id: int,
        tenant_id: int,
        feature_name: str,
    ) -> bool:
        """
        Check if a user has access to a feature.
        Considers: default features, user entitlements, tenant entitlements.
        """
        # Get feature
        feature = db.query(Feature).filter(Feature.name == feature_name).first()
        if not feature:
            return False

        # Check if feature is default (available to all)
        if feature.is_default:
            return True

        # Check user-specific entitlement
        user_entitlement = db.query(UserEntitlement).filter(
            and_(
                UserEntitlement.user_id == user_id,
                UserEntitlement.feature_id == feature.id,
                UserEntitlement.is_enabled == True,
                or_(
                    UserEntitlement.expires_at.is_(None),
                    UserEntitlement.expires_at > datetime.utcnow()
                )
            )
        ).first()

        if user_entitlement:
            return True

        # Check tenant-wide entitlement
        tenant_entitlement = db.query(TenantEntitlement).filter(
            and_(
                TenantEntitlement.tenant_id == tenant_id,
                TenantEntitlement.feature_id == feature.id,
                TenantEntitlement.is_enabled == True,
                or_(
                    TenantEntitlement.expires_at.is_(None),
                    TenantEntitlement.expires_at > datetime.utcnow()
                )
            )
        ).first()

        return tenant_entitlement is not None

    @staticmethod
    def check_quota_available(
        db: Session,
        user_id: int,
        tenant_id: int,
        feature_name: str,
        required_amount: int = 1,
    ) -> bool:
        """
        Check if user has quota available for a feature.
        Returns True if quota is available or unlimited.
        """
        feature = db.query(Feature).filter(Feature.name == feature_name).first()
        if not feature:
            return False

        # Check user quota first
        user_entitlement = db.query(UserEntitlement).filter(
            and_(
                UserEntitlement.user_id == user_id,
                UserEntitlement.feature_id == feature.id,
                UserEntitlement.is_enabled == True,
            )
        ).first()

        if user_entitlement:
            # No limit = unlimited
            if user_entitlement.quota_limit is None:
                return True
            # Check if quota available
            remaining = user_entitlement.quota_limit - user_entitlement.quota_used
            return remaining >= required_amount

        # Check tenant quota
        tenant_entitlement = db.query(TenantEntitlement).filter(
            and_(
                TenantEntitlement.tenant_id == tenant_id,
                TenantEntitlement.feature_id == feature.id,
                TenantEntitlement.is_enabled == True,
            )
        ).first()

        if tenant_entitlement:
            if tenant_entitlement.quota_limit is None:
                return True
            remaining = tenant_entitlement.quota_limit - tenant_entitlement.quota_used
            return remaining >= required_amount

        # No entitlement found
        return False

    @staticmethod
    def consume_quota(
        db: Session,
        user_id: int,
        tenant_id: int,
        feature_name: str,
        amount: int = 1,
    ) -> bool:
        """
        Consume quota for a feature.
        Returns True if successful, False if quota exceeded.
        """
        feature = db.query(Feature).filter(Feature.name == feature_name).first()
        if not feature:
            return False

        # Try user quota first
        user_entitlement = db.query(UserEntitlement).filter(
            and_(
                UserEntitlement.user_id == user_id,
                UserEntitlement.feature_id == feature.id,
                UserEntitlement.is_enabled == True,
            )
        ).first()

        if user_entitlement:
            if user_entitlement.quota_limit is None:
                # Unlimited
                user_entitlement.quota_used += amount
                db.commit()
                return True
            
            remaining = user_entitlement.quota_limit - user_entitlement.quota_used
            if remaining >= amount:
                user_entitlement.quota_used += amount
                db.commit()
                return True
            return False

        # Try tenant quota
        tenant_entitlement = db.query(TenantEntitlement).filter(
            and_(
                TenantEntitlement.tenant_id == tenant_id,
                TenantEntitlement.feature_id == feature.id,
                TenantEntitlement.is_enabled == True,
            )
        ).first()

        if tenant_entitlement:
            if tenant_entitlement.quota_limit is None:
                tenant_entitlement.quota_used += amount
                db.commit()
                return True
            
            remaining = tenant_entitlement.quota_limit - tenant_entitlement.quota_used
            if remaining >= amount:
                tenant_entitlement.quota_used += amount
                db.commit()
                return True
            return False

        return False

    @staticmethod
    def grant_user_feature(
        db: Session,
        user_id: int,
        tenant_id: int,
        feature_name: str,
        admin_id: Optional[int] = None,
        quota_limit: Optional[int] = None,
        expires_at: Optional[datetime] = None,
    ) -> UserEntitlement:
        """Grant a feature to a user."""
        feature = db.query(Feature).filter(Feature.name == feature_name).first()
        if not feature:
            raise ValueError(f"Feature not found: {feature_name}")

        # Check if already exists
        existing = db.query(UserEntitlement).filter(
            and_(
                UserEntitlement.user_id == user_id,
                UserEntitlement.feature_id == feature.id,
            )
        ).first()

        if existing:
            existing.is_enabled = True
            existing.quota_limit = quota_limit
            existing.expires_at = expires_at
            existing.granted_by = admin_id
            existing.granted_at = datetime.utcnow()
            entitlement = existing
        else:
            entitlement = UserEntitlement(
                user_id=user_id,
                tenant_id=tenant_id,
                feature_id=feature.id,
                is_enabled=True,
                quota_limit=quota_limit,
                expires_at=expires_at,
                granted_by=admin_id,
            )
            db.add(entitlement)

        db.commit()
        db.refresh(entitlement)

        # Log the change
        log = EntitlementLog(
            entity_type="user_entitlement",
            entity_id=entitlement.id,
            action="granted",
            admin_id=admin_id,
            user_id=user_id,
            tenant_id=tenant_id,
            new_value={"feature": feature_name, "quota_limit": quota_limit},
        )
        db.add(log)
        db.commit()

        return entitlement

    @staticmethod
    def grant_tenant_feature(
        db: Session,
        tenant_id: int,
        feature_name: str,
        admin_id: Optional[int] = None,
        quota_limit: Optional[int] = None,
        expires_at: Optional[datetime] = None,
    ) -> TenantEntitlement:
        """Grant a feature to all users in a tenant."""
        feature = db.query(Feature).filter(Feature.name == feature_name).first()
        if not feature:
            raise ValueError(f"Feature not found: {feature_name}")

        existing = db.query(TenantEntitlement).filter(
            and_(
                TenantEntitlement.tenant_id == tenant_id,
                TenantEntitlement.feature_id == feature.id,
            )
        ).first()

        if existing:
            existing.is_enabled = True
            existing.quota_limit = quota_limit
            existing.expires_at = expires_at
            existing.granted_by = admin_id
            existing.granted_at = datetime.utcnow()
            entitlement = existing
        else:
            entitlement = TenantEntitlement(
                tenant_id=tenant_id,
                feature_id=feature.id,
                is_enabled=True,
                quota_limit=quota_limit,
                expires_at=expires_at,
                granted_by=admin_id,
            )
            db.add(entitlement)

        db.commit()
        db.refresh(entitlement)

        # Log the change
        log = EntitlementLog(
            entity_type="tenant_entitlement",
            entity_id=entitlement.id,
            action="granted",
            admin_id=admin_id,
            tenant_id=tenant_id,
            new_value={"feature": feature_name, "quota_limit": quota_limit},
        )
        db.add(log)
        db.commit()

        return entitlement

    @staticmethod
    def get_user_features(
        db: Session,
        user_id: int,
        tenant_id: int,
    ) -> List[Dict]:
        """
        Get all features available to a user.
        Returns list of features with access and quota info.
        """
        # Get all features
        all_features = db.query(Feature).filter(Feature.is_default == False).all()
        
        result = []
        for feature in all_features:
            has_access = EntitlementService.check_feature_access(
                db, user_id, tenant_id, feature.name
            )
            
            if has_access:
                # Get quota info
                user_ent = db.query(UserEntitlement).filter(
                    and_(
                        UserEntitlement.user_id == user_id,
                        UserEntitlement.feature_id == feature.id,
                    )
                ).first()
                
                tenant_ent = db.query(TenantEntitlement).filter(
                    and_(
                        TenantEntitlement.tenant_id == tenant_id,
                        TenantEntitlement.feature_id == feature.id,
                    )
                ).first()
                
                quota_info = None
                if user_ent:
                    quota_info = {
                        "limit": user_ent.quota_limit,
                        "used": user_ent.quota_used,
                        "remaining": None if user_ent.quota_limit is None else user_ent.quota_limit - user_ent.quota_used,
                    }
                elif tenant_ent:
                    quota_info = {
                        "limit": tenant_ent.quota_limit,
                        "used": tenant_ent.quota_used,
                        "remaining": None if tenant_ent.quota_limit is None else tenant_ent.quota_limit - tenant_ent.quota_used,
                    }
                
                result.append({
                    "name": feature.name,
                    "display_name": feature.display_name,
                    "category": feature.category,
                    "quota": quota_info,
                })
        
        return result


entitlement_service = EntitlementService()
