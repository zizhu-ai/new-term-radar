"""Client for AIsa, the radar's one paid dependency: its tool router (X posts, Google
Trends and whois data through DataForSEO) and its OpenAI-compatible chat endpoint (the
name judge). One key: AISA_API_KEY, or the one the AIsa CLI stores when you log in.

The tool router runs a batch's calls one by one, about 10 s each, so batches are kept to
BATCH calls and the timeout is long. Every call is billed: a failed batch is never
retried here, so one bad day costs one batch at most.

Prices seen in October 2026: an account's last 20 posts $0.003, one Trends task $0.0012,
one whois overview query about $0.13.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from . import UA

ROUTER = os.environ.get("AISA_ROUTER_BASE_URL", "https://tools.aisa.one") + "/v1/tool-router/aisa-batch-use"
CHAT = os.environ.get("AISA_API_BASE_URL", "https://api.aisa.one") + "/v1/chat/completions"
MAX_CALLS = 20      # the router's own limit per batch
BATCH = 5           # what call_all sends at once, about 50 s a batch
TIMEOUT = 240
CHAT_TIMEOUT = 90


class AisaError(RuntimeError):
    pass


# Alias used by box callers / reports so a MiMo (LLM_API_KEY) failure is not mistaken
# for a missing AIsa tool-router key. Same exception class.
LLMError = AisaError


def key() -> str:
    """AISA_API_KEY, else the key the AIsa CLI stored at login (~/.aisa)."""
    k = os.environ.get("AISA_API_KEY", "").strip()
    if k:
        return k
    home = Path.home() / ".aisa"
    try:
        if (home / "key").exists():
            return (home / "key").read_text().strip()
        if (home / "tokens.json").exists():
            return json.loads((home / "tokens.json").read_text()).get("accessToken", "") or _no_key()
    except (OSError, ValueError):
        pass
    return _no_key()


def _no_key() -> str:
    raise AisaError("no AIsa key: set AISA_API_KEY, or log in with the AIsa CLI (`aisa login`)")


def _post(url: str, body: dict, timeout: int) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key()}",
        "User-Agent": UA, "x-aisa-source": "new-term-radar"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.load(res)
    except urllib.error.HTTPError as exc:
        raise AisaError(f"HTTP {exc.code}: {' '.join(exc.read().decode('utf-8', 'replace').split())[:200]}") from exc
    except (OSError, ValueError) as exc:
        raise AisaError(f"{type(exc).__name__}: {exc}") from exc


def call(calls: list[dict]) -> tuple[dict[str, dict], int]:
    """Run one batch of tool calls. Returns ({call_id: data}, cost in micro-USD). Calls
    that failed are left out of the dict; only a failed request raises."""
    blocked = [c for c in calls if "dataforseo" in str(c.get("tool", "")).lower()]
    if blocked:
        # Hard lock (2026-10-29, Yoyo): this radar never calls DataForSEO, key or no key.
        import sys
        print(f"aisa: DataForSEO locked off, skipped {len(blocked)} call(s): "
              f"{sorted({c.get('tool') for c in blocked})}", file=sys.stderr)
        calls = [c for c in calls if c not in blocked]
    if not calls:
        return {}, 0
    if len(calls) > MAX_CALLS:
        raise AisaError(f"{len(calls)} calls in one batch, the cap is {MAX_CALLS}")
    body = _post(ROUTER, {"calls": calls}, TIMEOUT)
    if "error" in body:
        raise AisaError(str(body["error"].get("message") or body["error"])[:200])
    out, cost = {}, 0
    for r in body.get("results", []):
        cost += int(r.get("customer_cost_micros_usd") or 0)
        if r.get("successful"):
            out[r["call_id"]] = r.get("data") or {}
    return out, cost


def call_all(calls: list[dict]) -> tuple[dict[str, dict], int]:
    """call() in batches of BATCH. A failed batch raises and stops the rest."""
    out, cost = {}, 0
    for i in range(0, len(calls), BATCH):
        data, c = call(calls[i:i + BATCH])
        out.update(data)
        cost += c
    return out, cost


def chat(model: str, system: str, user: str, max_tokens: int = 1500) -> str:
    # Box patch: if LLM_API_KEY is set, use that OpenAI-compatible endpoint (e.g. Xiaomi MiMo) instead of AIsa.
    if os.environ.get("LLM_API_KEY"):
        return _llm_chat(system, user, max_tokens)
    body = _post(CHAT, {"model": model, "temperature": 0, "max_tokens": max_tokens, "messages": [
        {"role": "system", "content": system}, {"role": "user", "content": user}]}, CHAT_TIMEOUT)
    try:
        return body["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise AisaError(f"unexpected chat answer: {str(body)[:160]}") from exc


LLM_TRIES = 4             # box patch: MiMo sometimes drops the connection mid-answer (IncompleteRead)
LLM_BACKOFF = (5, 15, 40)


def _llm_chat(system: str, user: str, max_tokens: int) -> str:
    """One chat call to the OpenAI-compatible endpoint, retried with backoff on transient
    errors (IncompleteRead / connection reset / timeout / 429 / 5xx). Always raises AisaError
    on failure, never a raw http.client exception, so callers can degrade gracefully."""
    import http.client
    import time
    url = os.environ.get("LLM_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1").rstrip("/") + "/chat/completions"
    model = os.environ.get("LLM_MODEL", "mimo-v2.6-pro")
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": max(max_tokens * 4, 4000), "messages": [
        {"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    last = ""
    for attempt in range(LLM_TRIES):
        if attempt:
            time.sleep(LLM_BACKOFF[min(attempt - 1, len(LLM_BACKOFF) - 1)])
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {os.environ['LLM_API_KEY']}", "User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=180) as res:
                data = json.load(res)
            return data["choices"][0]["message"]["content"] or ""
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', 'replace')[:200]
            # Permanent auth failures must not burn the retry budget (box: MiMo 401 for days).
            if exc.code in (401, 403):
                raise LLMError(f"LLM unavailable (HTTP {exc.code}): {body}") from exc
            last = f"LLM HTTP {exc.code}: {body}"
            if exc.code != 429 and exc.code < 500:
                break
        except (http.client.HTTPException, OSError, ValueError) as exc:   # IncompleteRead, reset, timeout, bad JSON
            last = f"LLM {type(exc).__name__}: {exc}"
        except (KeyError, IndexError, TypeError) as exc:
            last = f"LLM unexpected answer {type(exc).__name__}: {exc}"
            break
        print(f"[llm] attempt {attempt + 1}/{LLM_TRIES} failed: {last[:160]}", file=sys.stderr)
    raise LLMError(f"LLM unavailable: {last[:280]}")
