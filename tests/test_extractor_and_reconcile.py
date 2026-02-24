from decimal import Decimal

from invoice_audit.extractor import HybridExtractor
from invoice_audit.reconcile import ContractRate, reconcile_invoice


def test_pipeline_flags_overcharge_and_gst_mismatch():
    raw_text = """
Vendor: FastLogistics
Invoice Number: FL-2024-0099
Invoice Date: 10-07-2024
PO No: PO-55
Currency: INR
freight lane a 10 1300 13000 GST 12% HSN 9965
unknown surcharge 1 500 500 GST 18% HSN 9999
Subtotal: 13500
GST Total: 1620
Grand Total: 15120
"""
    invoice = HybridExtractor().parse("invoice.pdf", raw_text)

    contracts = [
        ContractRate("FastLogistics", "freight lane a", Decimal("1200"), Decimal("18"), "9965"),
    ]
    findings = reconcile_invoice(invoice, contracts, [], set())

    issue_types = {f.issue_type for f in findings}
    assert "rate_overcharge" in issue_types
    assert "gst_mismatch" in issue_types
    assert "mystery_surcharge" in issue_types
