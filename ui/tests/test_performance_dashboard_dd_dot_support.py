from __future__ import annotations

from pathlib import Path


def test_dd_dot_ui_adds_observed_uptime_card_and_role_gate() -> None:
    source = Path("ui/performance_dashboard_dd_dot_support.py").read_text(encoding="utf-8")
    assert '"Observed DoT Uptime"' in source
    assert 'casefold() == "dps"' in source
    assert "ObservedDotUptimes" in source
    assert "periodic-damage ticks" in source


def test_dd_dot_ui_does_not_assume_charts_layout_is_always_a_grid() -> None:
    source = Path("ui/performance_dashboard_dd_dot_support.py").read_text(encoding="utf-8")

    assert "isinstance(layout, QGridLayout)" in source
    assert "layout.addWidget(dot_card, 3, 0, 1, 2)" in source
    assert "layout.addWidget(dot_card)" in source
