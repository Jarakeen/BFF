from __future__ import annotations

"""DD-only observed Light Attack pairing presentation."""

_INSTALLED = False
_ORIGINAL_BUILD_KPI_CARD = None
_ORIGINAL_SHOW_SNAPSHOT = None


def _weave_value_text(percent: float | None, paired: int, skills: int) -> str:
    if percent is None:
        return "Unavailable"
    return f"{percent:.1f}% ({paired:,}/{skills:,})"


def _build_kpi_card_with_weave(self):
    assert _ORIGINAL_BUILD_KPI_CARD is not None
    card = _ORIGINAL_BUILD_KPI_CARD(self)

    from widgets.performance_dashboard import _StatBlock

    self.kpi_weave = _StatBlock("LA Pairing")
    first = card.body_layout.itemAt(0)
    row = first.layout() if first is not None else None
    if row is not None:
        row.addWidget(self.kpi_weave, 1)
    else:
        card.addWidget(self.kpi_weave)
    self.kpi_weave.setVisible(False)
    return card


def _show_snapshot_with_weave(self, snapshot):
    assert _ORIGINAL_SHOW_SNAPSHOT is not None
    _ORIGINAL_SHOW_SNAPSHOT(self, snapshot)

    is_dd = str(getattr(snapshot, "Role", "")).casefold() == "dps"
    self.kpi_weave.setVisible(is_dd)
    if not is_dd:
        return

    percent = getattr(snapshot, "WeavePairingPercent", None)
    paired = int(getattr(snapshot, "WeavePairedSkillCasts", 0) or 0)
    skills = int(getattr(snapshot, "WeaveSkillCasts", 0) or 0)
    light_attacks = int(getattr(snapshot, "WeaveLightAttackCasts", 0) or 0)
    unpaired = int(getattr(snapshot, "WeaveUnpairedSkillCasts", 0) or 0)
    median_delay = getattr(snapshot, "WeaveMedianPairDelayMs", None)

    self.kpi_weave.set_value(_weave_value_text(percent, paired, skills))

    detail = [
        "Observed Light Attack pairing, not a universal weave grade.",
        f"Light Attacks observed: {light_attacks:,}",
        f"Eligible skill casts: {skills:,}",
        f"Paired skill casts: {paired:,}",
        f"Unpaired skill casts: {unpaired:,}",
    ]
    if median_delay is not None:
        detail.append(f"Median LA→skill delay: {float(median_delay):,.0f} ms")
    detail.append(
        "A skill is paired only when an unused Light Attack precedes it within 1.2 seconds. "
        "Utility actions, heavy attacks, and synergies are excluded from the skill denominator."
    )

    note = str(getattr(snapshot, "WeaveAnalysisNote", "") or "").strip()
    if note:
        detail.append(note)

    self.kpi_weave.setToolTip("\n".join(detail))


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_KPI_CARD, _ORIGINAL_SHOW_SNAPSHOT
    if _INSTALLED:
        return

    from widgets.performance_dashboard import PerformanceDashboard

    _ORIGINAL_BUILD_KPI_CARD = PerformanceDashboard._build_kpi_card
    _ORIGINAL_SHOW_SNAPSHOT = PerformanceDashboard.show_snapshot

    PerformanceDashboard._build_kpi_card = _build_kpi_card_with_weave
    PerformanceDashboard.show_snapshot = _show_snapshot_with_weave
    _INSTALLED = True

    # Finish the DD presentation stack with a concise evidence summary.
    from ui.performance_dashboard_dd_summary_support import install as install_dd_summary

    install_dd_summary()
