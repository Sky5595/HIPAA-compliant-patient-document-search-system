"""
CLI — main entry point for hipaa-llm-wiki.
Usage: python main.py [command] [options]
"""
from __future__ import annotations
import click
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()


@click.group()
def cli():
    """
    \b
    HIPAA-LLM-Wiki: Patient Knowledge Base CLI
    ==========================================
    Karpathy's LLM Wiki pattern — adapted for clinical use.
    All processing is LOCAL. No PHI leaves your machine.
    """


# ── INGEST ────────────────────────────────────────────────────────────────────
@cli.command()
@click.argument("filepath")
@click.argument("patient_id")
@click.option("--user", "-u", required=True, help="Your username (from config/roles.yaml)")
@click.option("--type", "-t", "doc_type",
              default="clinical_note",
              type=click.Choice(["clinical_note","lab_report","discharge_summary","imaging_report","prescription"]),
              help="Document type hint for the LLM")
def ingest(filepath, patient_id, user, doc_type):
    """Ingest a raw document into the patient wiki.

    \b
    Examples:
      python main.py ingest raw/PT-0001/discharge_note.pdf PT-0001 -u dr_smith
      python main.py ingest raw/PT-0001/lab_results.txt PT-0001 -u dr_smith -t lab_report
    """
    from src.ingest import ingest_document
    console.print(Panel(f"[bold cyan]Ingesting:[/] {filepath} → {patient_id}", title="🏥 Ingest"))
    try:
        result = ingest_document(filepath, patient_id, user, doc_type)
        console.print(f"[green]✓ Success[/] — Wiki pages updated: {result['pages_updated']}")
    except PermissionError as e:
        console.print(f"[red]✗ Access Denied:[/] {e}")
    except Exception as e:
        console.print(f"[red]✗ Error:[/] {e}")
        raise


# ── QUERY ─────────────────────────────────────────────────────────────────────
@cli.command()
@click.argument("question")
@click.argument("patient_id")
@click.option("--user", "-u", required=True, help="Your username")
@click.option("--save", is_flag=True, default=False, help="Save answer back to wiki")
def query(question, patient_id, user, save):
    """Ask a clinical question about a patient.

    \b
    Examples:
      python main.py query "Has eGFR been declining?" PT-0001 -u dr_smith
      python main.py query "List all current medications" PT-0001 -u nurse_jones --save
    """
    from src.query import query_patient
    console.print(Panel(f"[bold yellow]Q:[/] {question}\n[dim]Patient: {patient_id}[/]", title="🔍 Query"))
    try:
        result = query_patient(question, patient_id, user, save_answer=save)
        console.print(Markdown(result["answer"]))
        console.print(f"\n[dim]Sources: {result['sources_used']}[/]")
        if save:
            console.print("[green]Answer saved to wiki.[/]")
    except PermissionError as e:
        console.print(f"[red]✗ Access Denied:[/] {e}")
    except Exception as e:
        console.print(f"[red]✗ Error:[/] {e}")
        raise


# ── LINT ──────────────────────────────────────────────────────────────────────
@cli.command()
@click.argument("patient_id", required=False)
@click.option("--user", "-u", required=True, help="Your username")
@click.option("--all-patients", is_flag=True, default=False, help="Lint all accessible patients")
def lint(patient_id, user, all_patients):
    """Run a clinical safety lint scan on a patient wiki.

    \b
    Examples:
      python main.py lint PT-0001 -u dr_smith
      python main.py lint --all-patients -u hia_admin
    """
    from src.lint import lint_patient, lint_all_patients
    try:
        if all_patients:
            results = lint_all_patients(user)
            for r in results:
                console.print(f"[cyan]{r['patient_id']}[/] — Issues: {r['issues_found']} | Report: {r['report_path']}")
        else:
            if not patient_id:
                console.print("[red]Provide a patient_id or use --all-patients[/]")
                return
            console.print(Panel(f"[bold magenta]Linting:[/] {patient_id}", title="🩺 Lint"))
            result = lint_patient(patient_id, user)
            console.print(Markdown(result["report_markdown"]))
            console.print(f"\n[dim]Report saved: {result['report_path']}[/]")
    except PermissionError as e:
        console.print(f"[red]✗ Access Denied:[/] {e}")


# ── AUDIT LOG ─────────────────────────────────────────────────────────────────
@cli.command("audit-log")
@click.option("--patient", "-p", default=None, help="Filter by patient_id")
@click.option("--tail", "-n", default=20, help="Last N entries (default 20)")
@click.option("--user", "-u", required=True, help="Your username")
def audit_log_cmd(patient, tail, user):
    """View the HIPAA audit log.

    \b
    Examples:
      python main.py audit-log -u hia_admin
      python main.py audit-log -p PT-0001 -u hia_admin
    """
    from src.audit import tail_audit_log, search_audit_log
    from src.rbac import require_permission
    require_permission(user, "read:audit_log")

    records = search_audit_log(patient) if patient else tail_audit_log(tail)

    table = Table(title="HIPAA Audit Log", show_lines=True)
    table.add_column("Timestamp", style="dim", width=25)
    table.add_column("Action", style="cyan")
    table.add_column("User", style="green")
    table.add_column("Patient", style="yellow")
    table.add_column("Document")
    for r in records:
        table.add_row(r["ts"], r["action"], r["user"], r["patient_id"], r["document"])
    console.print(table)


# ── USERS ─────────────────────────────────────────────────────────────────────
@cli.group()
def users():
    """Manage users and roles."""


@users.command("list")
@click.option("--user", "-u", required=True)
def users_list(user):
    """List all users."""
    from src.rbac import require_permission, _load_config
    require_permission(user, "manage:users")
    cfg = _load_config()
    table = Table(title="Users")
    table.add_column("Username")
    table.add_column("Role")
    table.add_column("Patients")
    table.add_column("Active")
    for u in cfg.get("users", []):
        table.add_row(u["username"], u["role"],
                      ", ".join(u.get("assigned_patients", [])),
                      "✓" if u.get("active") else "✗")
    console.print(table)
