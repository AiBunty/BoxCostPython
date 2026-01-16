import datetime
from decimal import Decimal

import pytest

from backend.services.gst import gst_calculator, invoice_number_generator


class TestInvoiceNumbering:
    def test_financial_year_boundaries(self):
        mar_31 = datetime.datetime(2025, 3, 31)
        apr_1 = datetime.datetime(2025, 4, 1)

        fy_mar = invoice_number_generator.get_financial_year(mar_31)
        fy_apr = invoice_number_generator.get_financial_year(apr_1)

        assert fy_mar == "2024-25"
        assert fy_apr == "2025-26"

    def test_sequence_and_format(self):
        num1 = invoice_number_generator.generate_invoice_number(prefix="INV", sequence=1, financial_year="2024-25")
        num2 = invoice_number_generator.generate_invoice_number(prefix="INV", sequence=42, financial_year="2024-25")
        assert num1 == "INV/FY2024-25/0001"
        assert num2 == "INV/FY2024-25/0042"
        assert invoice_number_generator.parse_sequence(num1) == 1
        assert invoice_number_generator.parse_sequence(num2) == 42


class TestGSTCalculator:
    def test_intra_state_no_discount(self):
        breakdown = gst_calculator.calculate_gst(
            amount=Decimal("1000"),
            gst_rate=Decimal("18"),
            is_inter_state=False,
            discount_amount=Decimal("0"),
        )
        assert breakdown["cgst"] == Decimal("90.00")
        assert breakdown["sgst"] == Decimal("90.00")
        assert breakdown["igst"] == Decimal("0")
        assert breakdown["total_gst"] == Decimal("180.00")
        assert breakdown["total_amount"] == Decimal("1180.00")

    def test_inter_state_with_discount(self):
        breakdown = gst_calculator.calculate_gst(
            amount=Decimal("1000"),
            gst_rate=Decimal("18"),
            is_inter_state=True,
            discount_amount=Decimal("200"),
        )
        assert breakdown["cgst"] == Decimal("0")
        assert breakdown["sgst"] == Decimal("0")
        assert breakdown["igst"] == Decimal("144.00")  # 800 * 18%
        assert breakdown["total_gst"] == Decimal("144.00")
        assert breakdown["total_amount"] == Decimal("944.00")

    def test_reverse_gst(self):
        base = gst_calculator.calculate_reverse_gst(total_amount=Decimal("1180.00"), gst_rate=Decimal("18"))
        assert base == Decimal("1000.00")

    @pytest.mark.parametrize(
        "gstin,valid",
        [
            ("27AABCU9603R1ZM", True),  # valid format/state
            ("06ABCDE1234F1Z5", True),
            ("27AABCU9603R1Z", False),   # wrong length
            ("99INVALIDGSTIN12", False),
            ("00AABCU9603R1ZM", False),  # invalid state code
        ],
    )
    def test_gstin_validation(self, gstin, valid):
        assert gst_calculator.validate_gstin(gstin) is valid

    def test_inter_state_detection(self):
        assert gst_calculator.determine_inter_state("27AABCU9603R1ZM", "06ABCDE1234F1Z5") is True
        assert gst_calculator.determine_inter_state("27AABCU9603R1ZM", "27ABCDE1234F1Z5") is False
        assert gst_calculator.determine_inter_state("", "06ABCDE1234F1Z5") is False
