"""
Lint engine — Karpathy Phase 3.
Scans the patient wiki for clinical safety issues:
  - Drug-allergy conflicts
  - Contradictory diagnoses
  - Stale medications
  - Orphan pages
  - Missing follow-ups
Outputs a lint report to wiki/<patient_id>/lint_report_YYYY-MM-DD.md
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from src.audit import audit_log
from src.rbac import require_permission
from src.llm import call_llm


WIKI_DIR = Path("wiki")
LOG_FILE = Path("logs/log.md")


def _load_all_wiki_pages(patient_id: str) -> dict[str, str]:
    patient_wiki = WIKI_DIR / patient_id
    if not patient_wiki.exists():
        return {}
    return {
        md.name: md.read_text(encoding="utf-8")
        for md in sorted(patient_wiki.glob("*.md"))
        if not md.name.startswith("lint_report")
    }


def _append_to_log(patient_id: str, issues_count: int) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"## [{ts}] lint | {patient_id} | issues_found:{issues_count}\n\n"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(entry)


def lint_patient(patient_id: str, username: str) -> dict:
    """
    Run a full clinical safety lint scan on a patient wiki.

    Returns:
        dict with keys: patient_id, issues_found, report_path, report_markdown
    """
    require_permission(username, "lint:run", patient_id)
    audit_log("lint", username, patient_id, detail="start", include_detail=True)

    pages = _load_all_wiki_pages(patient_id)
    if not pages:
        return {
            "patient_id": patient_id,
            "issues_found": 0,
            "report_path": None,
            "report_markdown": "No wiki pages found. Run ingest first.",
        }

    wiki_dump = "\n\n---\n\n".join(
        f"### {name}\n{content}" for name, content in pages.items()
    )

    prompt = f"""You are a clinical safety auditor reviewing the wiki for patient {patient_id}.

Carefully read ALL wiki pages below and check for the following issues.
For each issue found, output a numbered item with:
- Severity: 🔴 CRITICAL | 🟡 WARNING | 🔵 INFO
- Category
- Description
- Recommendation

## Checks to Perform
1. **Drug-allergy conflicts** — any active medication in medications.md that matches an allergen in allergies_alerts.md
2. **Contradictory diagnoses** — conflicting condition statuses across visit notes (e.g., "no history of X" vs active X diagnosis)
3. **Stale medications** — medications with no renewal note in over 12 months
4. **Orphan pages** — wiki pages with no references from other pages
5. **Abnormal labs not linked** — lab values marked ⚠️ in lab_history.md that have no corresponding entry in diagnoses.md
6. **Missing follow-ups** — follow-up orders mentioned in visit notes but absent from procedures_timeline.md
7. **Incomplete cross-references** — conditions in diagnoses.md not referenced in patient_overview.md

## Wiki Content for {patient_id}
{wiki_dump[:7000]}

## Lint Report
Start your response with a summary line: "**Issues found: N**"
Then list each issue. If no issues found, say "✅ No issues found. Wiki is clinically consistent."
"""

    report_md = call_llm(prompt)

    # Count issues (rough heuristic)
    import re
    issues_count = len(re.findall(r"^\d+\.", report_md, re.MULTILINE))

    # Write report
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_filename = f"lint_report_{ts}.md"
    report_path = WIKI_DIR / patient_id / report_filename
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        f"# Lint Report — {patient_id}\n**Generated:** {ts} by {username}\n\n{report_md}\n",
        encoding="utf-8",
    )

    _append_to_log(patient_id, issues_count)
    audit_log("lint", username, patient_id, report_filename, f"issues:{issues_count}", include_detail=True)

    return {
        "patient_id": patient_id,
        "issues_found": issues_count,
        "report_path": str(report_path),
        "report_markdown": report_md,
    }


def lint_all_patients(username: str) -> list[dict]:
    """Run lint on all patients accessible to the user."""
    from src.rbac import list_accessible_patients
    results = []
    for patient_id in list_accessible_patients(username):
        result = lint_patient(patient_id, username)
        results.append(result)
    return results
