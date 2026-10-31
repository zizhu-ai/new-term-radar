# Box fork: upstream sync notes

**Synced against upstream zhuyansen/new-term-radar up to `3cf6515` (0.6.1), 2026-10-31.**
Next time, review only `git log 3cf6515..origin/main`. No merge, no `merge -s ours`: hand-ported.

Taken (adapted):
- `e1ce49e` (0.6.0), only `radar/feeds.py` free sources: Product Hunt, Show HN, OpenRouter, App Store, awesome lists.
  Daily run only (`sources` fast line unchanged). Civitai off. 8 a feed. `google_new` (DataForSEO) and
  `trending` (paid AIsa) removed from code. `rising` (GoAnyAPI) off; if enabled: weekly, <= 4 seeds, serial, per-seed try.
  Feed terms stay out of `usecases.READ_KINDS`, so no GoAnyAPI keyword lookups.
- `d209a52` page-one site age (RDAP, free, recorded only), capped at 30 lookups a run, stop after 3 consecutive failures.

Not taken:
- `8f6c10a` (aisa.rest whois passthrough: bypasses the DataForSEO lock, overwrites new_sites' Columbus branch). Never.
- the rest of `e1ce49e` (wordage, markets, serpshape, sellers, site_words, sidelights, ai_answers: DataForSEO; money: GoAnyAPI points).
- `802db20` (silently falls back to the example config), `4fd9a0d` (says DataForSEO Trends; box review uses GoAnyAPI),
  `5ec2c47` sellers, `fa37e3c`/`399feef`, and all docs / plugin / MCP / README commits.

Box-only hardening done with this sync:
- DataForSEO lock moved into `aisa._post()` (URL or tool name, before the key is read); `aisa.rest()` always refuses;
  `tests/test_dataforseo_lock.py` scans `radar/` for any DataForSEO path or bypass. The report footer prints DataForSEO $0.
- Per-section alarm raises `SectionTimeout(BaseException)`; `TimeoutError` was an `OSError` and got swallowed.
