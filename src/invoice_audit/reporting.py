from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from .schemas import AuditFinding, InvoiceRecord


def write_outputs(
    output_dir: Path,
    invoices: list[InvoiceRecord],
    findings: list[AuditFinding],
    dashboard_rows: list[dict[str, float | int | str]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "extracted_invoices.json").write_text(
        json.dumps([asdict(i) for i in invoices], default=str, indent=2), encoding="utf-8"
    )
    (output_dir / "audit_findings.json").write_text(
        json.dumps([asdict(f) for f in findings], default=str, indent=2), encoding="utf-8"
    )

    dashboard_path = output_dir / "dashboard_summary.csv"
    with dashboard_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["vendor", "billed_total", "potential_recovery", "issue_count"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in dashboard_rows:
            writer.writerow(row)

    (output_dir / "audit_report.md").write_text(_build_markdown_report(invoices, findings), encoding="utf-8")


def _build_markdown_report(invoices: list[InvoiceRecord], findings: list[AuditFinding]) -> str:
    total_billed = sum((i.grand_total or 0) for i in invoices)
    potential_recovery = sum(f.amount_impact for f in findings)
    lines = [
        "# Invoice Audit Report",
        "",
        f"- Invoices processed: **{len(invoices)}**",
        f"- Total billed: **{total_billed}**",
        f"- Findings count: **{len(findings)}**",
        f"- Potential recovery: **{potential_recovery}**",
        "",
        "## Findings",
    ]
    for f in findings:
        lines.append(
            f"- [{f.severity.upper()}] {f.issue_type} | Vendor: {f.vendor_name} | Invoice: {f.invoice_number} | Impact: {f.amount_impact} | {f.message}"
        )
    return "\n".join(lines)
