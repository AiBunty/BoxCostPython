"""User model - Core user entity with Clerk integration."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from backend.database import Base, BaseMixin


class UserRole(str, enum.Enum):
    """User role enumeration."""
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    SUPPORT_AGENT = "support_agent"
    SUPPORT_MANAGER = "support_manager"


class ApprovalStatus(str, enum.Enum):
    """User approval status enumeration."""
    NEW_USER = "new_user"
    PENDING_VERIFICATION = "pending_verification"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class User(Base, BaseMixin):
    """
    User model - Represents a user in the system.
    Integrates with Clerk for authentication.
    """
    __tablename__ = "users"
    
    # Clerk Integration
    clerk_user_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Basic Information
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Role & Status
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    approval_status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.NEW_USER, nullable=False)
    
    # Verification
    email_verified = Column(Boolean, default=False, nullable=False)
    phone_verified = Column(Boolean, default=False, nullable=False)
    submitted_for_verification_at = Column(DateTime(timezone=True), nullable=True)
    
    # Profile Completion
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    
    # Metadata
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    # tenants = relationship("TenantUser", back_populates="user")
    # company_profiles = relationship("CompanyProfile", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
