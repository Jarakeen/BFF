from __future__ import annotations

from pathlib import Path


def test_dd_dot_ui_adds_observed_uptime_card_and_role_gate() -> None:
    source = Path("ui/performance_dashboard_dd_dot_support.py").read_text(encoding="utf-8")
    assert '"Observed DoT Uptime"' in source
    assert 'casefold() == "dps"' in source
    assert "ObservedDotUptimes" in source
    assert "periodic-damage ticks" in source
