"""
Two-Factor Authentication API routes
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_admin
from backend.models.admin import Admin
from backend.models.two_factor_auth import TwoFactorAuth
from backend.services.two_factor_service import two_factor_service


# Schemas
class TwoFactorSetupRequest(BaseModel):
    method: str = "totp"  # totp, sms, email


class TwoFactorSetupResponse(BaseModel):
    totp_secret: str
    backup_codes: List[str]
    qr_code_url: Optional[str] = None


class TwoFactorVerifyRequest(BaseModel):
    totp_code: str


class TwoFactorStatusResponse(BaseModel):
    enabled: bool
    method: Optional[str] = None
    enabled_at: Optional[datetime] = None


router = APIRouter(prefix="/api/admin/2fa", tags=["2FA"])


@router.get("/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get current 2FA status for admin."""
    two_fa = db.query(TwoFactorAuth).filter(
        TwoFactorAuth.admin_id == current_admin.id
    ).first()
    
    if not two_fa:
        return TwoFactorStatusResponse(enabled=False)
    
    return TwoFactorStatusResponse(
        enabled=two_fa.is_enabled,
        method=two_fa.method,
        enabled_at=two_fa.enabled_at,
    )


@router.post("/enable", response_model=TwoFactorSetupResponse)
async def enable_2fa(
    data: TwoFactorSetupRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Enable 2FA for current admin.
    Returns TOTP secret and backup codes.
    """
    try:
        two_fa, backup_codes = two_factor_service.enable_2fa_for_admin(
            db=db,
            admin_id=current_admin.id,
            method=data.method,
        )
        
        # Generate QR code URL for TOTP
        qr_code_url = None
        if data.method == "totp":
            # Format: otpauth://totp/BoxCostPro:admin@example.com?secret=SECRET&issuer=BoxCostPro
            qr_code_url = f"otpauth://totp/BoxCostPro:{current_admin.username}?secret={two_fa.totp_secret}&issuer=BoxCostPro"
        
        return TwoFactorSetupResponse(
            totp_secret=two_fa.totp_secret,
            backup_codes=backup_codes,
            qr_code_url=qr_code_url,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/verify")
async def verify_2fa(
    data: TwoFactorVerifyRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Verify TOTP code and fully enable 2FA.
    Must be called after /enable to confirm setup.
    """
    success = two_factor_service.verify_and_enable_totp(
        db=db,
        admin_id=current_admin.id,
        totp_code=data.totp_code,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code"
        )
    
    # Update enabled timestamp
    two_fa = db.query(TwoFactorAuth).filter(
        TwoFactorAuth.admin_id == current_admin.id
    ).first()
    
    if two_fa:
        two_fa.enabled_at = datetime.utcnow()
        db.commit()
    
    return {"message": "2FA enabled successfully", "enabled": True}


@router.post("/disable")
async def disable_2fa(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Disable 2FA for current admin."""
    success = two_factor_service.disable_2fa(
        db=db,
        admin_id=current_admin.id,
    )
    
    if not success:
        return {"message": "2FA was not enabled", "enabled": False}
    
    return {"message": "2FA disabled successfully", "enabled": False}


@router.post("/verify-backup")
async def verify_backup_code(
    backup_code: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Verify a backup code for 2FA recovery.
    Used when TOTP is unavailable.
    """
    success = two_factor_service.verify_backup_code(
        db=db,
        admin_id=current_admin.id,
        backup_code=backup_code,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used backup code"
        )
    
    return {"message": "Backup code verified successfully", "valid": True}


@router.get("/backup-codes")
async def get_backup_codes_status(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Get count of remaining backup codes.
    Does NOT return the actual codes (they're hashed).
    """
    two_fa = db.query(TwoFactorAuth).filter(
        TwoFactorAuth.admin_id == current_admin.id,
        TwoFactorAuth.is_enabled == True,
    ).first()
    
    if not two_fa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="2FA not enabled"
        )
    
    from backend.models.two_factor_auth import TwoFactorBackupCode
    
    remaining = db.query(TwoFactorBackupCode).filter(
        TwoFactorBackupCode.two_factor_auth_id == two_fa.id,
        TwoFactorBackupCode.is_used == False,
    ).count()
    
    return {
        "total_codes": 10,
        "remaining_codes": remaining,
        "used_codes": 10 - remaining,
    }
