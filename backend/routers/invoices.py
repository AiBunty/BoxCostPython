"""Invoice API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from typing import Optional
from datetime import datetime
from decimal import Decimal

from backend.database import get_db
from backend.middleware.auth import get_current_user, get_tenant_context
from backend.models.user import User
from backend.models.invoice import Invoice, SubscriptionInvoice, PaymentTransaction
from backend.models.company_profile import CompanyProfile
from backend.services.gst import gst_calculator, invoice_number_generator
from backend.services.pdf import invoice_pdf_generator
from backend.services.email import email_service
from shared.schemas import (
    InvoiceResponse,
    InvoiceCreate,
    PaginatedResponse
)
from fastapi.responses import StreamingResponse
from io import BytesIO

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("", response_model=PaginatedResponse)
async def list_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_context)
):
    """
    List all invoices for the current tenant.
    """
    query = select(Invoice).where(Invoice.tenant_id == tenant_id)
    
    if status:
        query = query.where(Invoice.status == status)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Paginate and order by date descending
    query = query.order_by(Invoice.invoice_date.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    return {
        "items": [InvoiceResponse.from_orm(inv) for inv in invoices],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_context)
):
    """
    Get invoice details by ID.
    """
    result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id
            )
        )
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return InvoiceResponse.from_orm(invoice)


@router.post("", response_model=InvoiceResponse)
async def create_invoice(
    invoice_data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_context)
):
    """
    Create a new invoice.
    Calculates GST automatically based on seller/buyer GSTIN.
    """
    # Get company profile for seller info
    company_result = await db.execute(
        select(CompanyProfile).where(CompanyProfile.tenant_id == tenant_id)
    )
    company = company_result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=400, detail="Company profile not configured")
    
    # Determine if inter-state
    is_inter_state = gst_calculator.determine_inter_state(
        company.gst_number,
        invoice_data.buyer_gst
    )
    
    # Calculate GST (discount-before-tax parity)
    discount_amount = invoice_data.discount_amount or Decimal("0")
    gst_breakdown = gst_calculator.calculate_gst(
        amount=invoice_data.subtotal,
        gst_rate=invoice_data.gst_rate,
        is_inter_state=is_inter_state,
        discount_amount=discount_amount
    )
    
    # Generate invoice number scoped to financial year (TS parity: FY resets annually)
    financial_year = invoice_number_generator.get_financial_year(invoice_data.invoice_date or datetime.utcnow())
    last_number = await db.scalar(
        select(Invoice.invoice_number)
        .where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.financial_year == financial_year
            )
        )
        .order_by(desc(Invoice.id))
        .limit(1)
    )
    last_sequence = invoice_number_generator.parse_sequence(last_number) if last_number else 0
    invoice_number = invoice_number_generator.generate_invoice_number(
        prefix=company.invoice_prefix or "INV",
        sequence=last_sequence + 1,
        financial_year=financial_year
    )
    
    # Create invoice
    invoice = Invoice(
        tenant_id=tenant_id,
        invoice_number=invoice_number,
        financial_year=financial_year,
        invoice_date=invoice_data.invoice_date or datetime.utcnow(),
        due_date=invoice_data.due_date,
        
        # Seller (from company profile)
        seller_name=company.company_name,
        seller_address=company.address,
        seller_gst=company.gst_number,
        seller_pan=company.pan_number,
        
        # Buyer
        buyer_name=invoice_data.buyer_name,
        buyer_address=invoice_data.buyer_address,
        buyer_gst=invoice_data.buyer_gst,
        buyer_pan=invoice_data.buyer_pan,
        
        # Amounts
        subtotal=invoice_data.subtotal,
        discount_amount=discount_amount,
        cgst=gst_breakdown["cgst"],
        sgst=gst_breakdown["sgst"],
        igst=gst_breakdown["igst"],
        total_gst=gst_breakdown["total_gst"],
        total_amount=gst_breakdown["total_amount"],
        
        # Additional
        notes=invoice_data.notes,
        terms=invoice_data.terms,
        status="draft"
    )
    
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    
    return InvoiceResponse.from_orm(invoice)


@router.post("/{invoice_id}/finalize")
async def finalize_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_context)
):
    """
    Finalize an invoice (make it immutable and send to buyer).
    """
    result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id
            )
        )
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft invoices can be finalized")
    
    invoice.status = "sent"
    invoice.finalized_at = datetime.utcnow()
    # Generate PDF
    invoice_dict = {
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date.strftime("%Y-%m-%d"),
        "due_date": invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else "Upon receipt",
        "seller_name": invoice.seller_name,
        "seller_address": invoice.seller_address,
        "seller_gst": invoice.seller_gst,
        "seller_pan": invoice.seller_pan,
        "buyer_name": invoice.buyer_name,
        "buyer_address": invoice.buyer_address,
        "buyer_gst": invoice.buyer_gst,
        "buyer_pan": invoice.buyer_pan,
        "buyer_email": invoice.buyer_email if hasattr(invoice, 'buyer_email') else None,
        "subtotal": float(invoice.subtotal),
        "cgst": float(invoice.cgst),
        "sgst": float(invoice.sgst),
        "igst": float(invoice.igst),
        "total_gst": float(invoice.total_gst),
        "total_amount": float(invoice.total_amount),
        "notes": invoice.notes,
        "terms": invoice.terms
    }
    
    try:
        pdf_bytes = invoice_pdf_generator.generate_invoice_pdf(invoice_dict)
        
        # Send email with PDF attachment
        if invoice_dict.get('buyer_email'):
            await email_service.send_invoice_email(
                invoice_data=invoice_dict,
                pdf_bytes=pdf_bytes,
                db=db
            )
    except Exception as e:
        # Log error but don't fail finalization
        pass
    
    await db.commit()
    
    # TODO: Send email to buyer
    
    return {"message": "Invoice finalized and sent to buyer"}


@router.post("/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: int,
    payment_method: str,
    transaction_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_context)
):
    """
    Mark invoice as paid.
    """
    result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id
            )
        )
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="Invoice already paid")
    
    invoice.status = "paid"
    invoice.paid_at = datetime.utcnow()
    
    # Create payment transaction record
    transaction = PaymentTransaction(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        amount=invoice.total_amount,
        currency="INR",
        payment_method=payment_method,
        external_transaction_id=transaction_id,
        status="completed"
    )
    db.add(transaction)
    
    await db.commit()
    
    return {"message": "Invoice marked as paid"}


@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_tenant_context)
):
    """
    Download invoice as PDF.
    """
    result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id
            )
        )
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Prepare invoice data
    invoice_dict = {
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date.strftime("%Y-%m-%d"),
        "due_date": invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else "Upon receipt",
        "seller_name": invoice.seller_name,
        "seller_address": invoice.seller_address,
        "seller_gst": invoice.seller_gst,
        "seller_pan": invoice.seller_pan,
        "buyer_name": invoice.buyer_name,
        "buyer_address": invoice.buyer_address,
        "buyer_gst": invoice.buyer_gst,
        "buyer_pan": invoice.buyer_pan,
        "subtotal": float(invoice.subtotal),
        "cgst": float(invoice.cgst),
        "sgst": float(invoice.sgst),
        "igst": float(invoice.igst),
        "total_gst": float(invoice.total_gst),
        "total_amount": float(invoice.total_amount),
        "notes": invoice.notes,
        "terms": invoice.terms
    }
    
    # Generate PDF
    pdf_bytes = invoice_pdf_generator.generate_invoice_pdf(invoice_dict)
    
    # Return as downloadable file
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice_{invoice.invoice_number.replace('/', '_')}.pdf"
        }
    )


@router.get("/subscription/my-invoices", response_model=PaginatedResponse)
async def list_my_subscription_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    List subscription invoices for current user.
    """
    query = select(SubscriptionInvoice).where(SubscriptionInvoice.user_id == user.id)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Paginate
    query = query.order_by(SubscriptionInvoice.billing_date.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    invoices = result.scalars().all()
    
    return {
        "items": invoices,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }
