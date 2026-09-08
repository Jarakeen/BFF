from __future__ import annotations

"""Selectable effect controls for the ESO Logs performance graph.

The graph can show at most six effect lanes at once, but those six are user
choices rather than a fixed raid-support preset.  A compact picker lets a player
add class/build-specific effects (for example a Warden watching Major Mending),
while unchecking an existing lane frees a graph slot without losing the option.
"""

from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QWidget

from ui.components.foundry_button import ButtonRole, FoundryButton
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


def _refresh_timeline_widget(page) -> None:
    widget = getattr(page, "effect_timeline_widget", None)
    if widget is not None:
        widget.refresh()


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
    _refresh_timeline_widget(page)


def _add_graph_effect_checkbox(page, name: str, *, checked: bool = True) -> None:
    name = str(name or "").strip()
    if not name:
        return

    existing = getattr(page, "graph_effect_checkboxes", {}).get(name)
    if existing is not None:
        if checked:
            existing.setChecked(True)
        return

    if checked and len(_selected_names(page)) >= _MAX_GRAPH_EFFECTS:
        page.graph_effect_limit_label.setText(
            f"Maximum {_MAX_GRAPH_EFFECTS} effects on the graph. Uncheck one to add another."
        )
        return

    checkbox = QCheckBox(name)
    checkbox.setChecked(checked)
    checkbox.toggled.connect(
        lambda state, effect=name, owner=page: _set_graph_selection(owner, effect, state)
    )
    page.graph_effect_checkboxes[name] = checkbox
    page.graph_effect_choice_layout.insertWidget(
        max(0, page.graph_effect_choice_layout.count() - 1), checkbox
    )
    page._graph_effect_names = _selected_names(page)
    _refresh_graph_effect_status(page)
    _refresh_timeline_widget(page)


def _add_graph_effect_from_picker(page) -> None:
    picker = getattr(page, "graph_effect_picker", None)
    if picker is None:
        return
    _add_graph_effect_checkbox(page, picker.currentText(), checked=True)


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
    intro = QLabel("Choose up to six support effects to show with this fight")
    intro.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
    intro_row.addWidget(intro)
    intro_row.addStretch(1)

    page.graph_effect_limit_label = QLabel()
    page.graph_effect_limit_label.setStyleSheet(f"color: {Colors.GOLD_LIGHT};")
    intro_row.addWidget(page.graph_effect_limit_label)
    card.addLayout(intro_row)

    picker_row = QHBoxLayout()
    picker_row.setSpacing(6)
    page.graph_effect_picker = QComboBox()
    page.graph_effect_picker.setEditable(True)
    try:
        from ui.performance_dashboard_polish_support import _SUPPORT_EFFECT_PRESETS

        page.graph_effect_picker.addItems(list(_SUPPORT_EFFECT_PRESETS))
    except Exception:
        page.graph_effect_picker.addItems(list(_DEFAULT_GRAPH_EFFECTS))
    page.graph_effect_picker.setCurrentText("Major Mending")
    picker_row.addWidget(page.graph_effect_picker, 1)

    add_button = FoundryButton("+ Add to Graph", role=ButtonRole.SECONDARY, compact=True)
    add_button.clicked.connect(lambda *_: _add_graph_effect_from_picker(page))
    picker_row.addWidget(add_button)
    card.addLayout(picker_row)

    choices = QWidget()
    choice_layout = QHBoxLayout(choices)
    choice_layout.setContentsMargins(0, 0, 0, 0)
    choice_layout.setSpacing(12)
    page.graph_effect_choice_layout = choice_layout

    page.graph_effect_checkboxes = {}
    available = list(getattr(page, "_tracked_effect_names", ()))
    if not available:
        available = list(_DEFAULT_GRAPH_EFFECTS)

    for fallback in ("Major Vulnerability", "Major Force"):
        if fallback not in available:
            available.append(fallback)

    choice_layout.addStretch(1)
    for name in available[:_MAX_GRAPH_EFFECTS]:
        _add_graph_effect_checkbox(
            page,
            name,
            checked=name in _DEFAULT_GRAPH_EFFECTS,
        )

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
        _refresh_timeline_widget(self)

    PerformanceDashboard.build_ui = build_ui_with_graph_effects
    PerformanceDashboard.show_snapshot = show_snapshot_with_graph_effects
    _INSTALLED = True
