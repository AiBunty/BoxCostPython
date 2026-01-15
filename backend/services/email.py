"""Email service with multi-provider support and template rendering."""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict
from pathlib import Path
import logging

from backend.config import settings
from backend.models.audit import EmailLog
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class EmailTemplate:
    """Email template renderer."""
    
    @staticmethod
    def render_invoice_email(invoice_data: Dict) -> tuple:
        """Render invoice notification email."""
        subject = f"Invoice {invoice_data['invoice_number']} - {invoice_data['seller_name']}"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .invoice-details {{ background: white; padding: 15px; margin: 15px 0; border-left: 4px solid #4CAF50; }}
                .amount {{ font-size: 24px; color: #4CAF50; font-weight: bold; }}
                .footer {{ text-align: center; padding: 20px; color: #777; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Invoice Generated</h1>
                </div>
                <div class="content">
                    <p>Dear {invoice_data['buyer_name']},</p>
                    <p>A new invoice has been generated for your recent transaction.</p>
                    
                    <div class="invoice-details">
                        <h3>Invoice Details</h3>
                        <p><strong>Invoice Number:</strong> {invoice_data['invoice_number']}</p>
                        <p><strong>Date:</strong> {invoice_data['invoice_date']}</p>
                        <p><strong>Due Date:</strong> {invoice_data.get('due_date', 'Upon receipt')}</p>
                        <p class="amount">Total Amount: ₹{invoice_data['total_amount']}</p>
                    </div>
                    
                    <p>Please find the detailed invoice attached to this email.</p>
                    <p>If you have any questions, please don't hesitate to contact us.</p>
                    
                    <p>Best regards,<br>{invoice_data['seller_name']}</p>
                </div>
                <div class="footer">
                    <p>This is an automated email from BoxCostPro. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text = f"""
        Invoice Generated
        
        Dear {invoice_data['buyer_name']},
        
        A new invoice has been generated for your recent transaction.
        
        Invoice Number: {invoice_data['invoice_number']}
        Date: {invoice_data['invoice_date']}
        Due Date: {invoice_data.get('due_date', 'Upon receipt')}
        Total Amount: ₹{invoice_data['total_amount']}
        
        Please find the detailed invoice attached to this email.
        
        Best regards,
        {invoice_data['seller_name']}
        """
        
        return subject, html, text
    
    @staticmethod
    def render_subscription_renewal_email(user_data: Dict, subscription_data: Dict) -> tuple:
        """Render subscription renewal notification."""
        subject = f"Subscription Renewed - {subscription_data['plan_name']}"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2196F3; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .plan-box {{ background: white; padding: 15px; margin: 15px 0; border-left: 4px solid #2196F3; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #2196F3; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Subscription Renewed</h1>
                </div>
                <div class="content">
                    <p>Hi {user_data['full_name']},</p>
                    <p>Great news! Your BoxCostPro subscription has been successfully renewed.</p>
                    
                    <div class="plan-box">
                        <h3>{subscription_data['plan_name']}</h3>
                        <p><strong>Renewal Date:</strong> {subscription_data['renewed_at']}</p>
                        <p><strong>Valid Until:</strong> {subscription_data['expires_at']}</p>
                        <p><strong>Amount:</strong> ₹{subscription_data['amount']}</p>
                    </div>
                    
                    <p>You can continue enjoying all the features of your plan without interruption.</p>
                    
                    <a href="{settings.app_url}/dashboard" class="button">Go to Dashboard</a>
                    
                    <p>Thank you for being a valued customer!</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text = f"""
        Subscription Renewed
        
        Hi {user_data['full_name']},
        
        Your BoxCostPro subscription has been successfully renewed.
        
        Plan: {subscription_data['plan_name']}
        Renewal Date: {subscription_data['renewed_at']}
        Valid Until: {subscription_data['expires_at']}
        Amount: ₹{subscription_data['amount']}
        
        You can continue enjoying all the features of your plan.
        
        Thank you for being a valued customer!
        """
        
        return subject, html, text
    
    @staticmethod
    def render_support_ticket_email(ticket_data: Dict) -> tuple:
        """Render support ticket notification."""
        subject = f"Support Ticket #{ticket_data['ticket_number']} - {ticket_data['subject']}"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #FF9800; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .ticket-box {{ background: white; padding: 15px; margin: 15px 0; border-left: 4px solid #FF9800; }}
                .priority-high {{ color: #f44336; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Support Ticket Created</h1>
                </div>
                <div class="content">
                    <p>Your support ticket has been created successfully.</p>
                    
                    <div class="ticket-box">
                        <h3>Ticket #{ticket_data['ticket_number']}</h3>
                        <p><strong>Subject:</strong> {ticket_data['subject']}</p>
                        <p><strong>Priority:</strong> <span class="priority-{ticket_data['priority']}">{ticket_data['priority'].upper()}</span></p>
                        <p><strong>Status:</strong> {ticket_data['status']}</p>
                        <p><strong>Created:</strong> {ticket_data['created_at']}</p>
                    </div>
                    
                    <p>Our support team will review your ticket and respond as soon as possible.</p>
                    <p>You will receive updates via email when there are new responses.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text = f"""
        Support Ticket Created
        
        Your support ticket has been created successfully.
        
        Ticket Number: {ticket_data['ticket_number']}
        Subject: {ticket_data['subject']}
        Priority: {ticket_data['priority'].upper()}
        Status: {ticket_data['status']}
        Created: {ticket_data['created_at']}
        
        Our support team will review your ticket and respond soon.
        """
        
        return subject, html, text


class EmailService:
    """Email service for sending notifications."""
    
    def __init__(self):
        self.template = EmailTemplate()
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        attachments: Optional[List[tuple]] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Send an email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body (optional)
            attachments: List of (filename, bytes) tuples
            db: Database session for logging
            
        Returns:
            bool: True if sent successfully
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = settings.smtp_from_email
            message["To"] = to_email
            message["Subject"] = subject
            
            # Add text part
            if body_text:
                part_text = MIMEText(body_text, "plain", "utf-8")
                message.attach(part_text)
            
            # Add HTML part
            part_html = MIMEText(body_html, "html", "utf-8")
            message.attach(part_html)
            
            # Add attachments
            if attachments:
                for filename, file_bytes in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(file_bytes)
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={filename}"
                    )
                    message.attach(part)
            
            # Send via SMTP
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                use_tls=True,
                timeout=30
            )
            
            logger.info(f"Email sent successfully to {to_email}")
            
            # Log success
            if db:
                log = EmailLog(
                    to_email=to_email,
                    subject=subject,
                    status="sent",
                    provider="smtp"
                )
                db.add(log)
                await db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            
            # Log failure
            if db:
                log = EmailLog(
                    to_email=to_email,
                    subject=subject,
                    status="failed",
                    provider="smtp",
                    error_message=str(e)
                )
                db.add(log)
                await db.commit()
            
            return False
    
    async def send_invoice_email(
        self,
        invoice_data: Dict,
        pdf_bytes: Optional[bytes] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Send invoice notification email with PDF attachment."""
        subject, html, text = self.template.render_invoice_email(invoice_data)
        
        attachments = []
        if pdf_bytes:
            filename = f"invoice_{invoice_data['invoice_number']}.pdf"
            attachments.append((filename, pdf_bytes))
        
        return await self.send_email(
            to_email=invoice_data['buyer_email'],
            subject=subject,
            body_html=html,
            body_text=text,
            attachments=attachments,
            db=db
        )
    
    async def send_subscription_renewal_email(
        self,
        user_data: Dict,
        subscription_data: Dict,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Send subscription renewal notification."""
        subject, html, text = self.template.render_subscription_renewal_email(
            user_data, subscription_data
        )
        
        return await self.send_email(
            to_email=user_data['email'],
            subject=subject,
            body_html=html,
            body_text=text,
            db=db
        )
    
    async def send_support_ticket_email(
        self,
        ticket_data: Dict,
        user_email: str,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Send support ticket creation notification."""
        subject, html, text = self.template.render_support_ticket_email(ticket_data)
        
        return await self.send_email(
            to_email=user_email,
            subject=subject,
            body_html=html,
            body_text=text,
            db=db
        )


# Singleton instance
email_service = EmailService()
