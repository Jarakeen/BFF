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


def test_dd_dot_ui_prefers_visible_polished_summary_row_over_hidden_compat_charts() -> None:
    source = Path("ui/performance_dashboard_dd_dot_support.py").read_text(encoding="utf-8")

    assert "def _visible_summary_layout(page):" in source
    assert 'getattr(page, "support_effects_card", None)' in source
    assert "visible_layout.addWidget(dot_card, 1)" in source
    assert "_add_dot_card_to_charts_layout(self.charts_widget.layout(), dot_card)" in source
