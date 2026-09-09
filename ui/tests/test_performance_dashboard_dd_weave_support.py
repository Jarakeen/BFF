from __future__ import annotations

from pathlib import Path

from ui.performance_dashboard_dd_weave_support import _weave_value_text


def test_weave_value_text_shows_pairing_counts() -> None:
    assert _weave_value_text(92.4, 121, 131) == "92.4% (121/131)"
    assert _weave_value_text(None, 0, 0) == "Unavailable"


def test_weave_support_uses_observed_pairing_language() -> None:
    source = Path("ui/performance_dashboard_dd_weave_support.py").read_text(encoding="utf-8")
    assert '_StatBlock("LA Pairing")' in source
    assert "Observed Light Attack pairing" in source
    assert "Median LA→skill delay" in source
    assert "within 1.2 seconds" in source
