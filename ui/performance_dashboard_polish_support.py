from __future__ import annotations

"""Presentation cleanup for the ESO Logs Performance Dashboard.

Keeps the existing ESO Logs service/model contract intact while replacing the
wall-of-bars layout with a compact two-column command surface and a readable
support-effect focus list.
"""

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtCharts import QChartView
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from models.performance_model import AbilityUptime
from ui.components.foundry_button import ButtonRole, FoundryButton
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_empty_state import FoundryEmptyState
from ui.theme.colors import Colors

_INSTALLED = False
_ORIGINAL_SHOW_SNAPSHOT = None
_ORIGINAL_LOAD = None

_SUPPORT_EFFECT_PRESETS = (
    "Major Brittle",
    "Minor Berserk",
    "Major Courage",
    "Major Slayer",
    "Major Vulnerability",
    "Minor Vulnerability",
    "Major Force",
    "Minor Force",
    "Major Breach",
    "Minor Breach",
    "Off Balance",
    "Major Resolve",
    "Minor Resolve",
    "Major Protection",
    "Minor Protection",
    "Major Mending",
    "Minor Mending",
    "Empower",
)

_DEFAULT_TRACKED_EFFECTS = (
    "Major Brittle",
    "Minor Berserk",
    "Major Courage",
    "Major Slayer",
)


@dataclass(frozen=True)
class _TrackedEffectResult:
    name: str
    source: str
    uptime_percent: float | None


class _EffectRow(QWidget):
    def __init__(self, result: _TrackedEffectResult, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 1, 0, 1)
        row.setSpacing(8)

        name = QLabel(result.name)
        name.setMinimumWidth(130)
        name.setStyleSheet(f"color: {Colors.TEXT};")

        source = QLabel(result.source)
        source.setMinimumWidth(78)
        source.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px;")

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        value = QLabel()
        value.setFixedWidth(48)
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        if result.uptime_percent is None:
            bar.setValue(0)
            value.setText("—")
            value.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
            bar.setStyleSheet(
                f"QProgressBar {{ background-color: {Colors.SURFACE_LIGHT}; border: none; border-radius: 4px; }}"
                f"QProgressBar::chunk {{ background-color: {Colors.TEXT_MUTED}; border-radius: 4px; }}"
            )
        else:
            pct = max(0.0, min(100.0, result.uptime_percent))
            bar.setValue(int(round(pct)))
            value.setText(f"{pct:.1f}%")
            value.setStyleSheet(f"color: {Colors.GOLD_LIGHT};")
            bar.setStyleSheet(
                f"QProgressBar {{ background-color: {Colors.SURFACE_LIGHT}; border: none; border-radius: 4px; }}"
                f"QProgressBar::chunk {{ background-color: {Colors.ACCENT_LIGHT}; border-radius: 4px; }}"
            )

        row.addWidget(name)
        row.addWidget(source)
        row.addWidget(bar, 1)
        row.addWidget(value)


def _index_uptimes(snapshot) -> dict[str, tuple[str, AbilityUptime]]:
    """Return one best readable entry per effect name.

    Raid-wide data wins ties because it best represents support coverage for the
    whole group; otherwise keep the higher observed uptime.
    """
    indexed: dict[str, tuple[str, AbilityUptime]] = {}
    groups = (
        ("Your Buff", snapshot.BuffUptimes),
        ("You Applied", snapshot.DebuffUptimes),
        ("Raid-Wide", snapshot.RaidDebuffUptimes),
    )
    priority = {"Your Buff": 0, "You Applied": 1, "Raid-Wide": 2}

    for source, values in groups:
        for uptime in values:
            key = uptime.Name.strip().casefold()
            if not key:
                continue
            current = indexed.get(key)
            if current is None:
                indexed[key] = (source, uptime)
                continue
            current_source, current_uptime = current
            if (
                uptime.UptimePercent > current_uptime.UptimePercent
                or (
                    uptime.UptimePercent == current_uptime.UptimePercent
                    and priority[source] > priority[current_source]
                )
            ):
                indexed[key] = (source, uptime)
    return indexed


def _tracked_results(snapshot, names: list[str]) -> list[_TrackedEffectResult]:
    indexed = _index_uptimes(snapshot)
    results: list[_TrackedEffectResult] = []
    for name in names:
        found = indexed.get(name.strip().casefold())
        if found is None:
            results.append(_TrackedEffectResult(name=name, source="Not found", uptime_percent=None))
        else:
            source, uptime = found
            results.append(
                _TrackedEffectResult(
                    name=uptime.Name or name,
                    source=source,
                    uptime_percent=float(uptime.UptimePercent),
                )
            )
    return results


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


def _render_tracked_effects(page) -> None:
    layout = getattr(page, "support_effects_layout", None)
    if layout is None:
        return
    _clear_layout(layout)

    snapshot = getattr(page, "_last_snapshot", None)
    tracked = list(getattr(page, "_tracked_effect_names", _DEFAULT_TRACKED_EFFECTS))

    if snapshot is None:
        placeholder = QLabel(
            "Load a fight to compare the support effects you actually care about."
        )
        placeholder.setWordWrap(True)
        placeholder.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        layout.addWidget(placeholder)
        return

    for result in _tracked_results(snapshot, tracked):
        layout.addWidget(_EffectRow(result))


def _render_tracking_label(page) -> None:
    label = getattr(page, "tracked_effects_label", None)
    if label is None:
        return
    names = list(getattr(page, "_tracked_effect_names", ()))
    label.setText("Watching: " + "  •  ".join(names) if names else "Watching: none")


def _add_tracked_effect(page) -> None:
    combo = page.tracked_effect_picker
    name = combo.currentText().strip()
    if not name:
        return
    names = list(getattr(page, "_tracked_effect_names", ()))
    if name.casefold() not in {value.casefold() for value in names}:
        names.append(name)
        page._tracked_effect_names = names[:8]
    _render_tracking_label(page)
    _render_tracked_effects(page)


def _reset_tracked_effects(page) -> None:
    page._tracked_effect_names = list(_DEFAULT_TRACKED_EFFECTS)
    _render_tracking_label(page)
    _render_tracked_effects(page)


def _build_source_card(page) -> FoundryCard:
    card = FoundryCard("Report Source")
    card.set_body_margins(10, 6, 10, 8)

    page.member_name = QLineEdit()
    page.member_name.setPlaceholderText("Tab label")
    page.member_name.textChanged.connect(page.nameChanged.emit)

    page.report_code = QLineEdit()
    page.report_code.setPlaceholderText("ESO Logs report URL or code")

    page.fight_id = QLineEdit()
    page.fight_id.setPlaceholderText("#")
    page.fight_id.setFixedWidth(70)

    page.load_fight_button = FoundryButton(
        "Load Fight", role=ButtonRole.PRIMARY, compact=True
    )
    page.load_fight_button.clicked.connect(page.loadFightRequested.emit)

    page.who_am_i = QComboBox()
    page.who_am_i.setEnabled(False)
    page.who_am_i.currentIndexChanged.connect(page._on_actor_selected)

    page.role_override = QComboBox()
    page.role_override.addItems(["Healer", "DPS", "Tank"])
    page.role_override.setMaximumWidth(120)

    page.show_button = FoundryButton(
        "Show My Performance", role=ButtonRole.SUCCESS, compact=True
    )
    page.show_button.setEnabled(False)
    page.show_button.clicked.connect(page.showPerformanceRequested.emit)

    form = QFormLayout()
    form.setHorizontalSpacing(8)
    form.setVerticalSpacing(6)
    form.addRow("Member", page.member_name)

    report_row = QHBoxLayout()
    report_row.setSpacing(6)
    report_row.addWidget(page.report_code, 1)
    report_row.addWidget(QLabel("Fight"))
    report_row.addWidget(page.fight_id)
    report_row.addWidget(page.load_fight_button)
    form.addRow("Report", report_row)

    who_row = QHBoxLayout()
    who_row.setSpacing(6)
    who_row.addWidget(page.who_am_i, 1)
    who_row.addWidget(page.role_override)
    who_row.addWidget(page.show_button)
    form.addRow("Who Am I?", who_row)

    page.immunity_toggle = QCheckBox("Boss has an immunity phase")
    page.immunity_toggle.setToolTip(
        "When enabled, use the configured ESO Logs effect marker to compute boss-active time."
    )

    page.immunity_buff_name = QLineEdit()
    page.immunity_buff_name.setPlaceholderText("Immunity effect marker")
    page.immunity_buff_name.setMaximumWidth(220)

    page.immunity_buff_kind = QComboBox()
    page.immunity_buff_kind.addItems(["Buff", "Debuff"])
    page.immunity_buff_kind.setMaximumWidth(95)

    immunity_row = QHBoxLayout()
    immunity_row.setSpacing(6)
    immunity_row.addWidget(page.immunity_toggle)
    immunity_row.addStretch(1)
    immunity_row.addWidget(page.immunity_buff_name)
    immunity_row.addWidget(page.immunity_buff_kind)
    form.addRow("Boss Immunity", immunity_row)

    def sync_immunity_fields(checked: bool) -> None:
        page.immunity_buff_name.setVisible(checked)
        page.immunity_buff_kind.setVisible(checked)

    page.immunity_toggle.toggled.connect(sync_immunity_fields)
    sync_immunity_fields(False)

    card.addLayout(form)

    page.fight_summary_label = QLabel("No fight loaded yet.")
    page.fight_summary_label.setWordWrap(True)
    page.fight_summary_label.setStyleSheet(f"color: {Colors.GOLD_LIGHT};")
    card.addWidget(page.fight_summary_label)
    return card


def _build_tracking_card(page) -> FoundryCard:
    card = FoundryCard("Track Specific Buffs / Debuffs")
    card.set_body_margins(10, 6, 10, 8)

    intro = QLabel(
        "Choose the raid-support effects worth watching instead of staring at anonymous bars."
    )
    intro.setWordWrap(True)
    intro.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
    card.addWidget(intro)

    picker_row = QHBoxLayout()
    picker_row.setSpacing(6)
    page.tracked_effect_picker = QComboBox()
    page.tracked_effect_picker.setEditable(True)
    page.tracked_effect_picker.addItems(_SUPPORT_EFFECT_PRESETS)
    page.tracked_effect_picker.setCurrentText("Major Brittle")
    picker_row.addWidget(page.tracked_effect_picker, 1)

    add = FoundryButton("+ Add", role=ButtonRole.SECONDARY, compact=True)
    add.clicked.connect(lambda *_: _add_tracked_effect(page))
    picker_row.addWidget(add)

    reset = FoundryButton("Reset", role=ButtonRole.SECONDARY, compact=True)
    reset.clicked.connect(lambda *_: _reset_tracked_effects(page))
    picker_row.addWidget(reset)
    card.addLayout(picker_row)

    page.tracked_effects_label = QLabel()
    page.tracked_effects_label.setWordWrap(True)
    page.tracked_effects_label.setStyleSheet(f"color: {Colors.GOLD_LIGHT};")
    card.addWidget(page.tracked_effects_label)
    _render_tracking_label(page)
    return card


def _build_support_effects_card(page) -> FoundryCard:
    card = FoundryCard("Support Effect Uptime")
    card.set_body_margins(10, 6, 10, 8)
    host = QWidget()
    page.support_effects_layout = QVBoxLayout(host)
    page.support_effects_layout.setContentsMargins(0, 0, 0, 0)
    page.support_effects_layout.setSpacing(4)
    card.addWidget(host)
    _render_tracked_effects(page)
    return card


def _build_quick_read_card(page) -> FoundryCard:
    card = FoundryCard("Quick Read")
    card.set_body_margins(10, 6, 10, 8)
    page.quick_read_label = QLabel(
        "Load a fight and the useful support takeaways will live here."
    )
    page.quick_read_label.setWordWrap(True)
    page.quick_read_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
    card.addWidget(page.quick_read_label)
    return card


def _update_quick_read(page, snapshot) -> None:
    results = _tracked_results(snapshot, list(page._tracked_effect_names))
    present = [r for r in results if r.uptime_percent is not None]
    missing = [r.name for r in results if r.uptime_percent is None]

    lines: list[str] = []
    if present:
        strongest = max(present, key=lambda r: r.uptime_percent or 0.0)
        weakest = min(present, key=lambda r: r.uptime_percent or 0.0)
        lines.append(
            f"Best tracked coverage: {strongest.name} at {strongest.uptime_percent:.1f}%."
        )
        if weakest.name != strongest.name:
            lines.append(
                f"Lowest tracked coverage: {weakest.name} at {weakest.uptime_percent:.1f}%."
            )
    if missing:
        lines.append("Not found in this fetched effect set: " + ", ".join(missing) + ".")
    if snapshot.BossActiveSeconds is not None:
        lines.append(
            f"Uptime basis is boss-active time ({snapshot.BossActiveSeconds:.0f}s of {snapshot.FightDurationSeconds:.0f}s)."
        )
    else:
        lines.append("Uptime basis is the full fight.")

    page.quick_read_label.setText("\n".join(lines))


def _build_ui_clean(self) -> None:
    from widgets import performance_dashboard as dashboard_module

    self._tracked_effect_names = list(_DEFAULT_TRACKED_EFFECTS)

    root = QVBoxLayout(self)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(10)

    top = QWidget()
    top_layout = QHBoxLayout(top)
    top_layout.setContentsMargins(0, 0, 0, 0)
    top_layout.setSpacing(10)
    top_layout.addWidget(_build_source_card(self), 1)
    top_layout.addWidget(_build_tracking_card(self), 1)
    root.addWidget(top)

    self.kpi_card = self._build_kpi_card()
    self.support_effects_card = _build_support_effects_card(self)

    summary = QWidget()
    summary_layout = QHBoxLayout(summary)
    summary_layout.setContentsMargins(0, 0, 0, 0)
    summary_layout.setSpacing(10)
    summary_layout.addWidget(self.kpi_card, 1)
    summary_layout.addWidget(self.support_effects_card, 1)
    root.addWidget(summary)

    output_card, self.output_chart_view = self._build_chart_card("Output Over Time")
    self.output_card = output_card
    root.addWidget(output_card)

    # Keep the original chart objects alive for compatibility with show_snapshot,
    # but do not put the unreadable category charts in the visible layout.
    self.buff_card, self.buff_chart_view = self._build_chart_card("Your Buff Uptime", compact=True)
    self.debuff_card, self.debuff_chart_view = self._build_chart_card("Debuffs You Applied", compact=True)
    self.raid_debuff_card, self.raid_debuff_chart_view = self._build_chart_card("Boss Debuffs (Raid-Wide)", compact=True)
    self.buff_card.hide()
    self.debuff_card.hide()
    self.raid_debuff_card.hide()

    abilities_card, self.abilities_list_layout = self._build_ability_list_card("Top Abilities")
    self.abilities_card = abilities_card
    self.quick_read_card = _build_quick_read_card(self)

    lower = QWidget()
    lower_layout = QHBoxLayout(lower)
    lower_layout.setContentsMargins(0, 0, 0, 0)
    lower_layout.setSpacing(10)
    lower_layout.addWidget(abilities_card, 1)
    lower_layout.addWidget(self.quick_read_card, 1)
    root.addWidget(lower)

    # Original visibility plumbing expects one charts_widget container.
    self.charts_widget = QWidget()
    hidden_layout = QVBoxLayout(self.charts_widget)
    hidden_layout.setContentsMargins(0, 0, 0, 0)
    self.charts_widget.setVisible(False)

    self.empty_state = FoundryEmptyState(
        "Load a fight, pick who you are in it, then Show My Performance."
    )
    root.addWidget(self.empty_state)

    # The cleaned dashboard keeps the source/tracking controls visible before a
    # result exists; result cards are hidden until a snapshot is loaded.
    self.kpi_card.setVisible(False)
    self.support_effects_card.setVisible(False)
    self.output_card.setVisible(False)
    self.abilities_card.setVisible(False)
    self.quick_read_card.setVisible(False)
    self.empty_state.setVisible(True)


def _set_results_visible_clean(self, visible: bool) -> None:
    self.kpi_card.setVisible(visible)
    self.support_effects_card.setVisible(visible)
    self.output_card.setVisible(visible)
    self.abilities_card.setVisible(visible)
    self.quick_read_card.setVisible(visible)
    self.empty_state.setVisible(not visible)


def _show_snapshot_clean(self, snapshot) -> None:
    assert _ORIGINAL_SHOW_SNAPSHOT is not None
    _ORIGINAL_SHOW_SNAPSHOT(self, snapshot)
    _render_tracked_effects(self)
    _update_quick_read(self, snapshot)


def _load_clean(self, profile) -> None:
    assert _ORIGINAL_LOAD is not None
    _ORIGINAL_LOAD(self, profile)
    enabled = bool(str(profile.ImmunityBuffName or "").strip())
    self.immunity_toggle.setChecked(enabled)


def _immunity_name_value(self) -> str:
    if not self.immunity_toggle.isChecked():
        return ""
    return self.immunity_buff_name.text().strip()


def install() -> None:
    global _INSTALLED, _ORIGINAL_SHOW_SNAPSHOT, _ORIGINAL_LOAD
    if _INSTALLED:
        return

    from widgets.performance_dashboard import PerformanceDashboard

    _ORIGINAL_SHOW_SNAPSHOT = PerformanceDashboard.show_snapshot
    _ORIGINAL_LOAD = PerformanceDashboard.load

    PerformanceDashboard.build_ui = _build_ui_clean
    PerformanceDashboard._set_results_visible = _set_results_visible_clean
    PerformanceDashboard.show_snapshot = _show_snapshot_clean
    PerformanceDashboard.load = _load_clean
    PerformanceDashboard.immunity_buff_name_value = property(_immunity_name_value)

    _INSTALLED = True
