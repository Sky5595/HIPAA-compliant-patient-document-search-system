"""
HIPAA Audit Trail — append-only JSON Lines log.
Every read, write, query, and lint operation is recorded here.
This file is the primary HIPAA audit artifact.
"""
import json
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


AUDIT_FILE = Path(os.getenv("AUDIT_FILE", "logs/audit.jsonl"))


def _ensure_log_dir():
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)


def _phi_safe(text: Optional[str]) -> str:
    """Replace free-form text with a SHA-256 hash to keep PHI out of logs."""
    if text is None:
        return ""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def audit_log(
    action: str,
    user: str,
    patient_id: Optional[str] = None,
    document: Optional[str] = None,
    detail: Optional[str] = None,
    include_detail: bool = False,
) -> None:
    """
    Append one audit record to the JSONL audit file.

    Args:
        action:      One of: ingest | query | lint | read | write | login | logout | access_denied
        user:        Username performing the action
        patient_id:  Patient identifier (e.g. PT-0001) — never full name
        document:    Filename of the source or wiki document accessed
        detail:      Free-form detail string — hashed unless include_detail=True
        include_detail: Set True only for non-PHI details (e.g. lint summary counts)
    """
    _ensure_log_dir()

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user": user,
        "patient_id": patient_id or "N/A",
        "document": document or "N/A",
        "detail": detail if include_detail else _phi_safe(detail),
    }

    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def audit_log_access_denied(user: str, patient_id: str, reason: str) -> None:
    audit_log("access_denied", user, patient_id, detail=reason, include_detail=True)


def tail_audit_log(n: int = 20) -> list[dict]:
    """Return the last N audit records."""
    _ensure_log_dir()
    if not AUDIT_FILE.exists():
        return []
    lines = AUDIT_FILE.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines[-n:] if line]


def search_audit_log(patient_id: str) -> list[dict]:
    """Return all audit records for a specific patient_id."""
    _ensure_log_dir()
    if not AUDIT_FILE.exists():
        return []
    results = []
    for line in AUDIT_FILE.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("patient_id") == patient_id:
            results.append(rec)
    return results
