from __future__ import annotations

"""Plain-language DD readout for the Performance Dashboard.

This card intentionally summarizes observed evidence without inventing build-
specific grades. Crit rate is not labelled good/bad without build context, and
observed DoT coverage is not treated as a canonical uptime target. The direct
execution observations we can name are unpaired eligible skill casts and long
internal skill-to-skill intervals. Long intervals are explicitly not called
"dead time" because mechanics or target unavailability may explain them.
"""

from html import escape

from PySide6.QtWidgets import QLabel

from ui.components.foundry_card import FoundryCard
from ui.theme.colors import Colors

_INSTALLED = False
_ORIGINAL_BUILD_UI = None
_ORIGINAL_SHOW_SNAPSHOT = None


def _enforce_dd_card_visibility(self, is_dd: bool) -> None:
    """Apply the final role-specific card state after every wrapped presenter.

    The polished dashboard's Support Effect Uptime card is useful for healer/tank
    review but competes with the DD-only Observed DoT Uptime card for the same
    visible summary row. DPS tabs therefore swap that support card out for the
    DoT card. Legacy hidden support cards are gated here too for compatibility.
    """

    for name in (
        "buff_card",
        "debuff_card",
        "raid_debuff_card",
        "support_effects_card",
    ):
        card = getattr(self, name, None)
        if card is not None:
            card.setVisible(not is_dd)

    dot_card = getattr(self, "dot_card", None)
    if dot_card is not None:
        dot_card.setVisible(is_dd)


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
            weave_line = weave_line[:-1] + (
                f"; median LA→skill delay {float(median_delay):,.0f} ms."
            )
        lines.append(weave_line)

    gap_count = int(getattr(snapshot, "ObservedActionGapCount", 0) or 0)
    largest_gap = getattr(snapshot, "ObservedLargestActionGapSeconds", None)
    excess_gap = float(getattr(snapshot, "ObservedActionGapExcessSeconds", 0.0) or 0.0)
    gap_threshold = float(getattr(snapshot, "ActivityGapThresholdSeconds", 2.5) or 2.5)
    if gap_count > 0 and largest_gap is not None:
        lines.append(
            f"Action gaps: {gap_count:,} internal skill-to-skill gap"
            f"{'s' if gap_count != 1 else ''} exceeded {gap_threshold:.1f}s; "
            f"largest {float(largest_gap):.1f}s; {excess_gap:.1f}s total beyond the threshold."
        )
    elif skills >= 2:
        lines.append(
            f"No internal eligible skill-to-skill gap exceeded {gap_threshold:.1f}s."
        )

    if gap_count > 0:
        quiet = int(getattr(snapshot, "ActionGapRaidQuietCount", 0) or 0)
        active = int(getattr(snapshot, "ActionGapRaidActiveCount", 0) or 0)
        unknown = int(getattr(snapshot, "ActionGapUnknownCount", 0) or 0)
        if quiet or active or unknown:
            parts: list[str] = []
            if quiet:
                parts.append(f"{quiet:,} raid-quiet")
            if active:
                parts.append(f"{active:,} raid-active")
            if unknown:
                parts.append(f"{unknown:,} unresolved")
            lines.append(
                "Gap context: " + ", ".join(parts) + ". Raid activity is context, not proof of cause."
            )

    dot_rows = list(getattr(snapshot, "ObservedDotUptimes", []) or [])
    if dot_rows:
        ordered = sorted(
            dot_rows,
            key=lambda row: float(getattr(row, "UptimePercent", 0.0)),
        )
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
                f"({escape(str(getattr(lowest, 'Name', 'lowest')))}) to "
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
    self.dd_readout_card.addWidget(self.dd_readout_label)

    self.dd_readout_note = QLabel(
        "Observed evidence only. Crit rate and DoT coverage are not graded against build-specific targets. Action gaps are observations, not graded dead time. Raid activity provides context but does not prove why a gap occurred."
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

    is_dd = str(getattr(snapshot, "Role", "")).strip().casefold() == "dps"
    _enforce_dd_card_visibility(self, is_dd)
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

    # Install the final role surface last so generic polish/overlay cards cannot
    # bury the DD presentation after all other wrappers have run.
    from ui.performance_dashboard_role_surface_support import install as install_role_surface

    install_role_surface()
