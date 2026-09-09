from __future__ import annotations

"""Plain-language DD readout for the Performance Dashboard.

This card intentionally summarizes observed evidence without inventing build-
specific grades. Crit rate is not labelled good/bad without build context, and
observed DoT coverage is not treated as a canonical uptime target. The one direct
execution leak we can name from the current evidence is an eligible skill cast
that had no preceding Light Attack inside the observed pairing window.
"""

from html import escape

from PySide6.QtWidgets import QLabel

from ui.components.foundry_card import FoundryCard
from ui.theme.colors import Colors

_INSTALLED = False
_ORIGINAL_BUILD_UI = None
_ORIGINAL_SHOW_SNAPSHOT = None


def _dd_readout_lines(snapshot) -> list[str]:
    """Return concise, non-judgmental DD observations for one snapshot."""

    lines: list[str] = []

    crit = getattr(snapshot, "CritRatePercent", None)
    crit_events = int(getattr(snapshot, "CriticalDamageEvents", 0) or 0)
    damage_events = int(getattr(snapshot, "DamageHitEvents", 0) or 0)
    if crit is not None and damage_events > 0:
        lines.append(
            f"Crit: {float(crit):.1f}% of observed damage events "
            f"({crit_events:,}/{damage_events:,})."
        )

    paired = int(getattr(snapshot, "WeavePairedSkillCasts", 0) or 0)
    skills = int(getattr(snapshot, "WeaveSkillCasts", 0) or 0)
    unpaired = int(getattr(snapshot, "WeaveUnpairedSkillCasts", 0) or 0)
    pairing = getattr(snapshot, "WeavePairingPercent", None)
    median_delay = getattr(snapshot, "WeaveMedianPairDelayMs", None)
    if pairing is not None and skills > 0:
        weave_line = (
            f"LA pairing: {paired:,}/{skills:,} eligible skill casts "
            f"({float(pairing):.1f}%); {unpaired:,} unpaired."
        )
        if median_delay is not None:
            weave_line = weave_line[:-1] + f"; median LA→skill delay {float(median_delay):,.0f} ms."
        lines.append(weave_line)

    dot_rows = list(getattr(snapshot, "ObservedDotUptimes", []) or [])
    if dot_rows:
        ordered = sorted(dot_rows, key=lambda row: float(getattr(row, "UptimePercent", 0.0)))
        lowest = ordered[0]
        highest = ordered[-1]
        if len(ordered) == 1:
            lines.append(
                f"Periodic damage: {escape(str(getattr(lowest, 'Name', 'DoT')))} had "
                f"{float(getattr(lowest, 'UptimePercent', 0.0)):.1f}% observed coverage."
            )
        else:
            lines.append(
                f"Periodic damage: {len(ordered)} DoTs had observed coverage from "
                f"{float(getattr(lowest, 'UptimePercent', 0.0)):.1f}% "
                f"({escape(str(getattr(lowest, 'Name', 'lowest')))} ) to "
                f"{float(getattr(highest, 'UptimePercent', 0.0)):.1f}% "
                f"({escape(str(getattr(highest, 'Name', 'highest')))})."
            )

    abilities = list(getattr(snapshot, "TopAbilities", []) or [])
    if abilities:
        top = abilities[0]
        lines.append(
            f"Top damage source: {escape(str(getattr(top, 'Name', 'Ability')))} at "
            f"{float(getattr(top, 'Percent', 0.0)):.1f}% of total damage."
        )

    if unpaired > 0:
        lines.append(
            f"Review first: {unpaired:,} eligible skill cast"
            f"{'s' if unpaired != 1 else ''} had no observed preceding Light Attack."
        )
    elif pairing is not None and skills > 0:
        lines.append(
            "No unpaired eligible skill casts were observed in the LA-pairing window."
        )

    if not lines:
        lines.append("No DD diagnostic evidence is available for this snapshot yet.")

    return lines


def _build_ui_with_dd_summary(self):
    assert _ORIGINAL_BUILD_UI is not None
    _ORIGINAL_BUILD_UI(self)

    self.dd_readout_card = FoundryCard("DD Readout")
    self.dd_readout_label = QLabel("No DD diagnostic evidence yet.")
    self.dd_readout_label.setWordWrap(True)
    self.dd_readout_label.setTextFormat(self.dd_readout_label.textFormat())
    self.dd_readout_card.addWidget(self.dd_readout_label)

    self.dd_readout_note = QLabel(
        "Observed evidence only. Crit rate and DoT coverage are not graded against "
        "build-specific targets."
    )
    self.dd_readout_note.setWordWrap(True)
    self.dd_readout_note.setStyleSheet(
        f"color: {Colors.TEXT_MUTED}; font-size: 10px;"
    )
    self.dd_readout_card.addWidget(self.dd_readout_note)
    self.dd_readout_card.setVisible(False)

    root = self.layout()
    if root is not None:
        root.insertWidget(2, self.dd_readout_card)


def _show_snapshot_with_dd_summary(self, snapshot):
    assert _ORIGINAL_SHOW_SNAPSHOT is not None
    _ORIGINAL_SHOW_SNAPSHOT(self, snapshot)

    is_dd = str(getattr(snapshot, "Role", "")).casefold() == "dps"
    self.dd_readout_card.setVisible(is_dd)
    if not is_dd:
        return

    lines = _dd_readout_lines(snapshot)
    self.dd_readout_label.setText(
        "<br>".join(f"• {line}" for line in lines)
    )


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_UI, _ORIGINAL_SHOW_SNAPSHOT
    if _INSTALLED:
        return

    from widgets.performance_dashboard import PerformanceDashboard

    _ORIGINAL_BUILD_UI = PerformanceDashboard.build_ui
    _ORIGINAL_SHOW_SNAPSHOT = PerformanceDashboard.show_snapshot

    PerformanceDashboard.build_ui = _build_ui_with_dd_summary
    PerformanceDashboard.show_snapshot = _show_snapshot_with_dd_summary
    _INSTALLED = True
