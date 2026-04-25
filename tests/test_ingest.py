"""Integration test for ingest — runs without Ollama via WIKI_MOCK_LLM=1."""
import os, pytest
os.environ["AUDIT_FILE"] = "/tmp/test_audit.jsonl"
os.environ["WIKI_MOCK_LLM"] = "1"

from src.ingest import ingest_document

def test_ingest_sample_doc(tmp_path):
    # Write a minimal raw doc
    raw = tmp_path / "note.txt"
    raw.write_text("Patient: PT-TEST\nDiagnosis: Hypertension ICD-10 I10\nMed: Lisinopril 10mg")

    # Patch wiki + log dirs to tmp
    import src.ingest as ing
    ing.WIKI_DIR = tmp_path / "wiki"
    ing.LOG_FILE = tmp_path / "log.md"

    result = ingest_document(str(raw), "PT-TEST", "dr_smith")
    assert result["status"] == "success"
    assert result["patient_id"] == "PT-TEST"
