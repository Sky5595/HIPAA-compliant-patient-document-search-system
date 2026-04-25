# hipaa-llm-wiki

Patient document search using [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Instead of RAG, an LLM compiles your raw clinical docs into a structured, interlinked Markdown wiki that gets smarter with every document added.

Runs 100% locally via Ollama. No PHI leaves your machine.

---

## How it works

Three operations, same as the original pattern:

- **Ingest** — drop a PDF/TXT/image into `raw/<patient_id>/`. The LLM extracts diagnoses (ICD-10), meds, labs, allergies, and updates the patient's wiki pages.
- **Query** — ask a plain English question. BM25 finds the relevant wiki pages, LLM synthesizes an answer with source citations.
- **Lint** — scan the wiki for drug-allergy conflicts, contradictory diagnoses, stale meds, and missing follow-ups.

Everything is written to `wiki/<patient_id>/*.md` — plain Markdown you can open in Obsidian, VS Code, or any editor.

---

## Setup

**Prerequisites:** Python 3.10+, [Ollama](https://ollama.com)

```bash
git clone https://github.com/Sky5595/HIPAA-compliant-patient-document-search-system
cd HIPAA-compliant-patient-document-search-system

python -m venv .venv && source .venv/bin/activate
pip install -e .

cp .env.example .env

ollama pull llama3.2
```

Edit `config/roles.yaml` to add your username and assign patient IDs.

---

## Usage

```bash
# Ingest a document
python main.py ingest raw/PT-0001/discharge_note.pdf PT-0001 -u dr_smith

# Specify document type
python main.py ingest raw/PT-0001/labs.pdf PT-0001 -u dr_smith -t lab_report

# Query
python main.py query "Has eGFR been declining?" PT-0001 -u dr_smith
python main.py query "Any drug-allergy conflicts?" PT-0001 -u dr_smith

# Lint
python main.py lint PT-0001 -u dr_smith
python main.py lint --all-patients -u hia_admin

# Audit log
python main.py audit-log -u hia_admin
python main.py audit-log -p PT-0001 -u hia_admin -n 50
```

Document types for `-t`: `clinical_note` `lab_report` `discharge_summary` `imaging_report` `prescription`

---

## Project structure

```
├── main.py
├── AGENTS.md              # LLM schema — clinical ontology, page templates, rules
├── config/
│   ├── settings.yaml      # LLM provider, OCR config
│   └── roles.yaml         # Users, roles, patient assignments
├── src/
│   ├── audit.py           # Append-only JSONL audit trail (PHI hashed)
│   ├── rbac.py            # Patient-scoped role enforcement
│   ├── ocr.py             # PDF + image text extraction
│   ├── llm.py             # Ollama / AWS Bedrock router
│   ├── ingest.py          # Raw doc → wiki compiler
│   ├── query.py           # BM25 + LLM synthesis
│   ├── lint.py            # Clinical safety scanner
│   └── cli.py             # CLI (Click + Rich)
├── raw/                   # Drop patient docs here (gitignored)
├── wiki/                  # Compiled wiki output (gitignored)
├── logs/                  # audit.jsonl + log.md (gitignored)
└── sample_data/           # De-identified test document
```

---

## HIPAA notes

- All inference is local (Ollama). Default config makes zero network calls.
- `logs/audit.jsonl` logs every read, write, query, and lint with timestamp + user ID. Free-form text is SHA-256 hashed before logging.
- `config/roles.yaml` enforces patient-level RBAC. Physicians only see assigned patients.
- `raw/` is never modified by the LLM.
- AWS Bedrock supported — set `bedrock.enabled: true` in `config/settings.yaml`. Requires a signed AWS HIPAA BAA.

> This is a reference implementation. Production use requires a formal HIPAA risk assessment and BAA with your LLM vendor.

---

## AWS Bedrock (optional)

If you have a HIPAA BAA with AWS, you can swap Ollama for Claude:

```yaml
# config/settings.yaml
llm:
  provider: bedrock
bedrock:
  enabled: true
  region: us-east-1
  model_id: anthropic.claude-3-5-sonnet-20241022-v2:0
```

---

## Tests

```bash
# Runs without Ollama
WIKI_MOCK_LLM=1 pytest tests/ -v
```

---

## Roadmap

- [ ] Web UI (FastAPI)
- [ ] HL7 FHIR R4 ingest adapter
- [ ] Embeddings-based hybrid search for large wikis
- [ ] Auto de-identification before ingest

---

## Credits

Pattern by [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).
