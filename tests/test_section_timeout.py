"""The per-section alarm must stop a section even when its code catches OSError
(TimeoutError is an OSError: it used to be swallowed, and the alarm rings once)."""
import time

from radar import __main__ as cli


def test_section_timeout_is_not_swallowed_by_except_oserror(monkeypatch):
    monkeypatch.setenv("RADAR_SECTION_TIMEOUT", "1")
    after = []

    def stubborn():
        for _ in range(3):
            try:
                time.sleep(2)
            except OSError:                  # what goanyapi / feeds / page_age do
                after.append("swallowed")
            except Exception:                # and the broad handlers
                after.append("swallowed")
        return {"done": True}

    t0 = time.monotonic()
    out = cli.run(stubborn)
    assert "SectionTimeout" in out.get("error", "")
    assert after == [] and time.monotonic() - t0 < 2.5


def test_section_timeout_is_not_an_oserror_or_exception():
    assert not issubclass(cli.SectionTimeout, Exception)
