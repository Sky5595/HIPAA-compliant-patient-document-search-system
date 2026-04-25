import os, pytest
os.environ["AUDIT_FILE"] = "/tmp/test_audit.jsonl"
from src.audit import audit_log, tail_audit_log, search_audit_log

def test_audit_log_writes():
    audit_log("ingest", "dr_smith", "PT-0001", "note.pdf", "test")
    records = tail_audit_log(5)
    assert any(r["action"] == "ingest" for r in records)

def test_audit_log_patient_filter():
    audit_log("query", "nurse_jones", "PT-0002", detail="test")
    results = search_audit_log("PT-0002")
    assert all(r["patient_id"] == "PT-0002" for r in results)

def test_phi_safe_hashing():
    audit_log("query", "dr_smith", "PT-0001", detail="John Doe DOB 1980-01-01")
    records = tail_audit_log(1)
    assert "John" not in records[-1]["detail"]
