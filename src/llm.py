"""
LLM client abstraction.
Routes to Ollama (local, default) or AWS Bedrock (HIPAA BAA required).
"""
from __future__ import annotations
import os
import yaml
from pathlib import Path


def _load_settings() -> dict:
    cfg_path = Path("config/settings.yaml")
    if cfg_path.exists():
        with cfg_path.open() as f:
            return yaml.safe_load(f)
    return {}


def call_llm(prompt: str, system: str = "") -> str:
    """
    Send a prompt to the configured LLM and return the response text.
    All inference is local by default (Ollama). Zero network calls unless
    Bedrock is explicitly enabled in config/settings.yaml.
    """
    cfg = _load_settings()
    provider = cfg.get("llm", {}).get("provider", "ollama")

    if provider == "bedrock" and cfg.get("bedrock", {}).get("enabled", False):
        return _call_bedrock(prompt, system, cfg)
    return _call_ollama(prompt, system, cfg)


def _call_ollama(prompt: str, system: str, cfg: dict) -> str:
    try:
        import ollama
    except ImportError:
        raise RuntimeError("pip install ollama  — then: ollama pull llama3.2")

    model = cfg.get("llm", {}).get("model", "llama3.2")
    base_url = cfg.get("llm", {}).get("base_url", "http://localhost:11434")
    temp = cfg.get("llm", {}).get("temperature", 0.1)

    client = ollama.Client(host=base_url)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat(
        model=model,
        messages=messages,
        options={"temperature": temp},
    )
    return response["message"]["content"]


def _call_bedrock(prompt: str, system: str, cfg: dict) -> str:
    """AWS Bedrock — only use if you have a signed HIPAA BAA with AWS."""
    try:
        import boto3, json
    except ImportError:
        raise RuntimeError("pip install boto3")

    bedrock_cfg = cfg.get("bedrock", {})
    region = bedrock_cfg.get("region", "us-east-1")
    model_id = bedrock_cfg.get("model_id", "anthropic.claude-3-5-sonnet-20241022-v2:0")

    client = boto3.client("bedrock-runtime", region_name=region)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": cfg.get("llm", {}).get("max_tokens", 4096),
        "temperature": cfg.get("llm", {}).get("temperature", 0.1),
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system

    response = client.invoke_model(modelId=model_id, body=json.dumps(body))
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]
