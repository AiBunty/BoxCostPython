"""Two-Factor Authentication (2FA) models."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from backend.database import Base, BaseMixin
from datetime import datetime


class TwoFactorAuth(Base, BaseMixin):
    """
    Two-Factor Authentication settings for users/admins.
    """
    __tablename__ = "two_factor_auth"
    
    user_id = Column(Integer, nullable=True, index=True)
    admin_id = Column(Integer, nullable=True, index=True)
    
    # 2FA Method
    method = Column(String(20), nullable=False, default="totp")  # totp, sms, email
    
    # TOTP (Time-based One-Time Password)
    totp_secret = Column(String(32), nullable=True)
    totp_verified = Column(Boolean, default=False, nullable=False)
    
    # Backup Codes
    backup_codes = Column(String(500), nullable=True)  # JSON array of hashed codes
    
    # Status
    is_enabled = Column(Boolean, default=False, nullable=False)
    enabled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Recovery
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<TwoFactorAuth(user={self.user_id}, admin={self.admin_id}, method={self.method})>"


class TwoFactorBackupCode(Base, BaseMixin):
    """
    Backup codes for 2FA recovery.
    """
    __tablename__ = "two_factor_backup_codes"
    
    two_factor_auth_id = Column(Integer, nullable=False, index=True)
    
    code_hash = Column(String(64), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<TwoFactorBackupCode(2fa={self.two_factor_auth_id}, used={self.is_used})>"
