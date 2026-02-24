from pathlib import Path

from invoice_audit.agents import InvoiceAuditApp


def test_app_runs_all_agents_and_writes_outputs(tmp_path, monkeypatch):
    invoices_dir = tmp_path / "invoices"
    invoices_dir.mkdir()
    (invoices_dir / "invoice1.pdf").write_text("dummy", encoding="utf-8")

    contracts_file = tmp_path / "contracts.csv"
    contracts_file.write_text(
        "vendor_name,item_key,unit_rate,expected_gst_rate,expected_hsn_code\n"
        "FastLogistics,freight lane a,1200,18,9965\n",
        encoding="utf-8",
    )

    history_file = tmp_path / "history.csv"
    history_file.write_text("vendor_name,invoice_number\n", encoding="utf-8")

    output_dir = tmp_path / "out"

    raw_text = """
Vendor: FastLogistics
Invoice Number: FL-2024-0100
Invoice Date: 10-07-2024
freight lane a 10 1200 12000 GST 18% HSN 9965
Subtotal: 12000
GST Total: 2160
Grand Total: 14160
"""

    monkeypatch.setattr("invoice_audit.agents.OCRAgent.run", lambda self, _: raw_text)

    context = InvoiceAuditApp().run(invoices_dir, contracts_file, history_file, output_dir)

    assert len(context.invoices) == 1
    assert (output_dir / "extracted_invoices.json").exists()
    assert (output_dir / "audit_findings.json").exists()
    assert (output_dir / "dashboard_summary.csv").exists()
    assert (output_dir / "audit_report.md").exists()
