from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class LineItem:
    description: str
    quantity: Decimal
    unit_rate: Decimal
    amount: Decimal
    hsn_code: str | None = None
    gst_rate: Decimal | None = None
    item_type: str = "goods_or_service"


@dataclass
class InvoiceRecord:
    source_file: str
    vendor_name: str | None
    invoice_number: str | None
    invoice_date: date | None
    contract_ref: str | None
    currency: str | None
    subtotal: Decimal | None
    tax_total: Decimal | None
    grand_total: Decimal | None
    line_items: list[LineItem] = field(default_factory=list)
    extraction_confidence: float = 0.0


@dataclass
class ContractRate:
    vendor_name: str
    item_key: str
    unit_rate: Decimal
    expected_gst_rate: Decimal | None
    expected_hsn_code: str | None = None


@dataclass
class AuditFinding:
    source_file: str
    invoice_number: str | None
    vendor_name: str | None
    issue_type: str
    severity: str
    amount_impact: Decimal
    message: str
