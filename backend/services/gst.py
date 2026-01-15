"""GST calculation utilities."""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Tuple


class GSTCalculator:
    """GST calculation service for Indian tax system."""
    
    @staticmethod
    def calculate_gst(
        amount: Decimal,
        gst_rate: Decimal,
        is_inter_state: bool = False
    ) -> Dict[str, Decimal]:
        """
        Calculate GST breakdown.
        
        Args:
            amount: Base amount (subtotal)
            gst_rate: GST rate (e.g., 5.00 for 5%)
            is_inter_state: If True, apply IGST; otherwise CGST+SGST
            
        Returns:
            dict: GST breakdown with cgst, sgst, igst, total_gst, and total_amount
        """
        gst_multiplier = gst_rate / Decimal("100")
        total_gst = (amount * gst_multiplier).quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        if is_inter_state:
            # Inter-state: Apply IGST (full GST rate)
            return {
                "cgst": Decimal("0"),
                "sgst": Decimal("0"),
                "igst": total_gst,
                "total_gst": total_gst,
                "total_amount": amount + total_gst
            }
        else:
            # Intra-state: Split into CGST and SGST (half each)
            cgst = (total_gst / 2).quantize(Decimal("0.01"), ROUND_HALF_UP)
            sgst = total_gst - cgst  # Ensure no rounding errors
            
            return {
                "cgst": cgst,
                "sgst": sgst,
                "igst": Decimal("0"),
                "total_gst": total_gst,
                "total_amount": amount + total_gst
            }
    
    @staticmethod
    def determine_inter_state(seller_gst: str, buyer_gst: str) -> bool:
        """
        Determine if transaction is inter-state based on GST numbers.
        GST format: First 2 digits are state code.
        
        Args:
            seller_gst: Seller's GSTIN
            buyer_gst: Buyer's GSTIN
            
        Returns:
            bool: True if inter-state transaction
        """
        if not seller_gst or not buyer_gst:
            return False
        
        if len(seller_gst) < 2 or len(buyer_gst) < 2:
            return False
        
        seller_state = seller_gst[:2]
        buyer_state = buyer_gst[:2]
        
        return seller_state != buyer_state
    
    @staticmethod
    def validate_gstin(gstin: str) -> bool:
        """
        Validate GSTIN format (basic validation).
        Format: 22AAAAA0000A1Z5 (15 characters)
        
        Args:
            gstin: GSTIN to validate
            
        Returns:
            bool: True if valid format
        """
        if not gstin or len(gstin) != 15:
            return False
        
        # First 2: State code (01-37)
        state_code = gstin[:2]
        if not state_code.isdigit() or not (1 <= int(state_code) <= 37):
            return False
        
        # Next 10: PAN number
        pan = gstin[2:12]
        if not (pan[:5].isalpha() and pan[5:9].isdigit() and pan[9].isalpha()):
            return False
        
        # Next 1: Entity number (1-9, A-Z)
        entity_num = gstin[12]
        if not entity_num.isalnum():
            return False
        
        # Next 1: Default 'Z'
        # Next 1: Checksum digit
        
        return True
    
    @staticmethod
    def extract_state_code(gstin: str) -> str:
        """Extract state code from GSTIN."""
        if gstin and len(gstin) >= 2:
            return gstin[:2]
        return ""


class InvoiceNumberGenerator:
    """Generate financial year-based invoice numbers."""
    
    @staticmethod
    def get_financial_year(date: object = None) -> str:
        """
        Get financial year for a date.
        Indian FY: April to March
        
        Args:
            date: Date (defaults to current)
            
        Returns:
            str: Financial year (e.g., "2024-25")
        """
        from datetime import datetime
        date = date or datetime.now()
        
        if date.month >= 4:  # April to December
            return f"{date.year}-{str(date.year + 1)[-2:]}"
        else:  # January to March
            return f"{date.year - 1}-{str(date.year)[-2:]}"
    
    @staticmethod
    def generate_invoice_number(
        prefix: str,
        sequence: int,
        financial_year: str = None
    ) -> str:
        """
        Generate invoice number.
        Format: PREFIX/FY/SEQUENCE
        
        Args:
            prefix: Company prefix (e.g., "BOX")
            sequence: Sequential number
            financial_year: FY string (auto-calculated if None)
            
        Returns:
            str: Invoice number (e.g., "BOX/2024-25/0001")
        """
        from datetime import datetime
        
        if not financial_year:
            financial_year = InvoiceNumberGenerator.get_financial_year()
        
        return f"{prefix}/{financial_year}/{sequence:04d}"


# Singleton instances
gst_calculator = GSTCalculator()
invoice_number_generator = InvoiceNumberGenerator()
