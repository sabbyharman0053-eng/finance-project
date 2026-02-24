from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .agents import InvoiceAuditApp

app = typer.Typer(help="Invoice intelligence and audit CLI")
console = Console()


@app.command("run")
def run_pipeline(
    invoices_dir: Path = typer.Option(..., help="Directory containing invoices (pdf/images)"),
    contracts_file: Path = typer.Option(..., help="CSV with contract/rate card data"),
    history_file: Path = typer.Option(..., help="CSV with historical invoice data"),
    output_dir: Path = typer.Option(Path("out"), help="Output directory"),
) -> None:
    app_runner = InvoiceAuditApp()
    try:
        context = app_runner.run(invoices_dir, contracts_file, history_file, output_dir)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    console.print(
        f"[green]Processed {len(context.invoices)} invoices. Findings: {len(context.findings)}. Output: {output_dir}"
    )


if __name__ == "__main__":
    app()
