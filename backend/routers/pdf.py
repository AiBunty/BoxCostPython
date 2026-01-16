"""
PDF generation API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from backend.database import get_db
from backend.middleware.auth import get_current_user, get_current_tenant_id
from backend.services.pdf_generator_service import generate_invoice_pdf, generate_quote_pdf
from backend.services.usage_tracking_service import track_pdf_generation
from backend.models.invoice import Invoice
from backend.models.quote import Quote
from backend.models.user import User

router = APIRouter(prefix="/api/pdf", tags=["PDF Generation"])


@router.get("/invoice/{invoice_id}")
def generate_invoice_pdf_endpoint(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Generate PDF for an invoice.
    
    **Requires authentication**
    
    Returns PDF file as binary response.
    """
    # Get invoice
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.tenant_id == tenant_id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Prepare invoice data for PDF
    invoice_data = {
        'tenant_name': invoice.tenant.name if invoice.tenant else 'BoxCostPro',
        'tenant_address': invoice.tenant.address if invoice.tenant else '',
        'tenant_email': invoice.tenant.email if invoice.tenant else '',
        'tenant_phone': invoice.tenant.phone if invoice.tenant else '',
        'invoice_number': invoice.invoice_number,
        'invoice_date': invoice.invoice_date.strftime('%Y-%m-%d'),
        'due_date': invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else '',
        'party_name': invoice.party.name if invoice.party else 'N/A',
        'billing_address': invoice.billing_address or '',
        'party_email': invoice.party.email if invoice.party else '',
        'party_phone': invoice.party.phone if invoice.party else '',
        'currency': invoice.currency,
        'subtotal': float(invoice.subtotal) if invoice.subtotal else 0,
        'tax_amount': float(invoice.tax_amount) if invoice.tax_amount else 0,
        'tax_rate': float(invoice.tax_rate) if invoice.tax_rate else 0,
        'discount_amount': float(invoice.discount_amount) if invoice.discount_amount else 0,
        'total_amount': float(invoice.total_amount),
        'payment_status': invoice.status,
        'terms': invoice.terms or '',
        'notes': invoice.notes or '',
        'items': []
    }
    
    # Add line items
    for item in invoice.items:
        invoice_data['items'].append({
            'name': item.product_name or 'Item',
            'description': item.description or '',
            'quantity': float(item.quantity),
            'unit_price': float(item.unit_price),
            'total': float(item.total_price)
        })
    
    # Generate PDF
    try:
        pdf_bytes = generate_invoice_pdf(invoice_data)
        
        # Track usage
        track_pdf_generation(db, current_user.id, tenant_id, 'invoice')
        
        # Return PDF
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Invoice-{invoice.invoice_number}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@router.get("/quote/{quote_id}")
def generate_quote_pdf_endpoint(
    quote_id: int,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Generate PDF for a quote.
    
    **Requires authentication**
    
    Returns PDF file as binary response.
    """
    # Get quote
    quote = db.query(Quote).filter(
        Quote.id == quote_id,
        Quote.tenant_id == tenant_id
    ).first()
    
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    
    # Prepare quote data for PDF
    quote_data = {
        'tenant_name': quote.tenant.name if quote.tenant else 'BoxCostPro',
        'tenant_address': quote.tenant.address if quote.tenant else '',
        'tenant_email': quote.tenant.email if quote.tenant else '',
        'tenant_phone': quote.tenant.phone if quote.tenant else '',
        'quote_number': quote.quote_number,
        'quote_date': quote.quote_date.strftime('%Y-%m-%d'),
        'valid_until': quote.valid_until.strftime('%Y-%m-%d') if quote.valid_until else '',
        'party_name': quote.party.name if quote.party else 'N/A',
        'billing_address': quote.party.billing_address if quote.party else '',
        'party_email': quote.party.email if quote.party else '',
        'party_phone': quote.party.phone if quote.party else '',
        'currency': quote.currency,
        'subtotal': float(quote.subtotal) if quote.subtotal else 0,
        'tax_amount': float(quote.tax_amount) if quote.tax_amount else 0,
        'tax_rate': float(quote.tax_rate) if quote.tax_rate else 0,
        'discount_amount': float(quote.discount_amount) if quote.discount_amount else 0,
        'total_amount': float(quote.total_amount),
        'status': quote.status,
        'terms': quote.terms or '',
        'notes': quote.notes or '',
        'items': []
    }
    
    # Add line items
    for item in quote.items:
        quote_data['items'].append({
            'name': item.product_name or 'Item',
            'description': item.description or '',
            'quantity': float(item.quantity),
            'unit_price': float(item.unit_price),
            'total': float(item.total_price)
        })
    
    # Generate PDF
    try:
        pdf_bytes = generate_quote_pdf(quote_data)
        
        # Track usage
        track_pdf_generation(db, current_user.id, tenant_id, 'quote')
        
        # Return PDF
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Quote-{quote.quote_number}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )
