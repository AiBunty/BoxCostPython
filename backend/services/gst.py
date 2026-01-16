"""GST calculation utilities."""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Tuple


class GSTCalculator:
    """GST calculation service for Indian tax system."""

    VALID_STATE_CODES = {
        '01', '02', '03', '04', '05', '06', '07', '08', '09', '10',
        '11', '12', '13', '14', '15', '16', '17', '18', '19', '20',
        '21', '22', '23', '24', '26', '27', '29', '30', '31', '32',
        '33', '34', '35', '36', '37', '38', '97', '99',
    }

    @staticmethod
    def calculate_gst(
        amount: Decimal,
        gst_rate: Decimal = Decimal("18.0"),
        is_inter_state: bool = False,
        discount_amount: Decimal = Decimal("0")
    ) -> Dict[str, Decimal]:
        """Calculate GST breakdown mirroring TS logic (discount-before-tax, rounded per field)."""
        taxable_value = (amount - discount_amount).quantize(Decimal("0.01"), ROUND_HALF_UP)
        if taxable_value < 0:
            taxable_value = Decimal("0.00")

        gst_multiplier = gst_rate / Decimal("100")
        total_gst = (taxable_value * gst_multiplier).quantize(Decimal("0.01"), ROUND_HALF_UP)

        if is_inter_state:
            return {
                "cgst": Decimal("0"),
                "sgst": Decimal("0"),
                "igst": total_gst,
                "total_gst": total_gst,
                "total_amount": taxable_value + total_gst,
            }

        cgst = (total_gst / 2).quantize(Decimal("0.01"), ROUND_HALF_UP)
        sgst = total_gst - cgst
        return {
            "cgst": cgst,
            "sgst": sgst,
            "igst": Decimal("0"),
            "total_gst": total_gst,
            "total_amount": taxable_value + total_gst,
        }

    @staticmethod
    def calculate_reverse_gst(total_amount: Decimal, gst_rate: Decimal = Decimal("18.0")) -> Decimal:
        """Extract base amount from total including GST (TS parity)."""
        base = (total_amount * Decimal("100") / (Decimal("100") + gst_rate)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        return base

    @staticmethod
    def determine_inter_state(seller_gst: str, buyer_gst: str) -> bool:
        """Determine inter-state by comparing state codes (first 2 digits)."""
        seller_state = GSTCalculator.extract_state_code(seller_gst)
        buyer_state = GSTCalculator.extract_state_code(buyer_gst)
        if not seller_state or not buyer_state:
            return False
        return seller_state != buyer_state

    @staticmethod
    def validate_gstin(gstin: str) -> bool:
        """Validate GSTIN format (15 chars, state code, PAN structure)."""
        if not gstin or len(gstin) != 15:
            return False

        state_code = gstin[:2]
        if state_code not in GSTCalculator.VALID_STATE_CODES:
            return False

        pan = gstin[2:12]
        if not (pan[:5].isalpha() and pan[5:9].isdigit() and pan[9].isalpha()):
            return False

        entity_num = gstin[12]
        if not entity_num.isalnum():
            return False

        # gstin[13] should be 'Z', gstin[14] checksum is skipped here
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
        
        return f"{prefix}/FY{financial_year}/{sequence:04d}"

    @staticmethod
    def parse_sequence(invoice_number: str) -> int:
        """Extract trailing sequence integer from an invoice number."""
        if not invoice_number:
            return 0
        parts = invoice_number.split('/')
        if not parts:
            return 0
        try:
            return int(parts[-1])
        except ValueError:
            return 0


# Singleton instances
gst_calculator = GSTCalculator()
invoice_number_generator = InvoiceNumberGenerator()
