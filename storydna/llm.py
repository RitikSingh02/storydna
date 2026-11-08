"""Optional LLM stage behind ONE swappable adapter.

The model is configuration, not code: set STORYDNA_PROVIDER / STORYDNA_MODEL / STORYDNA_API_KEY
(and STORYDNA_BASE_URL for OpenAI-compatible endpoints such as Groq, OpenRouter or Gemini's
OpenAI-compatible API). The prompt text lives in storydna/prompts/*.txt.

Every model answer is VALIDATED before it reaches a reviewer: beat numbers must exist, matches
need a reason, and a "same plot" verdict with no valid evidence is downgraded to "unverified".
The validator is tested with mock models, including one that invents evidence. The live provider
adapters (Anthropic, OpenAI-compatible) are thin HTTP wrappers that I could NOT test against a real
API from the build sandbox; treat them as untested until you run them with your key.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from .textproc import STOPWORDS

PROMPTS = Path(__file__).parent / "prompts"
VERDICTS = {"same_plot", "partial_overlap", "shared_tropes_only", "unrelated"}
CONFIDENCE = {"low", "medium", "high"}


class AdapterError(RuntimeError):
    pass


class NullAdapter:
    name = "none"

    def complete(self, system: str, user: str, max_tokens: int = 1200) -> str:
        raise AdapterError("No model configured. Set STORYDNA_PROVIDER and STORYDNA_MODEL.")


class MockAdapter:
    """Deterministic stand-in used by the tests and for offline demos."""
    name = "mock"

    def __init__(self, fn: Callable[[str, str], str]):
        self.fn = fn

    def complete(self, system: str, user: str, max_tokens: int = 1200) -> str:
        return self.fn(system, user)


def _post(url: str, headers: dict, body: dict, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise AdapterError("HTTP %s from model endpoint: %s" % (e.code, e.read().decode()[:300]))
    except (urllib.error.URLError, TimeoutError) as e:
        raise AdapterError("Could not reach model endpoint: %s" % e)


class AnthropicAdapter:
    def __init__(self, model: str, api_key: str, base_url: str = "https://api.anthropic.com"):
        self.model, self.key, self.base = model, api_key, base_url.rstrip("/")
        self.name = "anthropic:" + model

    def complete(self, system: str, user: str, max_tokens: int = 1200) -> str:
        d = _post(self.base + "/v1/messages", {"x-api-key": self.key, "anthropic-version": "2023-06-01"},
                  {"model": self.model, "max_tokens": max_tokens, "temperature": 0, "system": system,
                   "messages": [{"role": "user", "content": user}]})
        try:
            return "".join(b.get("text", "") for b in d["content"])
        except (KeyError, TypeError):
            raise AdapterError("Unexpected response shape from Anthropic endpoint")


class OpenAICompatAdapter:
    def __init__(self, model: str, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.model, self.key, self.base = model, api_key, base_url.rstrip("/")
        self.name = "openai-compat:%s@%s" % (model, re.sub(r"^https?://", "", self.base).split("/")[0])

    def complete(self, system: str, user: str, max_tokens: int = 1200) -> str:
        d = _post(self.base + "/chat/completions", {"authorization": "Bearer " + self.key},
                  {"model": self.model, "max_tokens": max_tokens, "temperature": 0,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        try:
            return d["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise AdapterError("Unexpected response shape from OpenAI-compatible endpoint")


def adapter_from_env(env: dict | None = None):
    """Build an adapter from environment variables. Returns NullAdapter when nothing is configured."""
    e = env if env is not None else os.environ
    prov = (e.get("STORYDNA_PROVIDER") or "none").lower()
    if prov in ("none", ""):
        return NullAdapter()
    model = e.get("STORYDNA_MODEL")
    if not model:
        raise AdapterError("STORYDNA_MODEL is required (the model is configuration, not code).")
    key = e.get("STORYDNA_API_KEY") or e.get("ANTHROPIC_API_KEY" if prov == "anthropic" else "OPENAI_API_KEY")
    if not key:
        raise AdapterError("No API key found: set STORYDNA_API_KEY.")
    if prov == "anthropic":
        return AnthropicAdapter(model, key, e.get("STORYDNA_BASE_URL", "https://api.anthropic.com"))
    if prov in ("openai", "openai_compat", "groq", "openrouter", "gemini"):
        return OpenAICompatAdapter(model, key, e.get("STORYDNA_BASE_URL", "https://api.openai.com/v1"))
    raise AdapterError("Unknown STORYDNA_PROVIDER %r" % prov)


# --------------------------------------------------------------------------------------------
def _load_prompt(name: str) -> tuple[str, str]:
    raw = (PROMPTS / name).read_text()
    system = raw.split("### SYSTEM", 1)[1].split("### USER", 1)[0].strip()
    user = raw.split("### USER", 1)[1].strip()
    return system, user


def _parse_json(s: str) -> dict:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.S)
    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m:
        raise ValueError("no JSON object found in model output")
    return json.loads(m.group(0))


def _numbered(beats: list[str]) -> str:
    return "\n".join("%d. %s" % (i, b) for i, b in enumerate(beats))


def validate_compare(raw: dict, q_beats: list[str], c_beats: list[str]) -> dict:
    """Validate a model's comparison against the source beats. Never trusts the model."""
    verdict = raw.get("verdict")
    if verdict not in VERDICTS:
        raise ValueError("invalid verdict %r" % (verdict,))
    conf = raw.get("confidence") if raw.get("confidence") in CONFIDENCE else "low"
    good, dropped, seen = [], 0, set()
    for m in (raw.get("matched") or [])[:12]:
        try:
            i, j, why = int(m["pitch_beat"]), int(m["candidate_beat"]), str(m.get("why", "")).strip()
        except (KeyError, TypeError, ValueError):
            dropped += 1
            continue
        if not (0 <= i < len(q_beats) and 0 <= j < len(c_beats)) or not why or (i, j) in seen:
            dropped += 1
            continue
        seen.add((i, j))
        good.append({"pitch_beat_index": i, "pitch_text": q_beats[i], "candidate_beat_index": j,
                     "candidate_text": c_beats[j], "why": why})
    diffs = [str(d) for d in (raw.get("differences") or [])[:5] if str(d).strip()]
    status = "ok"
    if verdict in ("same_plot", "partial_overlap") and not good:
        verdict, status = "unverified", "downgraded: no valid evidence for the claimed overlap"
    return {"status": status, "verdict": verdict, "confidence": conf, "matched": good,
            "invalid_evidence_dropped": dropped, "differences": diffs}


def llm_compare(q_beats: list[str], c_beats: list[str], adapter, retries: int = 1) -> dict:
    system, user_t = _load_prompt("compare_pair.txt")
    user = user_t.replace("{pitch_beats}", _numbered(q_beats)).replace("{candidate_beats}", _numbered(c_beats))
    last = "unknown error"
    for _ in range(retries + 1):
        try:
            out = adapter.complete(system, user)
            return validate_compare(_parse_json(out), q_beats, c_beats)
        except AdapterError as e:
            return {"status": "error", "verdict": "unverified", "error": str(e)}
        except (ValueError, json.JSONDecodeError, KeyError) as e:
            last = str(e)
    return {"status": "error", "verdict": "unverified", "error": "model output failed validation: " + last}


def llm_extract_beats(text: str, adapter, min_beats: int = 3, max_beats: int = 12) -> list[str]:
    """Condense a long text to ordered plot beats; reject beats not grounded in the source text."""
    system, user_t = _load_prompt("extract_beats.txt")
    out = adapter.complete(system, user_t.replace("{text}", text[:60000]), max_tokens=1500)
    beats = _parse_json(out).get("beats")
    if not isinstance(beats, list):
        raise ValueError("beats missing")
    src = {w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOPWORDS}
    kept = []
    for b in beats[:max_beats]:
        b = str(b).strip()
        words = [w for w in re.findall(r"[a-z]+", b.lower()) if w not in STOPWORDS]
        if b and len(b.split()) <= 40 and words and sum(w in src for w in words) / len(words) >= 0.6:
            kept.append(b if b[-1] in ".!?" else b + ".")
    if len(kept) < min_beats:
        raise ValueError("fewer than %d grounded beats returned" % min_beats)
    return kept
