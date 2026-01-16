"""Audit logging service."""
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.models.audit import AdminAuditLog, AuthAuditLog, AdminLoginAuditLog


class AuditService:
    """Service for creating audit log entries."""

    @staticmethod
    def log_admin_action(
        db: Session,
        admin_id: int,
        action: str,
        action_category: str,
        description: str,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: str = "true",
        error_message: Optional[str] = None,
    ) -> AdminAuditLog:
        """Log an admin action."""
        log_entry = AdminAuditLog(
            admin_id=admin_id,
            action=action,
            action_category=action_category,
            description=description,
            target_type=target_type,
            target_id=target_id,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def log_auth_event(
        db: Session,
        event_type: str,
        success: str = "true",
        user_id: Optional[int] = None,
        email: Optional[str] = None,
        auth_method: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        location: Optional[str] = None,
        failure_reason: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
    ) -> AuthAuditLog:
        """Log an authentication event."""
        log_entry = AuthAuditLog(
            user_id=user_id,
            email=email,
            event_type=event_type,
            auth_method=auth_method,
            ip_address=ip_address,
            user_agent=user_agent,
            location=location,
            success=success,
            failure_reason=failure_reason,
            event_metadata=event_metadata,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def log_admin_login_event(
        db: Session,
        event_type: str,
        success: str = "true",
        admin_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        failure_reason: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AdminLoginAuditLog:
        """Log an admin login/logout event."""
        log_entry = AdminLoginAuditLog(
            admin_id=admin_id,
            username=username,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason,
            session_id=session_id,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry


# Singleton instance
audit_service = AuditService()
