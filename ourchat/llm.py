#!/usr/bin/env python3
"""
llm.py — pluggable LLM adapter. The whole AI layer (room characterization, topic
naming, narratives, character profiles) goes through chat().
Configure via env — bring your own key, or run fully offline (provider=none):

  KAKAO_LLM_PROVIDER = none | openai | anthropic     (default: none)
  KAKAO_LLM_MODEL    = e.g. gpt-4o-mini / claude-haiku-4-5 / qwen (local)
  KAKAO_LLM_BASE_URL = OpenAI-compatible base (OpenAI, Ollama :11434/v1, vLLM, LM Studio…)
  KAKAO_LLM_API_KEY  = api key (omit for local servers)

provider=none → chat() returns None so every caller falls back to deterministic
output. This is the open-core seam: the pipeline is fully useful with no LLM; the
AI just makes it richer.
"""
import os, json, urllib.request, re

PROVIDER = os.environ.get("KAKAO_LLM_PROVIDER", "none").lower()
MODEL = os.environ.get("KAKAO_LLM_MODEL") or ("claude-haiku-4-5" if PROVIDER == "anthropic" else "gpt-4o-mini")
BASE = os.environ.get("KAKAO_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
KEY = os.environ.get("KAKAO_LLM_API_KEY", "")

def available():
    """True if an LLM provider is configured (i.e. not offline)."""
    return PROVIDER not in ("none", "", None)

def _post(url, body, headers, timeout=120):
    """POST JSON, return parsed JSON. Raises on HTTP/network error."""
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())

def chat(system, user, max_tokens=800, temperature=0.5, timeout=120):
    """Return assistant text, or None if no provider / on error."""
    if not available():
        return None
    try:
        if PROVIDER == "anthropic":
            d = _post("https://api.anthropic.com/v1/messages",
                {"model": MODEL, "max_tokens": max_tokens, "temperature": temperature,
                 "system": system, "messages": [{"role": "user", "content": user}]},
                {"content-type": "application/json", "x-api-key": KEY,
                 "anthropic-version": "2023-06-01"}, timeout)
            return "".join(b.get("text", "") for b in d.get("content", [])).strip()
        # default: OpenAI-compatible (OpenAI / Ollama / vLLM / LM Studio / local)
        h = {"content-type": "application/json"}
        if KEY: h["authorization"] = f"Bearer {KEY}"
        d = _post(f"{BASE}/chat/completions",
            {"model": MODEL, "max_tokens": max_tokens, "temperature": temperature,
             "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            h, timeout)
        return (d["choices"][0]["message"].get("content") or "").strip()
    except Exception as e:
        print(f"[llm] {PROVIDER} error: {e}", flush=True)
        return None

def chat_json(system, user, **kw):
    """chat() but parse the first {...} JSON object from the reply. None on failure."""
    txt = chat(system, user, **kw)
    if not txt:
        return None
    m = re.search(r"\{[\s\S]*\}", txt)
    try:
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None
