"""⑨ feeds, ported from upstream 0.6.0 (free sources only; google_new / trending removed)."""
import json
from datetime import date
from pathlib import Path

from radar import __main__ as cli
from radar import config, feeds, report

PH = """<feed><entry><title>Lumen Notes</title><link rel="alternate" href="https://www.producthunt.com/products/lumen"/>
<content>&lt;p&gt;AI notes&lt;/p&gt;</content><published>2020-01-01T00:00:00Z</published></entry></feed>"""


def test_free_feeds_snapshot_first_then_report_what_is_new(cfg, tmp_path, monkeypatch):
    cfg["feeds"]["enabled"] = ["producthunt", "hn", "openrouter", "awesome"]
    cfg["feeds"]["awesome"] = ["https://raw.example/README.md"]
    now = int(feeds.time.time())
    pages = {"https://www.producthunt.com/feed": PH,
             "https://openrouter.ai/api/v1/models": json.dumps({"data": [{"id": "x/pareto", "name": "Unbiased: Pareto 26.9", "created": now}]}),
             "https://raw.example/README.md": "- [Notchlive](https://captions-demo.app) - live captions\n"}

    def get(url):
        if "hn.algolia" in url:
            return json.dumps({"hits": [{"objectID": "9", "title": "Show HN: Quarry – SQL for spreadsheets", "points": 80}]}).encode()
        return pages[url].encode()
    monkeypatch.setattr(feeds, "get", get)
    first = feeds.feeds(cfg, tmp_path, today=date(2026, 10, 14))
    assert set(first["first_run"]) == {"producthunt", "hn", "openrouter", "awesome"}
    assert sorted(x["term"] for x in first["terms"]) == ["pareto 26.9", "quarry"]
    pages["https://raw.example/README.md"] += "- [Pixdemo](https://pixdemo.app) - prompts behind images\n"
    again = feeds.feeds(cfg, tmp_path, today=date(2026, 10, 15))
    assert [x["term"] for x in again["terms"]] == ["pixdemo"] and again["cost_micros"] == 0 and again["credits"] == 0


def test_cap_per_feed_is_eight(cfg, tmp_path, monkeypatch):
    assert config.DEFAULTS["feeds"]["max_per_feed"] == 8
    cfg["feeds"]["enabled"] = ["hn"]
    hits = [{"objectID": str(i), "title": f"Show HN: Tool{i} – x", "points": 100 + i} for i in range(20)]
    monkeypatch.setattr(feeds, "get", lambda url: json.dumps({"hits": hits}).encode())
    got = feeds.feeds(cfg, tmp_path, today=date(2026, 10, 14))
    assert len(got["new"]["hn"]) == 8 and got["new"]["hn"][0]["name"] == "Tool19"


def test_paid_feeds_are_gone_and_defaults_are_free():
    assert "google_new" not in feeds.FEEDS and "trending" not in feeds.FEEDS
    d = config.DEFAULTS["feeds"]
    assert not {"rising", "civitai", "google_new", "trending"} & set(d["enabled"])
    assert "google_new" not in d and "trending" not in d
    assert "aisa" not in Path(feeds.__file__).read_text().split("import")[1].split("\n")[0]


def test_old_config_naming_a_removed_feed_is_an_error_not_a_call(cfg, tmp_path, monkeypatch):
    cfg["feeds"]["enabled"] = ["google_new", "trending"]
    got = feeds.feeds(cfg, tmp_path, today=date(2026, 10, 14))
    assert len(got["errors"]) == 2 and got["terms"] == []


def test_rising_weekly_four_seeds_one_at_a_time_failures_kept_apart(cfg, tmp_path, monkeypatch):
    cfg["feeds"]["enabled"], cfg["feeds"]["weekly"], cfg["feeds"]["weekday"] = ["rising"], ["rising"], 0
    cfg["feeds"]["seeds"] = ["ai generator", "ai detector", "ai converter", "ai maker", "ai checker", "ai editor"]
    asked = []

    def rq(seed):
        asked.append(seed)
        if seed == "ai detector":
            raise feeds.goanyapi.GoAnyError("HTTP 500")
        return {"rising": [f"{seed} free", "best pizza near me"]}, 6
    monkeypatch.setattr(feeds.goanyapi, "related_queries", rq)
    assert feeds.feeds(cfg, tmp_path, today=date(2026, 10, 14))["read"] == {} and asked == []      # a Wednesday
    got = feeds.feeds(cfg, tmp_path, today=date(2026, 10, 19))                                     # a Monday
    assert asked == cfg["feeds"]["seeds"][:4]
    assert got["credits"] == 18 and any("ai detector" in e for e in got["errors"])
    assert {x["term"] for x in got["terms"]} == {"ai generator free", "ai converter free", "ai maker free"}


def test_feeds_run_in_daily_not_in_sources():
    src = Path(cli.__file__).read_text()
    sources_fn = src[src.index("def cmd_sources"):src.index("def cmd_daily")]
    daily_fn = src[src.index("def cmd_daily"):src.index("def keyword_table")]
    assert "feeds." not in sources_fn and "feeds.feeds(" in daily_fn


def test_feed_terms_never_reach_the_keyword_table():
    from radar import usecases
    assert "feed" not in usecases.READ_KINDS


def test_feed_lines_in_the_report(cfg):
    fd = {"new": {"hn": [{"name": "Quarry", "url": "https://q.example", "about": ""}]}, "first_run": ["awesome"],
          "errors": ["producthunt: HTTP Error 403"]}
    text = "\n".join(report._feed_lines(fd))
    assert "[Quarry](https://q.example)" in text and "403" in text
