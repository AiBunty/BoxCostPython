"""
PDF generation service for invoices and quotes.
Uses ReportLab to create professional PDF documents.
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from io import BytesIO
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Base class for PDF document generation."""
    
    def __init__(self, page_size=letter):
        self.page_size = page_size
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles."""
        # Company name style
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=6,
            alignment=TA_LEFT
        ))
        
        # Document title style
        self.styles.add(ParagraphStyle(
            name='DocumentTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=12,
            alignment=TA_RIGHT
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#2c3e50'),
            spaceBefore=12,
            spaceAfter=6,
            alignment=TA_LEFT
        ))
        
        # Address style
        self.styles.add(ParagraphStyle(
            name='Address',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=4,
            alignment=TA_LEFT
        ))
        
        # Amount style
        self.styles.add(ParagraphStyle(
            name='Amount',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#27ae60'),
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT
        ))
    
    def _create_header(self, data: Dict[str, Any]) -> List:
        """Create document header with company info."""
        elements = []
        
        # Company name and logo
        company_name = data.get('tenant_name', 'BoxCostPro')
        elements.append(Paragraph(company_name, self.styles['CompanyName']))
        
        # Company address
        if data.get('tenant_address'):
            elements.append(Paragraph(data['tenant_address'], self.styles['Address']))
        
        if data.get('tenant_email'):
            elements.append(Paragraph(f"Email: {data['tenant_email']}", self.styles['Address']))
        
        if data.get('tenant_phone'):
            elements.append(Paragraph(f"Phone: {data['tenant_phone']}", self.styles['Address']))
        
        elements.append(Spacer(1, 0.3*inch))
        return elements
    
    def _create_document_info(self, doc_type: str, doc_number: str, doc_date: str) -> List:
        """Create document info section."""
        elements = []
        
        elements.append(Paragraph(f"{doc_type} #{doc_number}", self.styles['DocumentTitle']))
        elements.append(Paragraph(f"Date: {doc_date}", self.styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _create_customer_section(self, data: Dict[str, Any]) -> List:
        """Create bill to / ship to section."""
        elements = []
        
        elements.append(Paragraph("Bill To:", self.styles['SectionHeader']))
        elements.append(Paragraph(data.get('party_name', 'N/A'), self.styles['Normal']))
        
        if data.get('billing_address'):
            elements.append(Paragraph(data['billing_address'], self.styles['Address']))
        
        if data.get('party_email'):
            elements.append(Paragraph(f"Email: {data['party_email']}", self.styles['Address']))
        
        if data.get('party_phone'):
            elements.append(Paragraph(f"Phone: {data['party_phone']}", self.styles['Address']))
        
        elements.append(Spacer(1, 0.3*inch))
        return elements
    
    def _create_line_items_table(self, items: List[Dict[str, Any]], currency: str) -> Table:
        """Create table for line items."""
        # Table data
        data = [['Item', 'Description', 'Quantity', 'Unit Price', 'Amount']]
        
        for item in items:
            row = [
                item.get('name', ''),
                item.get('description', ''),
                str(item.get('quantity', 0)),
                f"{currency} {item.get('unit_price', 0):.2f}",
                f"{currency} {item.get('total', 0):.2f}"
            ]
            data.append(row)
        
        # Create table
        table = Table(data, colWidths=[1.5*inch, 2.5*inch, 0.8*inch, 1*inch, 1*inch])
        
        # Style table
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Quantity
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),   # Unit Price
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),   # Amount
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')])
        ]))
        
        return table
    
    def _create_totals_section(self, data: Dict[str, Any]) -> Table:
        """Create totals section."""
        currency = data.get('currency', 'USD')
        
        totals_data = []
        
        if data.get('subtotal'):
            totals_data.append(['Subtotal:', f"{currency} {data['subtotal']:.2f}"])
        
        if data.get('tax_amount'):
            totals_data.append([f"Tax ({data.get('tax_rate', 0)}%):", f"{currency} {data['tax_amount']:.2f}"])
        
        if data.get('discount_amount'):
            totals_data.append(['Discount:', f"-{currency} {data['discount_amount']:.2f}"])
        
        totals_data.append(['Total Amount:', f"{currency} {data.get('total_amount', 0):.2f}"])
        
        # Create table
        table = Table(totals_data, colWidths=[3*inch, 1.5*inch])
        
        # Style table
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -2), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#27ae60')),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        return table
    
    def _create_footer(self, data: Dict[str, Any]) -> List:
        """Create document footer."""
        elements = []
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Terms and conditions
        if data.get('terms'):
            elements.append(Paragraph("Terms & Conditions:", self.styles['SectionHeader']))
            elements.append(Paragraph(data['terms'], self.styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Notes
        if data.get('notes'):
            elements.append(Paragraph("Notes:", self.styles['SectionHeader']))
            elements.append(Paragraph(data['notes'], self.styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Footer text
        footer_text = "Thank you for your business!"
        elements.append(Paragraph(footer_text, self.styles['Normal']))
        
        return elements


class InvoicePDFGenerator(PDFGenerator):
    """Generate professional invoice PDFs."""
    
    def generate(self, invoice_data: Dict[str, Any]) -> bytes:
        """
        Generate invoice PDF.
        
        Args:
            invoice_data: Dictionary with invoice information
            
        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        elements = []
        
        # Header
        elements.extend(self._create_header(invoice_data))
        
        # Document info
        elements.extend(self._create_document_info(
            "INVOICE",
            invoice_data.get('invoice_number', 'N/A'),
            invoice_data.get('invoice_date', datetime.utcnow().strftime('%Y-%m-%d'))
        ))
        
        # Due date
        if invoice_data.get('due_date'):
            elements.append(Paragraph(
                f"<b>Due Date:</b> {invoice_data['due_date']}", 
                self.styles['Normal']
            ))
            elements.append(Spacer(1, 0.2*inch))
        
        # Customer section
        elements.extend(self._create_customer_section(invoice_data))
        
        # Line items
        if invoice_data.get('items'):
            elements.append(self._create_line_items_table(
                invoice_data['items'],
                invoice_data.get('currency', 'USD')
            ))
            elements.append(Spacer(1, 0.3*inch))
        
        # Totals
        totals_table = self._create_totals_section(invoice_data)
        elements.append(totals_table)
        
        # Payment info
        if invoice_data.get('payment_status'):
            elements.append(Spacer(1, 0.2*inch))
            status_color = colors.HexColor('#27ae60') if invoice_data['payment_status'] == 'PAID' else colors.HexColor('#e74c3c')
            status_style = ParagraphStyle(
                'PaymentStatus',
                parent=self.styles['Normal'],
                fontSize=12,
                textColor=status_color,
                fontName='Helvetica-Bold'
            )
            elements.append(Paragraph(
                f"Payment Status: {invoice_data['payment_status']}",
                status_style
            ))
        
        # Footer
        elements.extend(self._create_footer(invoice_data))
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Generated invoice PDF: {invoice_data.get('invoice_number')}")
        return pdf_bytes


class QuotePDFGenerator(PDFGenerator):
    """Generate professional quote PDFs."""
    
    def generate(self, quote_data: Dict[str, Any]) -> bytes:
        """
        Generate quote PDF.
        
        Args:
            quote_data: Dictionary with quote information
            
        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        elements = []
        
        # Header
        elements.extend(self._create_header(quote_data))
        
        # Document info
        elements.extend(self._create_document_info(
            "QUOTE",
            quote_data.get('quote_number', 'N/A'),
            quote_data.get('quote_date', datetime.utcnow().strftime('%Y-%m-%d'))
        ))
        
        # Valid until
        if quote_data.get('valid_until'):
            elements.append(Paragraph(
                f"<b>Valid Until:</b> {quote_data['valid_until']}", 
                self.styles['Normal']
            ))
            elements.append(Spacer(1, 0.2*inch))
        
        # Customer section
        elements.extend(self._create_customer_section(quote_data))
        
        # Line items
        if quote_data.get('items'):
            elements.append(self._create_line_items_table(
                quote_data['items'],
                quote_data.get('currency', 'USD')
            ))
            elements.append(Spacer(1, 0.3*inch))
        
        # Totals
        totals_table = self._create_totals_section(quote_data)
        elements.append(totals_table)
        
        # Quote status
        if quote_data.get('status'):
            elements.append(Spacer(1, 0.2*inch))
            status_colors_map = {
                'ACCEPTED': colors.HexColor('#27ae60'),
                'PENDING': colors.HexColor('#f39c12'),
                'REJECTED': colors.HexColor('#e74c3c')
            }
            status_color = status_colors_map.get(quote_data['status'], colors.black)
            status_style = ParagraphStyle(
                'QuoteStatus',
                parent=self.styles['Normal'],
                fontSize=12,
                textColor=status_color,
                fontName='Helvetica-Bold'
            )
            elements.append(Paragraph(
                f"Quote Status: {quote_data['status']}",
                status_style
            ))
        
        # Footer
        elements.extend(self._create_footer(quote_data))
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Generated quote PDF: {quote_data.get('quote_number')}")
        return pdf_bytes


def generate_invoice_pdf(invoice_data: Dict[str, Any]) -> bytes:
    """
    Convenience function to generate invoice PDF.
    
    Args:
        invoice_data: Invoice information dictionary
        
    Returns:
        PDF as bytes
    """
    generator = InvoicePDFGenerator()
    return generator.generate(invoice_data)


def generate_quote_pdf(quote_data: Dict[str, Any]) -> bytes:
    """
    Convenience function to generate quote PDF.
    
    Args:
        quote_data: Quote information dictionary
        
    Returns:
        PDF as bytes
    """
    generator = QuotePDFGenerator()
    return generator.generate(quote_data)
