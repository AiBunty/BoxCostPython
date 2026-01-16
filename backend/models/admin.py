"""Admin model - Platform administrators with separate authentication."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base, BaseMixin


class Admin(Base, BaseMixin):
    """
    Admin model - Platform administrator with separate identity system.
    Uses bcrypt for password hashing, separate from Clerk user authentication.
    """
    __tablename__ = "admins"
    
    # Identity
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    
    # Authentication
    password_hash = Column(String(255), nullable=False)  # bcrypt hashed
    password_changed = Column(Boolean, default=False, nullable=False)  # Track if password changed from default
    
    # 2FA
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(255), nullable=True)  # TOTP secret
    backup_codes = Column(Text, nullable=True)  # Encrypted JSON array
    
    # Role & Permissions
    role = Column(String(50), default="admin", nullable=False)  # admin, super_admin
    permissions = Column(Text, nullable=True)  # JSON array of permissions
    
    # Security
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_by = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    # sessions = relationship("AdminSession", back_populates="admin")
    # audit_logs = relationship("AdminAuditLog", back_populates="admin")
    
    def __repr__(self):
        return f"<Admin(id={self.id}, username={self.username}, role={self.role})>"


class AdminSession(Base, BaseMixin):
    """
    AdminSession model - Tracks active admin sessions.
    """
    __tablename__ = "admin_sessions"
    
    admin_id = Column(Integer, nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    
    # Session Info
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Expiry
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    # admin = relationship("Admin", back_populates="sessions")
    
    def __repr__(self):
        return f"<AdminSession(admin_id={self.admin_id}, expires_at={self.expires_at})>"
