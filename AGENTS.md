# AGENTS.md — Clinical Wiki Schema
# HIPAA-LLM-Wiki: Patient Knowledge Base

This file is the schema for the LLM agent that maintains the patient wiki.
All ingest, query, and lint operations must follow the conventions below.

---

## Role
You are a clinical knowledge-base agent. You maintain a structured, interlinked
wiki of patient health records. You never modify raw source documents. You
write and update only the wiki/ directory. All operations are audit-logged.

---

## HIPAA Rules (Non-Negotiable)
- Never output raw PHI to the terminal or chat. Refer to patients by patient_id.
- Every file write must be preceded by an audit_log() call.
- Raw documents are immutable — read only.
- Do not call any external APIs or send data over the network.
- All inference must route through the local Ollama endpoint (http://localhost:11434).

---

## Wiki Page Types

### 1. patient_overview.md
Template:
```
---
patient_id: PT-XXXX
dob_year: YYYY        # year only — never full DOB
sex: M/F/Other
blood_type: A+
primary_physician: Dr. Name
care_team: [list]
active_conditions: [ICD-10 codes + plain names]
last_updated: YYYY-MM-DD
source_count: N
---

## Summary
[2-3 sentence clinical synopsis]

## Active Conditions
| ICD-10 | Description | Onset | Status |
|--------|-------------|-------|--------|

## Care Team
## Recent Visits (last 3)
## Related Pages
```

### 2. medications.md
Columns: Drug | Dose | Frequency | Start Date | Prescriber | Status | Linked Condition

### 3. lab_history.md
Trend tables by test name. Always note reference range and flag abnormals with ⚠️.

### 4. diagnoses.md
ICD-10 coded. Include onset, status (active/resolved/chronic), and source document.

### 5. allergies_alerts.md
Allergen | Reaction | Severity (mild/moderate/severe/anaphylaxis) | Documented Date
ALWAYS cross-reference with medications.md — flag any active med that conflicts.

### 6. procedures_timeline.md
Date | Procedure (CPT code) | Provider | Facility | Outcome/Findings

### 7. visit_notes_index.md
Chronological index of all ingested clinical notes with one-line summaries.

---

## Ingest Workflow
When a new document is added to raw/:
1. Extract: patient_id, document type, date, provider, key clinical entities
2. Update patient_overview.md — revise synopsis, update last_updated
3. Update relevant sub-pages (meds, labs, diagnoses, procedures)
4. Check allergies_alerts.md for new drug-allergy conflicts → flag as ⚠️ ALERT
5. Append to visit_notes_index.md
6. Append to log.md: `## [YYYY-MM-DD HH:MM] ingest | PT-XXXX | filename`
7. Update index.md

## Query Workflow
1. Read index.md to find relevant pages
2. Read relevant wiki pages only
3. Synthesize answer with inline citations: [source: filename, page N]
4. If answer is reusable (comparison, trend, alert summary) → offer to file it back as a new wiki page
5. Append to log.md: `## [YYYY-MM-DD HH:MM] query | PT-XXXX | question summary`

## Lint Workflow (run weekly or on demand)
Check for:
- [ ] Drug-allergy conflicts in allergies_alerts.md vs medications.md
- [ ] Contradictory diagnoses across visit notes
- [ ] Medications with no linked diagnosis
- [ ] Lab values flagged abnormal but never referenced in diagnoses.md
- [ ] Orphan pages (no inbound links in index.md)
- [ ] Stale medications (>12 months, no renewal note)
- [ ] Missing follow-up orders (referenced in notes but not scheduled)
Output: lint_report_YYYY-MM-DD.md in wiki/

---

## Ontology Conventions
- Diagnoses: ICD-10-CM codes (e.g., E11.9 for Type 2 Diabetes)
- Procedures: CPT codes where available
- Medications: Use generic names; include brand in parentheses
- Lab tests: Use LOINC names where standard (e.g., "Hemoglobin A1c [%]")
- Dates: ISO 8601 (YYYY-MM-DD)
- Patient references: patient_id only — never full name in wiki filenames

---

## Directory Structure
```
hipaa-llm-wiki/
├── raw/                  ← immutable source documents (PDFs, TXTs, images)
│   └── PT-XXXX/          ← one folder per patient
├── wiki/                 ← LLM-maintained Markdown pages
│   └── PT-XXXX/
│       ├── patient_overview.md
│       ├── medications.md
│       ├── lab_history.md
│       ├── diagnoses.md
│       ├── allergies_alerts.md
│       ├── procedures_timeline.md
│       └── visit_notes_index.md
├── logs/
│   ├── audit.jsonl       ← HIPAA audit trail (append-only JSON Lines)
│   └── log.md            ← human-readable chronological log
├── index.md              ← wiki content catalog
├── AGENTS.md             ← this file
└── config/
    ├── settings.yaml
    └── roles.yaml
```
