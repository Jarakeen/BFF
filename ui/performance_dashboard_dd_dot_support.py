from __future__ import annotations

"""DD-only observed DoT uptime presentation for Performance Dashboard."""

from ui.theme.colors import Colors

_INSTALLED = False
_ORIGINAL_BUILD_UI = None
_ORIGINAL_SHOW_SNAPSHOT = None


def _build_ui_with_dot_card(self):
    assert _ORIGINAL_BUILD_UI is not None
    _ORIGINAL_BUILD_UI(self)

    dot_card, self.dot_chart_view = self._build_chart_card(
        "Observed DoT Uptime", compact=True
    )
    self.dot_card = dot_card

    grid = self.charts_widget.layout()
    if grid is not None:
        grid.addWidget(dot_card, 3, 0, 1, 2)
    dot_card.setVisible(False)


def _show_snapshot_with_dot(self, snapshot):
    assert _ORIGINAL_SHOW_SNAPSHOT is not None
    _ORIGINAL_SHOW_SNAPSHOT(self, snapshot)

    is_dd = str(getattr(snapshot, "Role", "")).casefold() == "dps"
    self.dot_card.setVisible(is_dd)
    if not is_dd:
        return

    basis = "boss-active" if getattr(snapshot, "BossActiveSeconds", None) is not None else "full fight"
    self.dot_card.title_label.setText(f"Observed DoT Uptime ({basis})")

    rows = list(getattr(snapshot, "ObservedDotUptimes", []) or [])
    self._update_uptime_chart(self.dot_chart_view, rows, Colors.WARNING)

    note = str(getattr(snapshot, "DotAnalysisNote", "") or "").strip()
    tooltip = (
        "Estimated from real ESO Logs periodic-damage ticks. Numeric ability IDs are "
        "used only for temporary within-report correlation; readable ability names are "
        "the displayed identity. Long tick gaps split uptime windows."
    )
    if note:
        tooltip += f"\n\n{note}"
    self.dot_card.setToolTip(tooltip)


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_UI, _ORIGINAL_SHOW_SNAPSHOT
    if _INSTALLED:
        return

    from widgets.performance_dashboard import PerformanceDashboard

    _ORIGINAL_BUILD_UI = PerformanceDashboard.build_ui
    _ORIGINAL_SHOW_SNAPSHOT = PerformanceDashboard.show_snapshot

    PerformanceDashboard.build_ui = _build_ui_with_dot_card
    PerformanceDashboard.show_snapshot = _show_snapshot_with_dot
    _INSTALLED = True

    # Crit/contribution UI -> observed DoT -> observed LA pairing.
    from ui.performance_dashboard_dd_weave_support import install as install_weave_ui

    install_weave_ui()
