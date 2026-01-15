"""Authentication service for user and admin operations."""
from passlib.context import CryptContext
from datetime import datetime, timedelta
import secrets
import pyotp
from typing import Optional, Tuple

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def generate_session_token() -> str:
        """Generate a secure random session token."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_2fa_secret() -> str:
        """Generate a new TOTP secret for 2FA."""
        return pyotp.random_base32()
    
    @staticmethod
    def verify_2fa_token(secret: str, token: str) -> bool:
        """Verify a TOTP token."""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)
    
    @staticmethod
    def get_2fa_qr_code_url(secret: str, username: str, issuer: str = "BoxCostPro") -> str:
        """Get QR code provisioning URL for 2FA setup."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=issuer)
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> list:
        """Generate backup codes for 2FA."""
        return [secrets.token_hex(4).upper() for _ in range(count)]


class SessionManager:
    """Manages session lifecycle."""
    
    @staticmethod
    def create_session_expiry(timeout_minutes: int = 30) -> datetime:
        """Create session expiry datetime."""
        return datetime.utcnow() + timedelta(minutes=timeout_minutes)
    
    @staticmethod
    def is_session_expired(expires_at: datetime) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() > expires_at
    
    @staticmethod
    def should_extend_session(
        last_activity: datetime,
        idle_timeout_minutes: int = 30
    ) -> bool:
        """Check if session should be extended based on activity."""
        return (datetime.utcnow() - last_activity).total_seconds() < (idle_timeout_minutes * 60)


# Singleton instances
auth_service = AuthService()
session_manager = SessionManager()
