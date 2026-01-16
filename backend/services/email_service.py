"""
Email notification service with template support.
Handles transactional emails for quotes, invoices, support tickets, and subscriptions.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from backend.config import settings
from backend.models.audit import EmailLog

logger = logging.getLogger(__name__)


class EmailTemplate:
    """Email template builder."""
    
    @staticmethod
    def quote_created(quote_data: Dict[str, Any]) -> tuple[str, str]:
        """Generate quote creation email."""
        subject = f"Quote #{quote_data['quote_number']} - {quote_data['tenant_name']}"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">New Quote Created</h2>
            <p>Dear {quote_data['party_name']},</p>
            
            <p>Thank you for your interest! We've created a quote for your requirements.</p>
            
            <div style="background: #f8f9fa; padding: 15px; margin: 20px 0; border-radius: 5px;">
                <p style="margin: 5px 0;"><strong>Quote Number:</strong> {quote_data['quote_number']}</p>
                <p style="margin: 5px 0;"><strong>Date:</strong> {quote_data['quote_date']}</p>
                <p style="margin: 5px 0;"><strong>Valid Until:</strong> {quote_data['valid_until']}</p>
                <p style="margin: 5px 0;"><strong>Total Amount:</strong> {quote_data['currency']} {quote_data['total_amount']}</p>
            </div>
            
            <p>You can view and download your quote using the link below:</p>
            <p style="text-align: center;">
                <a href="{quote_data.get('quote_url', '#')}" 
                   style="background: #3498db; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    View Quote
                </a>
            </p>
            
            <p>If you have any questions, please don't hesitate to contact us.</p>
            
            <p>Best regards,<br>
            {quote_data['tenant_name']}</p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            <p style="color: #888; font-size: 12px;">
                This is an automated message. Please do not reply directly to this email.
            </p>
        </body>
        </html>
        """
        
        return subject, html
    
    @staticmethod
    def invoice_generated(invoice_data: Dict[str, Any]) -> tuple[str, str]:
        """Generate invoice notification email."""
        subject = f"Invoice #{invoice_data['invoice_number']} - Payment Due"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">Invoice Generated</h2>
            <p>Dear {invoice_data['party_name']},</p>
            
            <p>Your invoice is ready. Please find the details below:</p>
            
            <div style="background: #f8f9fa; padding: 15px; margin: 20px 0; border-radius: 5px;">
                <p style="margin: 5px 0;"><strong>Invoice Number:</strong> {invoice_data['invoice_number']}</p>
                <p style="margin: 5px 0;"><strong>Invoice Date:</strong> {invoice_data['invoice_date']}</p>
                <p style="margin: 5px 0;"><strong>Due Date:</strong> {invoice_data['due_date']}</p>
                <p style="margin: 5px 0;"><strong>Amount Due:</strong> {invoice_data['currency']} {invoice_data['total_amount']}</p>
                <p style="margin: 5px 0;"><strong>Status:</strong> <span style="color: #e74c3c;">{invoice_data['status']}</span></p>
            </div>
            
            <p>You can view and pay your invoice using the link below:</p>
            <p style="text-align: center;">
                <a href="{invoice_data.get('payment_url', '#')}" 
                   style="background: #27ae60; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Pay Invoice
                </a>
            </p>
            
            <p>Thank you for your business!</p>
            
            <p>Best regards,<br>
            {invoice_data['tenant_name']}</p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            <p style="color: #888; font-size: 12px;">
                This is an automated message. Please do not reply directly to this email.
            </p>
        </body>
        </html>
        """
        
        return subject, html
    
    @staticmethod
    def payment_received(payment_data: Dict[str, Any]) -> tuple[str, str]:
        """Generate payment confirmation email."""
        subject = f"Payment Received - {payment_data['currency']} {payment_data['amount']}"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #27ae60;">Payment Received Successfully</h2>
            <p>Dear {payment_data['customer_name']},</p>
            
            <p>We have received your payment. Thank you!</p>
            
            <div style="background: #d4edda; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #27ae60;">
                <p style="margin: 5px 0;"><strong>Transaction ID:</strong> {payment_data['transaction_id']}</p>
                <p style="margin: 5px 0;"><strong>Amount:</strong> {payment_data['currency']} {payment_data['amount']}</p>
                <p style="margin: 5px 0;"><strong>Payment Method:</strong> {payment_data['payment_method']}</p>
                <p style="margin: 5px 0;"><strong>Date:</strong> {payment_data['payment_date']}</p>
            </div>
            
            <p>A receipt has been sent to your email address.</p>
            
            <p style="text-align: center;">
                <a href="{payment_data.get('receipt_url', '#')}" 
                   style="background: #3498db; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Download Receipt
                </a>
            </p>
            
            <p>Best regards,<br>
            {payment_data['tenant_name']}</p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            <p style="color: #888; font-size: 12px;">
                This is an automated message. Please do not reply directly to this email.
            </p>
        </body>
        </html>
        """
        
        return subject, html
    
    @staticmethod
    def payment_failed(payment_data: Dict[str, Any]) -> tuple[str, str]:
        """Generate payment failure notification email."""
        subject = f"Payment Failed - Action Required"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #e74c3c;">Payment Failed</h2>
            <p>Dear {payment_data['customer_name']},</p>
            
            <p>We were unable to process your payment. Please review the details below:</p>
            
            <div style="background: #f8d7da; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #e74c3c;">
                <p style="margin: 5px 0;"><strong>Amount:</strong> {payment_data['currency']} {payment_data['amount']}</p>
                <p style="margin: 5px 0;"><strong>Reason:</strong> {payment_data.get('failure_reason', 'Payment declined')}</p>
                <p style="margin: 5px 0;"><strong>Date:</strong> {payment_data['payment_date']}</p>
            </div>
            
            <p>Please update your payment method or try again:</p>
            <p style="text-align: center;">
                <a href="{payment_data.get('retry_url', '#')}" 
                   style="background: #e74c3c; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Update Payment Method
                </a>
            </p>
            
            <p>If you continue to experience issues, please contact our support team.</p>
            
            <p>Best regards,<br>
            {payment_data['tenant_name']}</p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            <p style="color: #888; font-size: 12px;">
                This is an automated message. Please do not reply directly to this email.
            </p>
        </body>
        </html>
        """
        
        return subject, html
    
    @staticmethod
    def ticket_created(ticket_data: Dict[str, Any]) -> tuple[str, str]:
        """Generate support ticket creation email."""
        subject = f"Support Ticket #{ticket_data['ticket_number']} Created"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">Support Ticket Created</h2>
            <p>Dear {ticket_data['user_name']},</p>
            
            <p>We've received your support request and created a ticket for you.</p>
            
            <div style="background: #f8f9fa; padding: 15px; margin: 20px 0; border-radius: 5px;">
                <p style="margin: 5px 0;"><strong>Ticket Number:</strong> {ticket_data['ticket_number']}</p>
                <p style="margin: 5px 0;"><strong>Subject:</strong> {ticket_data['subject']}</p>
                <p style="margin: 5px 0;"><strong>Priority:</strong> {ticket_data['priority']}</p>
                <p style="margin: 5px 0;"><strong>Status:</strong> {ticket_data['status']}</p>
                <p style="margin: 5px 0;"><strong>Created:</strong> {ticket_data['created_at']}</p>
            </div>
            
            <p><strong>Description:</strong></p>
            <div style="background: #fff; padding: 15px; margin: 20px 0; border: 1px solid #ddd; border-radius: 5px;">
                {ticket_data['description']}
            </div>
            
            <p>Our support team will review your request and respond as soon as possible.</p>
            
            <p style="text-align: center;">
                <a href="{ticket_data.get('ticket_url', '#')}" 
                   style="background: #3498db; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    View Ticket
                </a>
            </p>
            
            <p>Best regards,<br>
            {ticket_data['tenant_name']} Support Team</p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            <p style="color: #888; font-size: 12px;">
                This is an automated message. Please do not reply directly to this email.
            </p>
        </body>
        </html>
        """
        
        return subject, html
    
    @staticmethod
    def ticket_updated(ticket_data: Dict[str, Any]) -> tuple[str, str]:
        """Generate ticket update notification email."""
        subject = f"Ticket #{ticket_data['ticket_number']} Updated - {ticket_data['status']}"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">Support Ticket Updated</h2>
            <p>Dear {ticket_data['user_name']},</p>
            
            <p>Your support ticket has been updated.</p>
            
            <div style="background: #d1ecf1; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #0c5460;">
                <p style="margin: 5px 0;"><strong>Ticket Number:</strong> {ticket_data['ticket_number']}</p>
                <p style="margin: 5px 0;"><strong>Status:</strong> {ticket_data['status']}</p>
                <p style="margin: 5px 0;"><strong>Updated By:</strong> {ticket_data.get('updated_by', 'Support Team')}</p>
            </div>
            
            {f'<p><strong>Latest Update:</strong></p><div style="background: #fff; padding: 15px; margin: 20px 0; border: 1px solid #ddd; border-radius: 5px;">{ticket_data.get("latest_message", "")}</div>' if ticket_data.get('latest_message') else ''}
            
            <p style="text-align: center;">
                <a href="{ticket_data.get('ticket_url', '#')}" 
                   style="background: #3498db; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    View Ticket
                </a>
            </p>
            
            <p>Best regards,<br>
            {ticket_data['tenant_name']} Support Team</p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            <p style="color: #888; font-size: 12px;">
                This is an automated message. Please do not reply directly to this email.
            </p>
        </body>
        </html>
        """
        
        return subject, html
    
    @staticmethod
    def subscription_activated(subscription_data: Dict[str, Any]) -> tuple[str, str]:
        """Generate subscription activation email."""
        subject = f"Subscription Activated - {subscription_data['plan_name']}"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #27ae60;">Subscription Activated</h2>
            <p>Dear {subscription_data['user_name']},</p>
            
            <p>Welcome! Your subscription has been activated.</p>
            
            <div style="background: #d4edda; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #27ae60;">
                <p style="margin: 5px 0;"><strong>Plan:</strong> {subscription_data['plan_name']}</p>
                <p style="margin: 5px 0;"><strong>Billing Cycle:</strong> {subscription_data['billing_cycle']}</p>
                <p style="margin: 5px 0;"><strong>Price:</strong> {subscription_data['currency']} {subscription_data['price']}</p>
                <p style="margin: 5px 0;"><strong>Next Billing Date:</strong> {subscription_data['next_billing_date']}</p>
            </div>
            
            <p>You now have access to all features included in your plan.</p>
            
            <p style="text-align: center;">
                <a href="{subscription_data.get('dashboard_url', '#')}" 
                   style="background: #3498db; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Go to Dashboard
                </a>
            </p>
            
            <p>Thank you for choosing {subscription_data['tenant_name']}!</p>
            
            <p>Best regards,<br>
            {subscription_data['tenant_name']}</p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            <p style="color: #888; font-size: 12px;">
                This is an automated message. Please do not reply directly to this email.
            </p>
        </body>
        </html>
        """
        
        return subject, html
    
    @staticmethod
    def subscription_cancelled(subscription_data: Dict[str, Any]) -> tuple[str, str]:
        """Generate subscription cancellation email."""
        subject = f"Subscription Cancelled - {subscription_data['plan_name']}"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #e74c3c;">Subscription Cancelled</h2>
            <p>Dear {subscription_data['user_name']},</p>
            
            <p>Your subscription has been cancelled as requested.</p>
            
            <div style="background: #f8d7da; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #e74c3c;">
                <p style="margin: 5px 0;"><strong>Plan:</strong> {subscription_data['plan_name']}</p>
                <p style="margin: 5px 0;"><strong>Cancellation Date:</strong> {subscription_data['cancelled_at']}</p>
                <p style="margin: 5px 0;"><strong>Access Until:</strong> {subscription_data.get('access_until', 'End of current billing period')}</p>
            </div>
            
            <p>You will continue to have access to your subscription until {subscription_data.get('access_until', 'the end of your billing period')}.</p>
            
            <p>We're sorry to see you go. If you change your mind, you can reactivate your subscription at any time.</p>
            
            <p style="text-align: center;">
                <a href="{subscription_data.get('reactivate_url', '#')}" 
                   style="background: #3498db; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Reactivate Subscription
                </a>
            </p>
            
            <p>Best regards,<br>
            {subscription_data['tenant_name']}</p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            <p style="color: #888; font-size: 12px;">
                This is an automated message. Please do not reply directly to this email.
            </p>
        </body>
        </html>
        """
        
        return subject, html


class EmailService:
    """Email sending service."""
    
    def __init__(self, db):
        self.db = db
        self.smtp_host = getattr(settings, 'SMTP_HOST', None)
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_user = getattr(settings, 'SMTP_USER', None)
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', None)
        self.from_email = getattr(settings, 'FROM_EMAIL', 'noreply@boxcostpro.com')
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
        email_type: str = "transactional",
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Send email and log to database.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            tenant_id: Optional tenant ID for logging
            user_id: Optional user ID for logging
            email_type: Type of email (quote, invoice, payment, ticket, subscription)
            attachments: List of attachments [{'filename': 'file.pdf', 'content': bytes, 'content_type': 'application/pdf'}]
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.smtp_host or not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP not configured, email not sent")
            self._log_email(to_email, subject, False, "SMTP not configured", tenant_id, user_id, email_type)
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Attach HTML
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Attach files
            if attachments:
                for attachment in attachments:
                    part = MIMEApplication(
                        attachment['content'],
                        _subtype=attachment.get('content_type', 'application/pdf').split('/')[-1]
                    )
                    part.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=attachment['filename']
                    )
                    msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to_email}: {subject}")
            self._log_email(to_email, subject, True, None, tenant_id, user_id, email_type)
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
            self._log_email(to_email, subject, False, str(e), tenant_id, user_id, email_type)
            return False
    
    def _log_email(
        self,
        to_email: str,
        subject: str,
        sent: bool,
        error: Optional[str],
        tenant_id: Optional[int],
        user_id: Optional[int],
        email_type: str
    ):
        """Log email attempt to database."""
        try:
            email_log = EmailLog(
                tenant_id=tenant_id,
                user_id=user_id,
                to_email=to_email,
                subject=subject,
                email_type=email_type,
                sent=sent,
                error_message=error,
                sent_at=datetime.utcnow() if sent else None
            )
            self.db.add(email_log)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log email: {e}", exc_info=True)
            self.db.rollback()
    
    # Convenience methods for specific email types
    def send_quote_email(self, to_email: str, quote_data: Dict[str, Any], tenant_id: int, pdf_content: Optional[bytes] = None):
        """Send quote creation email with optional PDF attachment."""
        subject, html = EmailTemplate.quote_created(quote_data)
        attachments = None
        if pdf_content:
            attachments = [{
                'filename': f"Quote-{quote_data.get('quote_number', 'N/A')}.pdf",
                'content': pdf_content,
                'content_type': 'application/pdf'
            }]
        return self.send_email(to_email, subject, html, tenant_id, email_type="quote", attachments=attachments)
    
    def send_invoice_email(self, to_email: str, invoice_data: Dict[str, Any], tenant_id: int, pdf_content: Optional[bytes] = None):
        """Send invoice notification email with optional PDF attachment."""
        subject, html = EmailTemplate.invoice_generated(invoice_data)
        attachments = None
        if pdf_content:
            attachments = [{
                'filename': f"Invoice-{invoice_data.get('invoice_number', 'N/A')}.pdf",
                'content': pdf_content,
                'content_type': 'application/pdf'
            }]
        return self.send_email(to_email, subject, html, tenant_id, email_type="invoice", attachments=attachments)
    
    def send_payment_confirmation(self, to_email: str, payment_data: Dict[str, Any], tenant_id: int, user_id: int):
        """Send payment received confirmation."""
        subject, html = EmailTemplate.payment_received(payment_data)
        return self.send_email(to_email, subject, html, tenant_id, user_id, email_type="payment_success")
    
    def send_payment_failure(self, to_email: str, payment_data: Dict[str, Any], tenant_id: int, user_id: int):
        """Send payment failure notification."""
        subject, html = EmailTemplate.payment_failed(payment_data)
        return self.send_email(to_email, subject, html, tenant_id, user_id, email_type="payment_failed")
    
    def send_ticket_created(self, to_email: str, ticket_data: Dict[str, Any], tenant_id: int, user_id: int):
        """Send ticket creation confirmation."""
        subject, html = EmailTemplate.ticket_created(ticket_data)
        return self.send_email(to_email, subject, html, tenant_id, user_id, email_type="ticket")
    
    def send_ticket_update(self, to_email: str, ticket_data: Dict[str, Any], tenant_id: int, user_id: int):
        """Send ticket update notification."""
        subject, html = EmailTemplate.ticket_updated(ticket_data)
        return self.send_email(to_email, subject, html, tenant_id, user_id, email_type="ticket")
    
    def send_subscription_activated(self, to_email: str, subscription_data: Dict[str, Any], tenant_id: int, user_id: int):
        """Send subscription activation email."""
        subject, html = EmailTemplate.subscription_activated(subscription_data)
        return self.send_email(to_email, subject, html, tenant_id, user_id, email_type="subscription")
    
    def send_subscription_cancelled(self, to_email: str, subscription_data: Dict[str, Any], tenant_id: int, user_id: int):
        """Send subscription cancellation email."""
        subject, html = EmailTemplate.subscription_cancelled(subscription_data)
        return self.send_email(to_email, subject, html, tenant_id, user_id, email_type="subscription")
