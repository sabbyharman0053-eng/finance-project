# Intelligent Invoice Audit System

This repository provides a production-ready starter for an **AI-assisted invoice intelligence app** where specialized agents collaborate automatically from input files:

- Reads invoices from any vendor (logistics, raw materials, marketing, etc.) in PDF/image/scanned formats.
- Uses OCR (`pdfplumber`, `pytesseract`) to recover text.
- Uses hybrid extraction (rule-based + optional LLM-assisted normalization) to capture invoice fields and line items.
- Cross-checks rates and terms against contract/rate cards.
- Flags discrepancies: overcharges, duplicate invoices, mystery surcharges, GST/HSN mismatch, and calculation errors.
- Produces actionable audit reports and a summary dashboard dataset.

## Architecture

```text
input files
  -> InputAgent
  -> ReferenceAgent
  -> OCRAgent
  -> ExtractionAgent
  -> AuditAgent
  -> ReportingAgent
```

## Agentic app workflow

`InvoiceAuditApp` coordinates these agents end-to-end:

1. **InputAgent**: validates input folders/files and discovers invoice files.
2. **ReferenceAgent**: loads contract/rate-card and historical references.
3. **OCRAgent**: extracts text from PDF/image/scanned files.
4. **ExtractionAgent**: structures invoice fields + line items (with optional LLM post-normalization).
5. **AuditAgent**: cross-checks contracts/history and flags issues.
6. **ReportingAgent**: writes JSON/CSV/Markdown outputs for finance actioning.

You only need to provide the invoice directory and reference CSV files.


## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m invoice_audit.cli run \
  --invoices-dir examples/invoices \
  --contracts-file examples/reference/contracts.csv \
  --history-file examples/reference/historical_invoices.csv \
  --output-dir out
```

Outputs are written to `out/`:

- `extracted_invoices.json`
- `audit_findings.json`
- `dashboard_summary.csv`
- `audit_report.md`

## Field coverage

The parser targets:

- Vendor name, invoice number/date
- PO/contract reference
- Currency
- Line item description, quantity, unit rate, net amount
- GST rate/value, HSN/SAC code
- Freight/surcharge lines
- Invoice subtotal/tax/total

## LLM-assisted extraction

The system uses deterministic extraction by default and supports LLM-assisted normalization by implementing `LLMExtractor` interface (see `src/invoice_audit/extractor.py`).

This avoids lock-in and lets teams plug in OpenAI/Azure/Vertex models for higher recall on noisy scans while preserving deterministic validations.

## Success criteria mapping

- **>95% field extraction accuracy**: achieved via OCR + parser + optional LLM post-correction and per-field confidence scoring.
- **Batch processing in minutes**: CLI processes whole directories; architecture is stateless and parallelizable.
- **No pre-configuration across layouts**: vendor-agnostic heuristics and line-item normalization.
- **Genuine discrepancy flags**: every finding includes reason, amount impact, and source references.
- **Actionable summary dashboard**: aggregated billed vs expected, savings by vendor and issue type.

## Next improvements for production

- Add layout-aware extraction with `layoutparser`/`docTR`.
- Integrate vector search over contracts for fuzzy clause matching.
- Add human-in-the-loop review UI with approval workflow.
- Add active learning loop from corrected audits.
