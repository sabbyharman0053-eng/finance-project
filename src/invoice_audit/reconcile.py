from __future__ import annotations

import csv
from collections import defaultdict
from decimal import Decimal

from .schemas import AuditFinding, ContractRate, InvoiceRecord


def load_contract_rates(path: str) -> list[ContractRate]:
    rates: list[ContractRate] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rates.append(
                ContractRate(
                    vendor_name=row["vendor_name"].strip(),
                    item_key=row["item_key"].strip().lower(),
                    unit_rate=Decimal(str(row["unit_rate"])),
                    expected_gst_rate=Decimal(str(row["expected_gst_rate"])) if row.get("expected_gst_rate") else None,
                    expected_hsn_code=row["expected_hsn_code"].strip() if row.get("expected_hsn_code") else None,
                )
            )
    return rates


def load_history(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def reconcile_invoice(
    invoice: InvoiceRecord,
    contracts: list[ContractRate],
    history: list[dict[str, str]],
    seen_invoice_ids: set[str],
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    contract_index = {(c.vendor_name.lower(), c.item_key): c for c in contracts}

    invoice_key = f"{invoice.vendor_name}|{invoice.invoice_number}".lower()
    if invoice_key in seen_invoice_ids or _exists_in_history(invoice, history):
        findings.append(
            _finding(invoice, "duplicate_invoice", "high", Decimal("0"), "Invoice appears duplicated in processed or historical data")
        )
    seen_invoice_ids.add(invoice_key)

    computed_subtotal = Decimal("0")
    for item in invoice.line_items:
        computed_subtotal += item.amount
        item_key = item.description.lower().strip()
        contract = contract_index.get(((invoice.vendor_name or "").lower(), item_key))

        if contract:
            if item.unit_rate > contract.unit_rate:
                overcharge = (item.unit_rate - contract.unit_rate) * item.quantity
                findings.append(
                    _finding(
                        invoice,
                        "rate_overcharge",
                        "high",
                        overcharge,
                        f"{item.description}: billed rate {item.unit_rate} exceeds contract rate {contract.unit_rate}",
                    )
                )
            if contract.expected_gst_rate is not None and item.gst_rate is not None and item.gst_rate != contract.expected_gst_rate:
                findings.append(
                    _finding(
                        invoice,
                        "gst_mismatch",
                        "medium",
                        Decimal("0"),
                        f"{item.description}: GST {item.gst_rate}% differs from expected {contract.expected_gst_rate}%",
                    )
                )
            if contract.expected_hsn_code and item.hsn_code and item.hsn_code != contract.expected_hsn_code:
                findings.append(
                    _finding(
                        invoice,
                        "hsn_mismatch",
                        "medium",
                        Decimal("0"),
                        f"{item.description}: HSN {item.hsn_code} differs from expected {contract.expected_hsn_code}",
                    )
                )
        elif item.item_type == "surcharge":
            findings.append(
                _finding(
                    invoice,
                    "mystery_surcharge",
                    "medium",
                    item.amount,
                    f"Unmapped surcharge line item detected: {item.description}",
                )
            )

    if invoice.subtotal is not None and computed_subtotal != invoice.subtotal:
        findings.append(
            _finding(
                invoice,
                "calculation_error",
                "high",
                abs(computed_subtotal - invoice.subtotal),
                f"Subtotal mismatch: computed {computed_subtotal} vs invoice {invoice.subtotal}",
            )
        )

    return findings


def summarize_findings(invoices: list[InvoiceRecord], findings: list[AuditFinding]) -> list[dict[str, float | int | str]]:
    by_vendor = defaultdict(lambda: {"billed_total": Decimal("0"), "impact_total": Decimal("0"), "issues": 0})
    for inv in invoices:
        if inv.grand_total:
            by_vendor[inv.vendor_name or "Unknown"]["billed_total"] += inv.grand_total
    for finding in findings:
        vendor = finding.vendor_name or "Unknown"
        by_vendor[vendor]["impact_total"] += finding.amount_impact
        by_vendor[vendor]["issues"] += 1

    rows = []
    for vendor, stats in by_vendor.items():
        rows.append(
            {
                "vendor": vendor,
                "billed_total": float(stats["billed_total"]),
                "potential_recovery": float(stats["impact_total"]),
                "issue_count": stats["issues"],
            }
        )
    return sorted(rows, key=lambda x: x["potential_recovery"], reverse=True)


def _exists_in_history(invoice: InvoiceRecord, history: list[dict[str, str]]) -> bool:
    if not invoice.invoice_number or not invoice.vendor_name:
        return False
    for row in history:
        if (
            str(row.get("invoice_number", "")).lower() == invoice.invoice_number.lower()
            and str(row.get("vendor_name", "")).lower() == invoice.vendor_name.lower()
        ):
            return True
    return False


def _finding(invoice: InvoiceRecord, issue_type: str, severity: str, amount_impact: Decimal, message: str) -> AuditFinding:
    return AuditFinding(
        source_file=invoice.source_file,
        invoice_number=invoice.invoice_number,
        vendor_name=invoice.vendor_name,
        issue_type=issue_type,
        severity=severity,
        amount_impact=amount_impact,
        message=message,
    )
