# 🏥 HIPAA-LLM-Wiki

> **Andrej Karpathy's LLM Wiki pattern — adapted for HIPAA-compliant patient document search in hospitals and clinics.**

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Local-First](https://img.shields.io/badge/PHI-Local--Only-red)](#-hipaa-compliance)
[![Ollama](https://img.shields.io/badge/LLM-Ollama-purple)](https://ollama.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/YOUR_USERNAME/hipaa-llm-wiki/pulls)

Instead of re-querying raw clinical documents on every search (like RAG), this system uses an LLM to **incrementally compile and maintain a structured patient wiki** — so knowledge compounds with every document ingested. Clinicians get synthesized, contradiction-checked, cross-referenced answers in seconds.

---

## 🤔 Why Not Just RAG?

| | Traditional RAG | HIPAA-LLM-Wiki |
|---|---|---|
| **Knowledge synthesis** | Re-derived on every query | Compiled once, cached in wiki |
| **Cross-visit continuity** | Depends on chunk overlap | Explicitly maintained entity pages |
| **Contradiction detection** | Passive — must be queried for | Active at every ingest + lint pass |
| **Drug-allergy conflicts** | Must be queried for | Flagged automatically on ingest |
| **PHI protection** | Varies by implementation | 100% local — zero network calls |
| **Auditability** | Opaque vector index | Human-readable Markdown + JSONL |
| **Clinician experience** | Scroll through raw chunks | Browse a structured wiki in Obsidian |

> Inspired by [Andrej Karpathy's LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (April 2026).

---

## ✨ Features

- 📄 **Ingest** — Drop any clinical document (PDF, scanned image, TXT). The LLM extracts diagnoses (ICD-10), medications, labs, allergies, and procedures, then updates the patient wiki automatically.
- 🔍 **Query** — Ask plain-English clinical questions: *"Has this patient's eGFR been declining?"* — answered from pre-compiled wiki pages with source citations.
- 🩺 **Lint** — Weekly or on-demand safety scans: drug-allergy conflicts, contradictory diagnoses, stale medications, missing follow-up orders, abnormal labs never linked to a diagnosis.
- 🔒 **HIPAA Audit Trail** — Every read, write, query, and lint operation logged to an append-only JSONL file with PHI hashing.
- 👥 **RBAC** — Role-based access control: physicians see only their assigned patients, nurses have limited write scope, admins manage users with no clinical access.
- 🏠 **100% Local** — Runs on Ollama (Llama 3.2, Mistral, Phi-3). Zero PHI over the network. AWS Bedrock supported if you have a signed HIPAA BAA.
- 📁 **Git-friendly** — Wiki is plain Markdown. Browse it in Obsidian, VS Code, or any text editor.

---

## 🏗️ Architecture

```
hipaa-llm-wiki/
├── main.py                        ← CLI entry point
├── AGENTS.md                      ← Clinical LLM schema (ICD-10, SNOMED CT, LOINC)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml             ← Air-gapped Ollama + wiki container
├── config/
│   ├── settings.yaml              ← LLM provider, OCR, paths
│   └── roles.yaml                 ← Users, roles, patient assignments
├── src/
│   ├── audit.py                   ← HIPAA audit trail (append-only JSONL, PHI-hashed)
│   ├── rbac.py                    ← Patient-scoped role enforcement
│   ├── ocr.py                     ← PDF + scanned image text extraction
│   ├── llm.py                     ← Ollama (local) or AWS Bedrock router
│   ├── ingest.py                  ← Raw doc → compiled wiki pages
│   ├── query.py                   ← BM25 retrieval + LLM synthesis
│   ├── lint.py                    ← Clinical safety scanner
│   └── cli.py                     ← Full CLI (Click + Rich)
├── tests/
│   ├── test_audit.py
│   └── test_rbac.py
├── raw/                           ← Drop patient documents here (gitignored)
│   └── PT-XXXX/
├── wiki/                          ← LLM-compiled wiki pages (gitignored)
│   └── PT-XXXX/
│       ├── patient_overview.md
│       ├── medications.md
│       ├── lab_history.md
│       ├── diagnoses.md
│       ├── allergies_alerts.md
│       ├── procedures_timeline.md
│       └── visit_notes_index.md
├── logs/
│   ├── audit.jsonl                ← HIPAA audit trail (gitignored)
│   └── log.md                     ← Human-readable log (gitignored)
└── sample_data/
    └── PT-0001_discharge_note.txt ← De-identified test document
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [Ollama](https://ollama.com) installed and running

### 1. Install Ollama and pull a model

```bash
# Install Ollama: https://ollama.com/download
ollama pull llama3.2        # recommended — runs 100% locally
# or: ollama pull mistral
# or: ollama pull phi3
```

### 2. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/hipaa-llm-wiki
cd hipaa-llm-wiki
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. Configure users

Edit `config/roles.yaml` — add your username and assign patient IDs:

```yaml
users:
  - username: dr_smith
    role: physician
    assigned_patients: [PT-0001, PT-0002]
    active: true
```

### 4. Ingest a document

```bash
mkdir -p raw/PT-0001
cp my_discharge_note.pdf raw/PT-0001/

python main.py ingest raw/PT-0001/discharge_note.pdf PT-0001 -u dr_smith
# With document type hint:
python main.py ingest raw/PT-0001/labs.pdf PT-0001 -u dr_smith -t lab_report
```

### 5. Query the wiki

```bash
python main.py query "Has the patient's eGFR been declining?" PT-0001 -u dr_smith
python main.py query "List all current medications and flag any allergy conflicts" PT-0001 -u dr_smith
python main.py query "Summarize this patient's cardiac history for a new provider" PT-0001 -u dr_smith --save
```

### 6. Run a clinical safety lint scan

```bash
python main.py lint PT-0001 -u dr_smith
python main.py lint --all-patients -u hia_admin
```

### 7. View the HIPAA audit log

```bash
python main.py audit-log -u hia_admin
python main.py audit-log -p PT-0001 -u hia_admin
```

---

## 🐳 Docker (Air-Gapped)

```bash
docker-compose up -d        # starts Ollama + wiki container, network_mode: none
docker exec -it hipaa-llm-wiki python main.py ingest raw/PT-0001/note.txt PT-0001 -u dr_smith
```

The `wiki` container runs with `network_mode: none` — fully air-gapped after startup.

---

## 📋 Example Auto-Generated Wiki Page

After ingesting a discharge summary, `wiki/PT-0001/patient_overview.md` might look like:

```markdown
---
patient_id: PT-0001
dob_year: 1962
sex: M
primary_physician: Dr. Sample
active_conditions: [I50.20, E11.65, N18.31]
last_updated: 2025-11-14
source_count: 3
---

## Summary
PT-0001 is a male patient with HFrEF, uncontrolled T2DM (HbA1c 9.1%), and
progressive CKD Stage 3a (eGFR 48, trending down from 54 over 3 months).
Admitted for acute decompensated heart failure; discharged on Carvedilol + Furosemide.

⚠️ ALERT: Furosemide is sulfonamide-derived. Patient has a SEVERE sulfonamide
allergy on file. Verify with pharmacy — see allergies_alerts.md.

## Active Conditions
| ICD-10  | Description               | Onset   | Status           |
|---------|---------------------------|---------|------------------|
| I50.20  | HFrEF                     | 2025-11 | Active           |
| E11.65  | T2DM, uncontrolled        | 2021-03 | Chronic          |
| N18.31  | CKD Stage 3a              | 2023-06 | Chronic/Progressing |
```

---

## 🩺 Lint Checks

| Severity | Check |
|---|---|
| 🔴 CRITICAL | Drug-allergy conflicts (active med matches allergen) |
| 🔴 CRITICAL | Contradictory diagnoses across provider notes |
| 🟡 WARNING | Stale medications (>12 months, no renewal) |
| 🟡 WARNING | Abnormal lab values not linked to any diagnosis |
| 🟡 WARNING | Missing follow-up orders (referenced in notes, not scheduled) |
| 🔵 INFO | Orphan wiki pages with no inbound references |

---

## 🔒 HIPAA Compliance

| Control | Implementation |
|---|---|
| **Local-only inference** | Ollama — zero PHI over the network by default |
| **Audit trail** | Append-only `logs/audit.jsonl` — every action logged with timestamp + user |
| **PHI in logs** | Free-form text SHA-256 hashed; patient IDs used instead of names |
| **Access control** | `config/roles.yaml` — patient-scoped RBAC (physician/nurse/admin/readonly) |
| **Immutable source** | `raw/` is never modified by the LLM |
| **AWS Bedrock option** | Enable in `config/settings.yaml` **only** with a signed AWS HIPAA BAA |

> ⚠️ **Disclaimer:** This is a reference implementation for research and development.
> A production clinical deployment requires a formal HIPAA risk assessment, signed BAA
> with your LLM/cloud vendor, and review by your compliance and legal team.

---

## 🛠️ CLI Reference

```
python main.py ingest <filepath> <patient_id> -u <username> [-t doc_type]
python main.py query  <question>  <patient_id> -u <username> [--save]
python main.py lint   [patient_id] -u <username> [--all-patients]
python main.py audit-log -u <username> [-p patient_id] [-n tail_count]
python main.py users list -u <username>
```

Document types for `--type` (`-t`): `clinical_note` · `lab_report` · `discharge_summary` · `imaging_report` · `prescription`

---

## 🧪 Running Tests

```bash
pytest tests/ -v --cov=src
```

---

## 🗺️ Roadmap

- [ ] Web UI (FastAPI + React) for non-technical clinical staff
- [ ] HL7 FHIR R4 ingest adapter
- [ ] Multi-patient dashboard with lint summary across all patients
- [ ] Embeddings-based hybrid search (BM25 + medical BERT) for large wikis
- [ ] Automated de-identification layer before ingest
- [ ] Integration with Epic / Cerner via SMART on FHIR

---

## 🤝 Contributing

PRs welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting.
For clinical accuracy improvements, please cite the relevant clinical guideline or ontology source.

---

## 🙏 Credits

- **Pattern:** [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (April 2026)
- **Local LLM inference:** [Ollama](https://ollama.com)
- **Ontologies:** ICD-10-CM · SNOMED CT · LOINC · CPT

---

## 📄 License

MIT — see [LICENSE](LICENSE).
