"""DataForSEO is locked off for good (Yoyo, 2026-10-29): no path in radar/ may reach it.
The runtime checks use the real aisa._post, saved here before conftest swaps it out."""
import ast
import re
from pathlib import Path

import pytest

from radar import aisa

REAL_POST = aisa._post
RADAR = Path(__file__).resolve().parent.parent / "radar"
SOURCES = {p.name: p.read_text() for p in RADAR.glob("*.py")}


def test_post_refuses_a_dataforseo_tool_before_reading_the_key(monkeypatch):
    def no_key():
        raise AssertionError("the key must not be read for a locked call")
    monkeypatch.setattr(aisa, "key", no_key)
    with pytest.raises(aisa.AisaError, match="locked off"):
        REAL_POST(aisa.ROUTER, {"calls": [{"call_id": "a", "tool": "post_dataforseo_serp_google_organic_live"}]}, 1)


def test_post_refuses_a_dataforseo_url(monkeypatch):
    monkeypatch.setattr(aisa, "key", lambda: (_ for _ in ()).throw(AssertionError("key read")))
    for url in ("https://api.dataforseo.com/v3/serp/google/organic/live", "https://api.aisa.one/apis/v1/dataforseo/x"):
        with pytest.raises(aisa.AisaError, match="locked off"):
            REAL_POST(url, {}, 1)


def test_rest_always_refuses():
    with pytest.raises(aisa.AisaError, match="locked off"):
        aisa.rest("dataforseo/domain_analytics/whois/overview/live", {"limit": 1})
    with pytest.raises(aisa.AisaError):
        aisa.rest()


def test_call_drops_dataforseo_and_spends_nothing(monkeypatch):
    sent = []
    monkeypatch.setattr(aisa, "_post", lambda *a, **k: sent.append(a) or {"results": []})
    assert aisa.call([{"call_id": "a", "tool": "post_dataforseo_labs_google_keyword_overview_live"}]) == ({}, 0)
    assert sent == []


def test_post_checks_the_lock_first():
    fn = next(n for n in ast.parse(SOURCES["aisa.py"]).body if isinstance(n, ast.FunctionDef) and n.name == "_post")
    first = fn.body[0]
    assert isinstance(first, ast.If) and "_dataforseo" in ast.unparse(first.test)


# --- static scan: no bypass anywhere in radar/ -----------------------------------

BYPASS = [
    (r"\baisa\.rest\s*\(", "aisa.rest() reaches DataForSEO around call()"),
    (r"\b_post\s*\(", "only aisa.py may call _post()"),
    (r"dataforseo\.com", "a direct DataForSEO URL"),
    (r"(import|from)\s+dataforseo", "the DataForSEO client"),
    (r"DATAFORSEO_(LOGIN|PASSWORD|API)", "DataForSEO credentials"),
    (r"/apis?/v\d+/dataforseo", "AIsa's DataForSEO REST passthrough"),
]


@pytest.mark.parametrize("pattern,why", BYPASS)
def test_no_dataforseo_path_in_radar(pattern, why):
    hits = [f"{name}:{i}" for name, text in SOURCES.items() for i, line in enumerate(text.splitlines(), 1)
            if re.search(pattern, line, re.I) and not (name == "aisa.py" and pattern == r"\b_post\s*\(")]
    assert not hits, f"{why}: {hits}"


def test_network_calls_outside_aisa_never_name_dataforseo():
    """urlopen in any other module must not be pointed at a DataForSEO host or path."""
    for name, text in SOURCES.items():
        if name == "aisa.py":
            continue
        for line in text.splitlines():
            if "urlopen" in line or "Request(" in line:
                assert "dataforseo" not in line.lower(), f"{name}: {line.strip()}"
