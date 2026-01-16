"""Audit logging models."""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from backend.database import Base, BaseMixin


class AdminAuditLog(Base, BaseMixin):
    """
    Comprehensive audit log for admin actions.
    """
    __tablename__ = "admin_audit_logs"
    
    admin_id = Column(Integer, nullable=False, index=True)
    
    # Action Details
    action = Column(String(100), nullable=False, index=True)
    action_category = Column(String(50), nullable=False)  # user_management, subscription, system
    description = Column(Text, nullable=False)
    
    # Target
    target_type = Column(String(50), nullable=True)  # user, subscription, tenant
    target_id = Column(Integer, nullable=True, index=True)
    
    # Changes
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    
    # Request Info
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Result
    success = Column(String, nullable=False)  # Using String instead of Boolean for more states
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<AdminAuditLog(admin={self.admin_id}, action={self.action})>"


class AuthAuditLog(Base, BaseMixin):
    """
    Authentication event logging.
    """
    __tablename__ = "auth_audit_logs"
    
    # User
    user_id = Column(Integer, nullable=True, index=True)
    email = Column(String(255), nullable=True)
    
    # Event
    event_type = Column(String(50), nullable=False, index=True)  # login, logout, failed_login
    auth_method = Column(String(50), nullable=True)  # password, oauth, magic_link
    
    # Request Info
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    location = Column(String(100), nullable=True)
    
    # Result
    success = Column(String, nullable=False)
    failure_reason = Column(Text, nullable=True)
    
    # Metadata
    event_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<AuthAuditLog(user={self.user_id}, event={self.event_type})>"


class AdminLoginAuditLog(Base, BaseMixin):
    """
    Admin login tracking separate from user auth.
    """
    __tablename__ = "admin_login_audit_logs"
    
    admin_id = Column(Integer, nullable=True, index=True)
    username = Column(String(100), nullable=True)
    
    # Event
    event_type = Column(String(50), nullable=False)  # login_attempt, login_success, logout, 2fa_success
    
    # Request Info
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Result
    success = Column(String, nullable=False)
    failure_reason = Column(Text, nullable=True)
    
    # 2FA & Session
    two_factor_used = Column(String, nullable=False, default="false")
    session_id = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<AdminLoginAuditLog(admin={self.admin_id}, event={self.event_type})>"


class EmailLog(Base, BaseMixin):
    """
    Email sending log for tracking.
    """
    __tablename__ = "email_logs"
    
    user_id = Column(Integer, nullable=True, index=True)
    
    # Email Details
    email_type = Column(String(50), nullable=False)  # quote, invoice, verification, support
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    
    # Sending
    provider = Column(String(50), nullable=True)  # gmail, smtp, ses
    message_id = Column(String(255), nullable=True)
    
    # Status
    status = Column(String(20), nullable=False)  # sent, delivered, failed, bounced
    error_message = Column(Text, nullable=True)
    
    # Tracking
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<EmailLog(to={self.recipient}, type={self.email_type}, status={self.status})>"
