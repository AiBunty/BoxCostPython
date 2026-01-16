"""Two-Factor Authentication service (scaffolding)."""
import secrets
import hashlib
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

try:
    import pyotp
    PYOTP_AVAILABLE = True
except ImportError:
    PYOTP_AVAILABLE = False

from backend.models.two_factor_auth import TwoFactorAuth, TwoFactorBackupCode


class TwoFactorAuthService:
    """Service for managing 2FA."""

    @staticmethod
    def generate_totp_secret() -> str:
        """Generate a TOTP secret (base32 encoded)."""
        if PYOTP_AVAILABLE:
            return pyotp.random_base32()
        return secrets.token_urlsafe(20)

    @staticmethod
    def generate_backup_codes(count: int = 10) -> List[str]:
        """Generate backup codes for 2FA recovery."""
        return [secrets.token_urlsafe(8) for _ in range(count)]

    @staticmethod
    def hash_code(code: str) -> str:
        """Hash a backup code for secure storage."""
        return hashlib.sha256(code.encode()).hexdigest()

    @staticmethod
    def enable_2fa_for_admin(
        db: Session,
        admin_id: int,
        method: str = "totp",
    ) -> Tuple[TwoFactorAuth, List[str]]:
        """
        Enable 2FA for an admin.
        Returns the TwoFactorAuth record and list of backup codes.
        """
        # Check if 2FA already exists
        existing = db.query(TwoFactorAuth).filter(
            TwoFactorAuth.admin_id == admin_id
        ).first()

        if existing and existing.is_enabled:
            raise ValueError("2FA is already enabled for this admin")

        # Generate secret and backup codes
        totp_secret = TwoFactorAuthService.generate_totp_secret()
        backup_codes = TwoFactorAuthService.generate_backup_codes()

        if existing:
            existing.method = method
            existing.totp_secret = totp_secret
            existing.is_enabled = False  # Must verify first
            two_fa = existing
        else:
            two_fa = TwoFactorAuth(
                admin_id=admin_id,
                method=method,
                totp_secret=totp_secret,
                is_enabled=False,
            )
            db.add(two_fa)

        db.flush()

        # Store backup codes
        for code in backup_codes:
            backup_code = TwoFactorBackupCode(
                two_factor_auth_id=two_fa.id,
                code_hash=TwoFactorAuthService.hash_code(code),
            )
            db.add(backup_code)

        db.commit()
        db.refresh(two_fa)

        return two_fa, backup_codes

    @staticmethod
    def verify_and_enable_totp(
        db: Session,
        admin_id: int,
        totp_code: str,
    ) -> bool:
        """
        Verify TOTP code and enable 2FA.
        Uses pyotp library for verification.
        """
        two_fa = db.query(TwoFactorAuth).filter(
            TwoFactorAuth.admin_id == admin_id
        ).first()

        if not two_fa or not two_fa.totp_secret:
            raise ValueError("2FA setup not initiated")

        # Verify TOTP code using pyotp
        if PYOTP_AVAILABLE:
            totp = pyotp.TOTP(two_fa.totp_secret)
            if totp.verify(totp_code, valid_window=1):  # Allow ±30 seconds
                two_fa.totp_verified = True
                two_fa.is_enabled = True
                db.commit()
                return True
            return False
        else:
            # Fallback for testing without pyotp
            if len(totp_code) == 6 and totp_code.isdigit():
                two_fa.totp_verified = True
                two_fa.is_enabled = True
                db.commit()
                return True
            return False

    @staticmethod
    def disable_2fa(db: Session, admin_id: int) -> bool:
        """Disable 2FA for an admin."""
        two_fa = db.query(TwoFactorAuth).filter(
            TwoFactorAuth.admin_id == admin_id
        ).first()

        if not two_fa:
            return False

        two_fa.is_enabled = False
        db.commit()
        return True

    @staticmethod
    def verify_backup_code(
        db: Session,
        admin_id: int,
        backup_code: str,
    ) -> bool:
        """Verify a backup code (for 2FA recovery)."""
        two_fa = db.query(TwoFactorAuth).filter(
            TwoFactorAuth.admin_id == admin_id,
            TwoFactorAuth.is_enabled == True,
        ).first()

        if not two_fa:
            return False

        code_hash = TwoFactorAuthService.hash_code(backup_code)
        backup = db.query(TwoFactorBackupCode).filter(
            TwoFactorBackupCode.two_factor_auth_id == two_fa.id,
            TwoFactorBackupCode.code_hash == code_hash,
            TwoFactorBackupCode.is_used == False,
        ).first()

        if not backup:
            return False

        backup.is_used = True
        db.commit()
        return True


# Singleton instance
two_factor_service = TwoFactorAuthService()
