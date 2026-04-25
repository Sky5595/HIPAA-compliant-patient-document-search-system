"""
LLM client — routes to Ollama (local) or AWS Bedrock.
Set WIKI_MOCK_LLM=1 in environment to return stub responses (useful for testing without Ollama).
"""
from __future__ import annotations
import os
import yaml
from pathlib import Path


def _cfg() -> dict:
    p = Path("config/settings.yaml")
    return yaml.safe_load(p.read_text()) if p.exists() else {}


def call_llm(prompt: str, system: str = "") -> str:
    if os.getenv("WIKI_MOCK_LLM"):
        return _mock_response(prompt)

    cfg = _cfg()
    provider = cfg.get("llm", {}).get("provider", "ollama")
    if provider == "bedrock" and cfg.get("bedrock", {}).get("enabled", False):
        return _bedrock(prompt, system, cfg)
    return _ollama(prompt, system, cfg)


def _ollama(prompt: str, system: str, cfg: dict) -> str:
    try:
        import ollama
    except ImportError:
        raise RuntimeError(
            "Run: pip install ollama\n"
            "Then: ollama pull llama3.2\n"
            "Docs: https://ollama.com"
        )
    model = cfg.get("llm", {}).get("model", "llama3.2")
    host  = cfg.get("llm", {}).get("base_url", "http://localhost:11434")
    temp  = cfg.get("llm", {}).get("temperature", 0.1)
    msgs  = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    try:
        r = ollama.Client(host=host).chat(
            model=model, messages=msgs, options={"temperature": temp}
        )
        return r["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}\nIs Ollama running? Try: ollama serve") from e


def _bedrock(prompt: str, system: str, cfg: dict) -> str:
    """Only use with a signed AWS HIPAA BAA."""
    import boto3, json
    bc  = cfg.get("bedrock", {})
    client = boto3.client("bedrock-runtime", region_name=bc.get("region", "us-east-1"))
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": cfg.get("llm", {}).get("max_tokens", 4096),
        "temperature": cfg.get("llm", {}).get("temperature", 0.1),
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system
    r = client.invoke_model(modelId=bc.get("model_id"), body=json.dumps(body))
    return json.loads(r["body"].read())["content"][0]["text"]


def _mock_response(prompt: str) -> str:
    """Stub used in tests / CI — no Ollama needed."""
    return """```wiki:patient_overview.md
---
patient_id: PT-TEST
last_updated: 2026-01-01
---
## Summary
Mock patient for testing.
```
```wiki:visit_notes_index.md
| Date | Document | Summary |
|------|----------|---------|
| 2026-01-01 | test.txt | Mock ingest |
```"""
