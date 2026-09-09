from __future__ import annotations

"""Healer-specific Performance Dashboard presentation.

The healer page emphasizes coverage, response, and support execution rather than
pretending raw HPS is a universal grade. All wording is observational and keeps
missing evidence separate from player blame.
"""

from html import escape

from PySide6.QtWidgets import QLabel, QGridLayout

from ui.components.foundry_card import FoundryCard
from ui.theme.colors import Colors

_INSTALLED = False
_ORIGINAL_BUILD_UI = None
_ORIGINAL_BUILD_KPI_CARD = None
_ORIGINAL_SHOW_SNAPSHOT = None


def _response_value(snapshot) -> str:
    selected = int(getattr(snapshot, "HealerResponseSelectedEvents", 0) or 0)
    responded = int(getattr(snapshot, "HealerRespondedEvents", 0) or 0)
    median_ms = getattr(snapshot, "HealerMedianResponseMs", None)
    if selected <= 0:
        return "No sample"
    if median_ms is None:
        return f"{responded:,}/{selected:,} observed"
    return f"{responded:,}/{selected:,} • {float(median_ms):,.0f} ms"


def _support_gap_value(snapshot) -> str:
    count = int(getattr(snapshot, "HealerSupportGapCount", 0) or 0)
    largest = getattr(snapshot, "HealerLargestSupportGapSeconds", None)
    if count <= 0:
        return "No long gaps"
    if largest is None:
        return f"{count:,} gap{'s' if count != 1 else ''}"
    return f"{count:,} • max {float(largest):.1f}s"


def _healer_readout_lines(snapshot) -> list[str]:
    lines: list[str] = []

    crit = getattr(snapshot, "HealerCritRatePercent", None)
    critical = int(getattr(snapshot, "HealerCriticalEvents", 0) or 0)
    total_heals = int(getattr(snapshot, "HealerHealingEvents", 0) or 0)
    if crit is not None and total_heals > 0:
        lines.append(
            f"Healing crit: {float(crit):.1f}% of observed healing events "
            f"({critical:,}/{total_heals:,})."
        )

    hot_rows = list(getattr(snapshot, "ObservedHotUptimes", []) or [])
    if hot_rows:
        ordered = sorted(hot_rows, key=lambda row: float(getattr(row, "UptimePercent", 0.0)))
        low = ordered[0]
        high = ordered[-1]
        if len(ordered) == 1:
            lines.append(
                f"Periodic healing: {escape(str(getattr(low, 'Name', 'HoT')))} had "
                f"{float(getattr(low, 'UptimePercent', 0.0)):.1f}% observed coverage."
            )
        else:
            lines.append(
                f"Periodic healing: {len(ordered)} HoTs had observed coverage from "
                f"{float(getattr(low, 'UptimePercent', 0.0)):.1f}% "
                f"({escape(str(getattr(low, 'Name', 'lowest')))}) to "
                f"{float(getattr(high, 'UptimePercent', 0.0)):.1f}% "
                f"({escape(str(getattr(high, 'Name', 'highest')))})."
            )

    selected = int(getattr(snapshot, "HealerResponseSelectedEvents", 0) or 0)
    precovered = int(getattr(snapshot, "HealerPrecoveredEvents", 0) or 0)
    responded = int(getattr(snapshot, "HealerRespondedEvents", 0) or 0)
    unanswered = int(getattr(snapshot, "HealerUnansweredEvents", 0) or 0)
    median_ms = getattr(snapshot, "HealerMedianResponseMs", None)
    largest_ms = getattr(snapshot, "HealerLargestResponseMs", None)
    if selected > 0:
        text = (
            f"High-damage sample: {selected:,} upper-quartile raid damage events; "
            f"{precovered:,} had recent periodic healing from this healer; "
            f"{responded:,} had a healing event within 1.5s afterward"
        )
        if median_ms is not None:
            text += f"; median observed response {float(median_ms):,.0f} ms"
        if largest_ms is not None:
            text += f"; longest observed response {float(largest_ms):,.0f} ms"
        text += f"; {unanswered:,} had neither observation in the analysis window."
        lines.append(text)

    casts = int(getattr(snapshot, "HealerSupportCastCount", 0) or 0)
    gaps = int(getattr(snapshot, "HealerSupportGapCount", 0) or 0)
    largest_gap = getattr(snapshot, "HealerLargestSupportGapSeconds", None)
    threshold = float(getattr(snapshot, "HealerSupportGapThresholdSeconds", 3.0) or 3.0)
    excess = float(getattr(snapshot, "HealerSupportGapExcessSeconds", 0.0) or 0.0)
    if casts >= 2:
        if gaps > 0 and largest_gap is not None:
            lines.append(
                f"Support cadence: {casts:,} meaningful casts; {gaps:,} internal gap"
                f"{'s' if gaps != 1 else ''} exceeded {threshold:.1f}s; largest "
                f"{float(largest_gap):.1f}s; {excess:.1f}s total beyond the threshold."
            )
        else:
            lines.append(
                f"Support cadence: {casts:,} meaningful casts and no internal cast gap "
                f"exceeded {threshold:.1f}s."
            )

    abilities = list(getattr(snapshot, "TopAbilities", []) or [])
    if abilities:
        top = abilities[0]
        lines.append(
            f"Top healing source: {escape(str(getattr(top, 'Name', 'Ability')))} at "
            f"{float(getattr(top, 'Percent', 0.0)):.1f}% of total healing."
        )

    debuffs = list(getattr(snapshot, "DebuffUptimes", []) or [])
    if debuffs:
        top_debuff = debuffs[0]
        lines.append(
            f"Personal debuff footprint: highest observed applied debuff was "
            f"{escape(str(getattr(top_debuff, 'Name', 'Debuff')))} at "
            f"{float(getattr(top_debuff, 'UptimePercent', 0.0)):.1f}% on the dashboard basis."
        )

    if not lines:
        lines.append("No healer diagnostic evidence is available for this snapshot yet.")

    return lines


def _build_kpi_card_with_healer_metrics(self):
    assert _ORIGINAL_BUILD_KPI_CARD is not None
    card = _ORIGINAL_BUILD_KPI_CARD(self)

    from widgets.performance_dashboard import _StatBlock

    self.kpi_heal_crit = _StatBlock("Heal Crit")
    self.kpi_heal_response = _StatBlock("Healing Response")
    self.kpi_heal_cadence = _StatBlock("Support Cadence")

    first = card.body_layout.itemAt(0)
    row = first.layout() if first is not None else None
    if row is not None:
        row.addWidget(self.kpi_heal_crit, 1)
        row.addWidget(self.kpi_heal_response, 1)
        row.addWidget(self.kpi_heal_cadence, 1)
    else:
        card.addWidget(self.kpi_heal_crit)
        card.addWidget(self.kpi_heal_response)
        card.addWidget(self.kpi_heal_cadence)

    for block in (self.kpi_heal_crit, self.kpi_heal_response, self.kpi_heal_cadence):
        block.setVisible(False)

    return card


def _build_ui_with_healer(self):
    assert _ORIGINAL_BUILD_UI is not None
    _ORIGINAL_BUILD_UI(self)

    self.healer_readout_card = FoundryCard("Healer Readout")
    self.healer_readout_label = QLabel("No healer diagnostic evidence yet.")
    self.healer_readout_label.setWordWrap(True)
    self.healer_readout_card.addWidget(self.healer_readout_label)

    self.healer_readout_note = QLabel(
        "Observed evidence only. HPS is not graded as a universal healer score. "
        "Response samples, HoT coverage, and cast gaps describe what the log shows; "
        "they do not prove assignment success or failure by themselves."
    )
    self.healer_readout_note.setWordWrap(True)
    self.healer_readout_note.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px;")
    self.healer_readout_card.addWidget(self.healer_readout_note)
    self.healer_readout_card.setVisible(False)

    root = self.layout()
    if root is not None:
        root.insertWidget(2, self.healer_readout_card)

    hot_card, self.hot_chart_view = self._build_chart_card(
        "Observed HoT Coverage", compact=True
    )
    self.hot_card = hot_card
    layout = self.charts_widget.layout()
    if isinstance(layout, QGridLayout):
        layout.addWidget(hot_card, layout.rowCount(), 0, 1, 2)
    elif layout is not None:
        layout.addWidget(hot_card)
    hot_card.setVisible(False)


def _show_snapshot_with_healer(self, snapshot):
    assert _ORIGINAL_SHOW_SNAPSHOT is not None
    _ORIGINAL_SHOW_SNAPSHOT(self, snapshot)

    is_healer = str(getattr(snapshot, "Role", "")).casefold() == "healer"
    self.healer_readout_card.setVisible(is_healer)
    self.hot_card.setVisible(is_healer)
    for block in (self.kpi_heal_crit, self.kpi_heal_response, self.kpi_heal_cadence):
        block.setVisible(is_healer)

    if not is_healer:
        return

    crit = getattr(snapshot, "HealerCritRatePercent", None)
    critical = int(getattr(snapshot, "HealerCriticalEvents", 0) or 0)
    total = int(getattr(snapshot, "HealerHealingEvents", 0) or 0)
    self.kpi_heal_crit.set_value(
        "Unavailable" if crit is None else f"{float(crit):.1f}% ({critical:,}/{total:,})"
    )
    self.kpi_heal_response.set_value(_response_value(snapshot))
    self.kpi_heal_cadence.set_value(_support_gap_value(snapshot))

    self.kpi_heal_crit.setToolTip(
        "Critical healing events divided by all observed healing events from this healer."
    )
    self.kpi_heal_response.setToolTip(
        "Upper-quartile raid damage events only. Shows how often this healer had recent periodic "
        "healing on the target and/or a healing event within 1.5 seconds afterward. This is not a blame score."
    )
    self.kpi_heal_cadence.setToolTip(
        "Internal intervals between meaningful healer casts. Heavy attacks and synergies count as activity; "
        "Light Attacks and movement/utility actions do not. Long gaps are observations, not automatic mistakes."
    )

    self.abilities_card.title_label.setText(
        "Top Healing Abilities • contribution to total"
    )
    self.hot_card.title_label.setText("Observed HoT Coverage (full fight)")
    self._update_uptime_chart(
        self.hot_chart_view,
        list(getattr(snapshot, "ObservedHotUptimes", []) or []),
        Colors.ROLE.get("healer", Colors.SUCCESS),
    )

    lines = _healer_readout_lines(snapshot)
    self.healer_readout_label.setText("<br>".join(f"• {line}" for line in lines))

    note = str(getattr(snapshot, "HealerAnalysisNote", "") or "").strip()
    if note:
        self.healer_readout_card.setToolTip(note)
        self.hot_card.setToolTip(note)


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_UI, _ORIGINAL_BUILD_KPI_CARD, _ORIGINAL_SHOW_SNAPSHOT
    if _INSTALLED:
        return

    from widgets.performance_dashboard import PerformanceDashboard

    _ORIGINAL_BUILD_UI = PerformanceDashboard.build_ui
    _ORIGINAL_BUILD_KPI_CARD = PerformanceDashboard._build_kpi_card
    _ORIGINAL_SHOW_SNAPSHOT = PerformanceDashboard.show_snapshot

    PerformanceDashboard.build_ui = _build_ui_with_healer
    PerformanceDashboard._build_kpi_card = _build_kpi_card_with_healer_metrics
    PerformanceDashboard.show_snapshot = _show_snapshot_with_healer
    _INSTALLED = True
