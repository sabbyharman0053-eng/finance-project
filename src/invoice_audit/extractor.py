from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from .schemas import InvoiceRecord, LineItem


class LLMExtractor(Protocol):
    def normalize_invoice(self, raw_text: str, draft: InvoiceRecord) -> InvoiceRecord:
        """Optional hook for LLM-assisted extraction refinement."""


class HybridExtractor:
    def __init__(self, llm_extractor: LLMExtractor | None = None) -> None:
        self.llm_extractor = llm_extractor

    def parse(self, source_file: str, raw_text: str) -> InvoiceRecord:
        vendor = _search(raw_text, [r"Vendor\s*[:\-]\s*(.+)", r"Supplier\s*[:\-]\s*(.+)"])
        invoice_no = _search(raw_text, [r"Invoice\s*(?:No|#|Number)\s*[:\-]\s*([A-Z0-9\-/]+)"])
        invoice_date = _parse_date(_search(raw_text, [r"Invoice\s*Date\s*[:\-]\s*([0-9\-/]+)"]))
        contract_ref = _search(raw_text, [r"(?:PO|Contract)\s*(?:No|Ref)?\s*[:\-]\s*([A-Z0-9\-/]+)"])
        currency = _search(raw_text, [r"Currency\s*[:\-]\s*([A-Z]{3})"]) or "INR"
        subtotal = _parse_decimal(_search(raw_text, [r"Subtotal\s*[:\-]\s*([0-9,]+\.?[0-9]*)"]))
        tax_total = _parse_decimal(_search(raw_text, [r"(?:Tax|GST)\s*(?:Total)?\s*[:\-]\s*([0-9,]+\.?[0-9]*)"]))
        grand_total = _parse_decimal(_search(raw_text, [r"(?:Grand\s*Total|Total\s*Amount)\s*[:\-]\s*([0-9,]+\.?[0-9]*)"]))

        line_items = _parse_line_items(raw_text)
        confidence = 0.6 + 0.05 * sum(
            value is not None for value in [vendor, invoice_no, invoice_date, subtotal, tax_total, grand_total]
        )

        draft = InvoiceRecord(
            source_file=source_file,
            vendor_name=vendor,
            invoice_number=invoice_no,
            invoice_date=invoice_date,
            contract_ref=contract_ref,
            currency=currency,
            subtotal=subtotal,
            tax_total=tax_total,
            grand_total=grand_total,
            line_items=line_items,
            extraction_confidence=min(confidence, 0.95),
        )

        if self.llm_extractor:
            return self.llm_extractor.normalize_invoice(raw_text, draft)
        return draft


LINE_PATTERN = re.compile(
    r"^\s*(?P<desc>[A-Za-z0-9 ._\-/]+)\s+"
    r"(?P<qty>[0-9]+(?:\.[0-9]+)?)\s+"
    r"(?P<rate>[0-9]+(?:\.[0-9]+)?)\s+"
    r"(?P<amt>[0-9]+(?:\.[0-9]+)?)"
    r"(?:\s+GST\s*(?P<gst>[0-9]+(?:\.[0-9]+)?)%)?"
    r"(?:\s+HSN\s*(?P<hsn>[A-Z0-9]+))?\s*$",
    flags=re.IGNORECASE,
)


def _parse_line_items(raw_text: str) -> list[LineItem]:
    rows: list[LineItem] = []
    for line in raw_text.splitlines():
        match = LINE_PATTERN.match(line)
        if not match:
            continue
        rows.append(
            LineItem(
                description=match.group("desc").strip(),
                quantity=Decimal(match.group("qty")),
                unit_rate=Decimal(match.group("rate")),
                amount=Decimal(match.group("amt")),
                gst_rate=_parse_decimal(match.group("gst")),
                hsn_code=match.group("hsn"),
                item_type="surcharge" if "surcharge" in line.lower() else "goods_or_service",
            )
        )
    return rows


def _search(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _parse_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value.replace(",", "").strip())
    except InvalidOperation:
        return None


def _parse_date(value: str | None):
    if not value:
        return None
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None
