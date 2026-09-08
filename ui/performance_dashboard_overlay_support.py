from __future__ import annotations

"""Selectable effect controls for the ESO Logs performance graph.

The current PerformanceSnapshot only contains aggregate uptime totals, not exact
per-effect on/off intervals. These controls therefore own *selection state* for
future timeline lanes without inventing fake interval data. They also keep the
visible graph choices disciplined: no more than six effects may be selected at
once.
"""

from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QWidget

from ui.components.foundry_card import FoundryCard
from ui.theme.colors import Colors

_INSTALLED = False
_MAX_GRAPH_EFFECTS = 6

_DEFAULT_GRAPH_EFFECTS = (
    "Major Brittle",
    "Minor Berserk",
    "Major Courage",
    "Major Slayer",
)


def _selected_names(page) -> list[str]:
    return [
        name
        for name, checkbox in getattr(page, "graph_effect_checkboxes", {}).items()
        if checkbox.isChecked()
    ]


def _set_graph_selection(page, name: str, checked: bool) -> None:
    selected = _selected_names(page)
    checkbox = page.graph_effect_checkboxes.get(name)
    if checkbox is None:
        return

    if checked and name not in selected and len(selected) >= _MAX_GRAPH_EFFECTS:
        checkbox.blockSignals(True)
        checkbox.setChecked(False)
        checkbox.blockSignals(False)
        page.graph_effect_limit_label.setText(
            f"Maximum {_MAX_GRAPH_EFFECTS} effects on the graph. Uncheck one to add another."
        )
        return

    page._graph_effect_names = _selected_names(page)
    _refresh_graph_effect_status(page)


def _refresh_graph_effect_status(page) -> None:
    names = list(getattr(page, "_graph_effect_names", ()))
    label = getattr(page, "graph_effect_limit_label", None)
    if label is not None:
        label.setText(
            f"{len(names)} / {_MAX_GRAPH_EFFECTS} selected"
            if names
            else f"Select up to {_MAX_GRAPH_EFFECTS} effects"
        )

    snapshot = getattr(page, "_last_snapshot", None)
    summary = getattr(page, "graph_effect_summary_label", None)
    if summary is None:
        return

    if snapshot is None or not names:
        summary.setText("Load a fight to use these effect selections with the output graph.")
        return

    # Aggregate percentages are honest here; exact timeline intervals are not
    # yet present in PerformanceSnapshot, so do not fabricate colored time bands.
    try:
        from ui.performance_dashboard_polish_support import _tracked_results

        results = _tracked_results(snapshot, names)
    except Exception:
        results = []

    pieces = []
    for result in results:
        if result.uptime_percent is None:
            pieces.append(f"{result.name}: not found")
        else:
            pieces.append(f"{result.name}: {result.uptime_percent:.1f}%")
    summary.setText("  •  ".join(pieces) if pieces else "No selected effect data found.")


def _build_graph_effect_card(page) -> FoundryCard:
    card = FoundryCard("Graph Effects")
    card.set_body_margins(10, 5, 10, 6)

    intro_row = QHBoxLayout()
    intro = QLabel("Show up to six support effects with this fight view")
    intro.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
    intro_row.addWidget(intro)
    intro_row.addStretch(1)

    page.graph_effect_limit_label = QLabel()
    page.graph_effect_limit_label.setStyleSheet(f"color: {Colors.GOLD_LIGHT};")
    intro_row.addWidget(page.graph_effect_limit_label)
    card.addLayout(intro_row)

    choices = QWidget()
    choice_layout = QHBoxLayout(choices)
    choice_layout.setContentsMargins(0, 0, 0, 0)
    choice_layout.setSpacing(12)

    page.graph_effect_checkboxes = {}
    available = list(getattr(page, "_tracked_effect_names", ()))
    if not available:
        available = list(_DEFAULT_GRAPH_EFFECTS)

    # Include sensible raid-support defaults without producing another wall of
    # controls. Tracked effects added elsewhere can still replace these on a
    # subsequent dashboard construction.
    for fallback in ("Major Vulnerability", "Major Force"):
        if fallback not in available:
            available.append(fallback)

    for name in available[:_MAX_GRAPH_EFFECTS]:
        checkbox = QCheckBox(name)
        checkbox.setChecked(name in _DEFAULT_GRAPH_EFFECTS)
        checkbox.toggled.connect(
            lambda checked, effect=name, owner=page: _set_graph_selection(owner, effect, checked)
        )
        page.graph_effect_checkboxes[name] = checkbox
        choice_layout.addWidget(checkbox)

    choice_layout.addStretch(1)
    card.addWidget(choices)

    page._graph_effect_names = _selected_names(page)
    page.graph_effect_summary_label = QLabel()
    page.graph_effect_summary_label.setWordWrap(True)
    page.graph_effect_summary_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px;")
    card.addWidget(page.graph_effect_summary_label)
    _refresh_graph_effect_status(page)
    return card


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from widgets.performance_dashboard import PerformanceDashboard

    original_build_ui = PerformanceDashboard.build_ui
    original_show_snapshot = PerformanceDashboard.show_snapshot

    def build_ui_with_graph_effects(self):
        original_build_ui(self)
        root = self.layout()
        output_card = getattr(self, "output_card", None)
        if root is None or output_card is None:
            return
        index = root.indexOf(output_card)
        self.graph_effect_card = _build_graph_effect_card(self)
        root.insertWidget(max(index, 0), self.graph_effect_card)

    def show_snapshot_with_graph_effects(self, snapshot):
        original_show_snapshot(self, snapshot)
        _refresh_graph_effect_status(self)

    PerformanceDashboard.build_ui = build_ui_with_graph_effects
    PerformanceDashboard.show_snapshot = show_snapshot_with_graph_effects
    _INSTALLED = True
