"""PDF generation service for invoices and quotes."""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, PageBreak, Image
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class InvoicePDFGenerator:
    """Generate GST-compliant invoice PDFs."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        
        # Custom styles
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2196F3'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12
        )
    
    def generate_invoice_pdf(self, invoice_data: Dict) -> bytes:
        """
        Generate GST-compliant invoice PDF.
        
        Args:
            invoice_data: Invoice data dictionary
            
        Returns:
            bytes: PDF file content
        """
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch
            )
            
            elements = []
            
            # Header - Invoice Title
            title = Paragraph("<b>TAX INVOICE</b>", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.2*inch))
            
            # Invoice Number and Date
            info_data = [
                ['Invoice No:', invoice_data['invoice_number'], 'Date:', invoice_data['invoice_date']],
                ['Due Date:', invoice_data.get('due_date', 'Upon receipt'), '', '']
            ]
            info_table = Table(info_data, colWidths=[1.5*inch, 2*inch, 1*inch, 1.5*inch])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Seller and Buyer Details
            details_data = [
                [Paragraph('<b>Seller Details:</b>', self.heading_style), 
                 Paragraph('<b>Buyer Details:</b>', self.heading_style)],
                [
                    Paragraph(f"<b>{invoice_data['seller_name']}</b><br/>{invoice_data['seller_address']}", self.styles['Normal']),
                    Paragraph(f"<b>{invoice_data['buyer_name']}</b><br/>{invoice_data['buyer_address']}", self.styles['Normal'])
                ],
                [
                    Paragraph(f"<b>GSTIN:</b> {invoice_data.get('seller_gst', 'N/A')}<br/><b>PAN:</b> {invoice_data.get('seller_pan', 'N/A')}", self.styles['Normal']),
                    Paragraph(f"<b>GSTIN:</b> {invoice_data.get('buyer_gst', 'N/A')}<br/><b>PAN:</b> {invoice_data.get('buyer_pan', 'N/A')}", self.styles['Normal'])
                ]
            ]
            
            details_table = Table(details_data, colWidths=[3.5*inch, 3.5*inch])
            details_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('BOX', (0, 0), (-1, -1), 1, colors.grey),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.grey),
            ]))
            elements.append(details_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Line Items (if available)
            if 'items' in invoice_data and invoice_data['items']:
                items_heading = Paragraph('<b>Items:</b>', self.heading_style)
                elements.append(items_heading)
                
                items_data = [['#', 'Description', 'Quantity', 'Rate', 'Amount']]
                for idx, item in enumerate(invoice_data['items'], 1):
                    items_data.append([
                        str(idx),
                        item['description'],
                        str(item['quantity']),
                        f"₹{item['rate']}",
                        f"₹{item['amount']}"
                    ])
                
                items_table = Table(items_data, colWidths=[0.5*inch, 3*inch, 1*inch, 1.25*inch, 1.25*inch])
                items_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E3F2FD')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                elements.append(items_table)
                elements.append(Spacer(1, 0.2*inch))
            
            # GST Breakdown
            gst_heading = Paragraph('<b>Tax Breakdown:</b>', self.heading_style)
            elements.append(gst_heading)
            
            gst_data = [
                ['Subtotal:', f"₹{invoice_data['subtotal']:.2f}"],
            ]
            
            # Add GST components
            if invoice_data.get('cgst', 0) > 0:
                gst_data.append(['CGST:', f"₹{invoice_data['cgst']:.2f}"])
            if invoice_data.get('sgst', 0) > 0:
                gst_data.append(['SGST:', f"₹{invoice_data['sgst']:.2f}"])
            if invoice_data.get('igst', 0) > 0:
                gst_data.append(['IGST:', f"₹{invoice_data['igst']:.2f}"])
            
            gst_data.extend([
                ['<b>Total GST:</b>', f"<b>₹{invoice_data['total_gst']:.2f}</b>"],
                ['', ''],
                ['<b>Total Amount:</b>', f"<b>₹{invoice_data['total_amount']:.2f}</b>"]
            ])
            
            # Convert to Paragraphs for bold text
            gst_data_formatted = []
            for row in gst_data:
                gst_data_formatted.append([
                    Paragraph(row[0], self.styles['Normal']),
                    Paragraph(row[1], self.styles['Normal'])
                ])
            
            gst_table = Table(gst_data_formatted, colWidths=[5*inch, 2*inch])
            gst_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -2), 6),
                ('TOPPADDING', (0, -1), (-1, -1), 12),
                ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#2196F3')),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E3F2FD')),
            ]))
            elements.append(gst_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Terms and Notes
            if invoice_data.get('terms'):
                terms_heading = Paragraph('<b>Terms & Conditions:</b>', self.heading_style)
                elements.append(terms_heading)
                terms_text = Paragraph(invoice_data['terms'], self.styles['Normal'])
                elements.append(terms_text)
                elements.append(Spacer(1, 0.2*inch))
            
            if invoice_data.get('notes'):
                notes_heading = Paragraph('<b>Notes:</b>', self.heading_style)
                elements.append(notes_heading)
                notes_text = Paragraph(invoice_data['notes'], self.styles['Normal'])
                elements.append(notes_text)
            
            # Footer
            elements.append(Spacer(1, 0.5*inch))
            footer = Paragraph(
                "<i>This is a computer-generated invoice and does not require a signature.</i>",
                ParagraphStyle('Footer', parent=self.styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
            )
            elements.append(footer)
            
            # Build PDF
            doc.build(elements)
            
            # Get PDF bytes
            buffer.seek(0)
            pdf_bytes = buffer.read()
            buffer.close()
            
            logger.info(f"Generated invoice PDF for {invoice_data['invoice_number']}")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Failed to generate invoice PDF: {str(e)}")
            raise


class QuotePDFGenerator:
    """Generate quote/estimate PDFs."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
    
    def generate_quote_pdf(self, quote_data: Dict) -> bytes:
        """
        Generate quote PDF.
        
        Args:
            quote_data: Quote data dictionary
            
        Returns:
            bytes: PDF file content
        """
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = self.styles
            
            # Title
            title = Paragraph(
                f"<b>QUOTATION</b><br/>#{quote_data['quote_number']}",
                ParagraphStyle('QuoteTitle', parent=styles['Title'], fontSize=20, alignment=TA_CENTER)
            )
            elements.append(title)
            elements.append(Spacer(1, 0.3*inch))
            
            # Company and Customer Info
            info_data = [
                ['Date:', quote_data['created_at']],
                ['Valid Until:', quote_data.get('valid_until', 'N/A')],
                ['Customer:', quote_data.get('customer_name', 'N/A')],
            ]
            
            info_table = Table(info_data, colWidths=[2*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Quote Items
            items_heading = Paragraph('<b>Items:</b>', styles['Heading2'])
            elements.append(items_heading)
            
            items_data = [['Box Specification', 'Quantity', 'Unit Cost', 'Total']]
            
            for item in quote_data.get('items', []):
                spec = f"{item['length']}x{item['width']}x{item['height']} - {item['bf_type']}"
                items_data.append([
                    spec,
                    str(item['quantity']),
                    f"₹{item['unit_cost']:.2f}",
                    f"₹{item['total_cost']:.2f}"
                ])
            
            items_table = Table(items_data, colWidths=[3*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            items_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(items_table)
            elements.append(Spacer(1, 0.2*inch))
            
            # Total
            total_data = [
                ['<b>Total Amount:</b>', f"<b>₹{quote_data['total_amount']:.2f}</b>"]
            ]
            total_table = Table(total_data, colWidths=[5.5*inch, 1.5*inch])
            total_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 14),
                ('LINEABOVE', (0, 0), (-1, -1), 2, colors.black),
            ]))
            elements.append(total_table)
            
            # Build PDF
            doc.build(elements)
            
            buffer.seek(0)
            pdf_bytes = buffer.read()
            buffer.close()
            
            logger.info(f"Generated quote PDF for {quote_data['quote_number']}")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Failed to generate quote PDF: {str(e)}")
            raise


# Singleton instances
invoice_pdf_generator = InvoicePDFGenerator()
quote_pdf_generator = QuotePDFGenerator()
