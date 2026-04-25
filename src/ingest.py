"""
Ingest pipeline — Karpathy Phase 1.
Reads a raw document, compiles/updates the patient wiki via LLM,
and appends to both audit.jsonl and log.md.
"""
from __future__ import annotations
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml

from src.audit import audit_log
from src.ocr import extract_text, get_document_metadata
from src.rbac import require_permission
from src.llm import call_llm


AGENTS_FILE = Path("AGENTS.md")
WIKI_DIR = Path("wiki")
LOG_FILE = Path("logs/log.md")


def _load_agents_schema() -> str:
    if AGENTS_FILE.exists():
        return AGENTS_FILE.read_text(encoding="utf-8")
    return ""


def _get_wiki_context(patient_id: str) -> str:
    """Read existing wiki pages for a patient to give the LLM context."""
    patient_wiki = WIKI_DIR / patient_id
    if not patient_wiki.exists():
        return "No existing wiki pages for this patient. Create fresh pages."
    pages = []
    for md_file in patient_wiki.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        pages.append(f"### Existing: {md_file.name}\n{content}")
    return "\n\n---\n\n".join(pages) if pages else "No existing wiki pages."


def _write_wiki_updates(patient_id: str, llm_response: str) -> list[str]:
    """
    Parse LLM response for wiki page blocks and write them.
    Expects the LLM to use fenced blocks:
        ```wiki:patient_overview.md
        <content>
        ```
    Returns list of updated filenames.
    """
    patient_wiki = WIKI_DIR / patient_id
    patient_wiki.mkdir(parents=True, exist_ok=True)

    updated = []
    import re
    pattern = re.compile(r"```wiki:(\S+\.md)\n([\s\S]*?)```", re.MULTILINE)
    for match in pattern.finditer(llm_response):
        filename = match.group(1)
        content = match.group(2).strip()
        out_path = patient_wiki / filename
        out_path.write_text(content + "\n", encoding="utf-8")
        updated.append(filename)

    return updated


def _append_to_log(patient_id: str, filename: str, pages_updated: list[str]) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pages_str = ", ".join(pages_updated) if pages_updated else "none"
    entry = f"## [{ts}] ingest | {patient_id} | {filename}\nPages updated: {pages_str}\n\n"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(entry)


def ingest_document(
    filepath: str | Path,
    patient_id: str,
    username: str,
    doc_type: str = "clinical_note",
) -> dict:
    """
    Ingest a raw clinical document into the patient wiki.

    Args:
        filepath:   Path to the document (PDF, TXT, image)
        patient_id: e.g. "PT-0001"
        username:   Authenticated user performing the ingest
        doc_type:   Hint to the LLM: clinical_note | lab_report | discharge_summary | imaging_report

    Returns:
        dict with keys: patient_id, filename, pages_updated, status
    """
    require_permission(username, "ingest:all", patient_id)
    audit_log("ingest", username, patient_id, str(Path(filepath).name), "start")

    # 1. Extract text
    raw_text = extract_text(filepath)
    meta = get_document_metadata(filepath)

    # 2. Load schema + existing wiki context
    schema = _load_agents_schema()
    wiki_context = _get_wiki_context(patient_id)

    # 3. Build LLM prompt
    system_prompt = f"""You are a clinical knowledge-base agent.
Follow all rules in the AGENTS.md schema below exactly.
Patient ID: {patient_id}
Document type: {doc_type}

{schema}
"""

    user_prompt = f"""## New Document to Ingest
Filename: {meta["filename"]}
Document Type: {doc_type}

### Raw Document Text
{raw_text[:6000]}

---

### Existing Wiki Context for {patient_id}
{wiki_context[:4000]}

---

## Your Task
1. Extract all clinical entities from the new document (diagnoses with ICD-10, medications, labs, procedures, allergies, follow-ups).
2. Update each relevant wiki page. Output ONLY the updated page(s) using this exact format:

```wiki:<pagename.md>
<full markdown content of the page>
```

3. Flag any drug-allergy conflicts or diagnostic contradictions with ⚠️ ALERT.
4. Do not output any PHI (no full names, DOBs, SSNs, MRNs) outside the wiki page blocks.
5. Update at minimum: patient_overview.md and visit_notes_index.md.
"""

    llm_response = call_llm(user_prompt, system=system_prompt)

    # 4. Write wiki updates
    pages_updated = _write_wiki_updates(patient_id, llm_response)

    # 5. Log
    _append_to_log(patient_id, meta["filename"], pages_updated)
    audit_log(
        "ingest", username, patient_id, meta["filename"],
        f"pages_updated:{len(pages_updated)}", include_detail=True
    )

    return {
        "patient_id": patient_id,
        "filename": meta["filename"],
        "pages_updated": pages_updated,
        "status": "success",
        "llm_response_preview": llm_response[:300] + "..." if len(llm_response) > 300 else llm_response,
    }
