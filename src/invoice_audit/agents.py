from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .extractor import HybridExtractor
from .ocr import extract_text
from .reconcile import load_contract_rates, load_history, reconcile_invoice, summarize_findings
from .reporting import write_outputs
from .schemas import AuditFinding, ContractRate, InvoiceRecord


@dataclass
class PipelineContext:
    invoices_dir: Path
    contracts_file: Path
    history_file: Path
    output_dir: Path
    invoice_files: list[Path]
    contracts: list[ContractRate]
    history: list[dict[str, str]]
    invoices: list[InvoiceRecord]
    findings: list[AuditFinding]


class InputAgent:
    """Validates and discovers input files."""

    def run(self, invoices_dir: Path, contracts_file: Path, history_file: Path, output_dir: Path) -> PipelineContext:
        invoice_files = sorted([p for p in invoices_dir.iterdir() if p.is_file()])
        if not invoice_files:
            raise ValueError("No invoice files found in invoices-dir")
        return PipelineContext(
            invoices_dir=invoices_dir,
            contracts_file=contracts_file,
            history_file=history_file,
            output_dir=output_dir,
            invoice_files=invoice_files,
            contracts=[],
            history=[],
            invoices=[],
            findings=[],
        )


class ReferenceAgent:
    """Loads contract/rate-card and historical invoice references."""

    def run(self, context: PipelineContext) -> None:
        context.contracts = load_contract_rates(str(context.contracts_file))
        context.history = load_history(str(context.history_file))


class OCRAgent:
    """Converts invoice files into raw text."""

    def run(self, file_path: Path) -> str:
        return extract_text(file_path)


class ExtractionAgent:
    """Extracts structured invoice fields and line items."""

    def __init__(self) -> None:
        self.extractor = HybridExtractor()

    def run(self, file_path: Path, raw_text: str) -> InvoiceRecord:
        return self.extractor.parse(file_path.name, raw_text)


class AuditAgent:
    """Runs contract checks, duplicate detection, and discrepancy checks."""

    def run(self, invoice: InvoiceRecord, context: PipelineContext, seen_invoice_ids: set[str]) -> list[AuditFinding]:
        return reconcile_invoice(invoice, context.contracts, context.history, seen_invoice_ids)


class ReportingAgent:
    """Builds dashboard rows and writes all report outputs."""

    def run(self, context: PipelineContext) -> list[dict[str, float | int | str]]:
        dashboard_rows = summarize_findings(context.invoices, context.findings)
        write_outputs(context.output_dir, context.invoices, context.findings, dashboard_rows)
        return dashboard_rows


class InvoiceAuditApp:
    """Agent-orchestrated app: give input files and receive audited outputs."""

    def __init__(self) -> None:
        self.input_agent = InputAgent()
        self.reference_agent = ReferenceAgent()
        self.ocr_agent = OCRAgent()
        self.extraction_agent = ExtractionAgent()
        self.audit_agent = AuditAgent()
        self.reporting_agent = ReportingAgent()

    def run(self, invoices_dir: Path, contracts_file: Path, history_file: Path, output_dir: Path) -> PipelineContext:
        context = self.input_agent.run(invoices_dir, contracts_file, history_file, output_dir)
        self.reference_agent.run(context)

        seen_invoice_ids: set[str] = set()
        for file_path in context.invoice_files:
            raw_text = self.ocr_agent.run(file_path)
            invoice = self.extraction_agent.run(file_path, raw_text)
            context.invoices.append(invoice)
            context.findings.extend(self.audit_agent.run(invoice, context, seen_invoice_ids))

        self.reporting_agent.run(context)
        return context
