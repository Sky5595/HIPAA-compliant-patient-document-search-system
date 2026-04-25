"""
Query engine — Karpathy Phase 2.
Natural-language queries against the compiled patient wiki.
BM25 search over wiki pages; LLM synthesizes the answer.
"""
from __future__ import annotations
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.audit import audit_log
from src.rbac import require_permission
from src.llm import call_llm


WIKI_DIR = Path("wiki")
LOG_FILE = Path("logs/log.md")


# ── Lightweight BM25 ──────────────────────────────────────────────────────────

class BM25:
    def __init__(self, docs: list[tuple[str, str]], k1: float = 1.5, b: float = 0.75):
        self.docs = docs  # [(name, content)]
        self.k1, self.b = k1, b
        tokenized = [self._tokenize(c) for _, c in docs]
        self.avgdl = sum(len(t) for t in tokenized) / max(len(tokenized), 1)
        self.tf = [Counter(t) for t in tokenized]
        N = len(docs)
        self.idf = {}
        all_terms = set(term for t in tokenized for term in t)
        for term in all_terms:
            df = sum(1 for t in tokenized if term in t)
            self.idf[term] = math.log((N - df + 0.5) / (df + 0.5) + 1)

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, str, float]]:
        q_terms = self._tokenize(query)
        scores = []
        for i, (name, _) in enumerate(self.docs):
            dl = sum(self.tf[i].values())
            score = 0.0
            for term in q_terms:
                if term not in self.tf[i]:
                    continue
                tf_val = self.tf[i][term]
                idf = self.idf.get(term, 0)
                score += idf * (tf_val * (self.k1 + 1)) / (
                    tf_val + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                )
            scores.append((name, self.docs[i][1], score))
        return sorted(scores, key=lambda x: -x[2])[:top_k]


def _load_wiki_pages(patient_id: str) -> list[tuple[str, str]]:
    patient_wiki = WIKI_DIR / patient_id
    if not patient_wiki.exists():
        return []
    pages = []
    for md in sorted(patient_wiki.glob("*.md")):
        pages.append((md.name, md.read_text(encoding="utf-8")))
    return pages


def _append_to_log(patient_id: str, question: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"## [{ts}] query | {patient_id} | {question[:80]}\n\n"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(entry)


def query_patient(
    question: str,
    patient_id: str,
    username: str,
    save_answer: bool = False,
) -> dict:
    """
    Answer a natural-language question about a patient using their wiki.

    Args:
        question:    Clinical question in plain English
        patient_id:  e.g. "PT-0001"
        username:    Authenticated user
        save_answer: If True, save the answer back to the wiki as a new page

    Returns:
        dict with keys: answer, sources_used, patient_id
    """
    require_permission(username, "query:all", patient_id)
    audit_log("query", username, patient_id, detail=question)

    pages = _load_wiki_pages(patient_id)
    if not pages:
        return {
            "answer": f"No wiki pages found for {patient_id}. Run ingest first.",
            "sources_used": [],
            "patient_id": patient_id,
        }

    # BM25 retrieval
    bm25 = BM25(pages)
    top_pages = bm25.search(question, top_k=6)

    context_parts = []
    sources_used = []
    for name, content, score in top_pages:
        if score > 0:
            context_parts.append(f"### {name}\n{content}")
            sources_used.append(name)

    context = "\n\n---\n\n".join(context_parts)

    prompt = f"""You are a clinical decision-support assistant.
Answer the following question about patient {patient_id} using ONLY the wiki pages provided.
Cite your sources inline like [source: filename].
Do not invent clinical facts. If the answer is not in the wiki, say so explicitly.

## Question
{question}

## Relevant Wiki Pages
{context[:5000]}

## Answer
"""

    answer = call_llm(prompt)

    # Optionally file answer back to wiki
    if save_answer:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        safe_q = re.sub(r"[^a-z0-9_]", "_", question[:40].lower())
        out_path = WIKI_DIR / patient_id / f"query_{ts}_{safe_q}.md"
        out_path.write_text(
            f"# Query: {question}\n\n**Date:** {ts}\n\n**Answer:**\n{answer}\n\n**Sources:** {sources_used}\n",
            encoding="utf-8"
        )

    _append_to_log(patient_id, question)
    audit_log("query", username, patient_id, detail="complete", include_detail=True)

    return {
        "answer": answer,
        "sources_used": sources_used,
        "patient_id": patient_id,
    }
