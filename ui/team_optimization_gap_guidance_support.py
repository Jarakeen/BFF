from __future__ import annotations

"""Expose exact Team Optimization capability gaps with useful next actions.

The canonical analyzer already preserves per-build gap strings. This UI layer
makes them visible instead of collapsing dozens of unresolved rows into one
counter. Guidance is deliberately conservative: it tells the raid lead what to
review without inventing an ESO answer when Foundry's source evidence is missing.
"""

from PySide6.QtWidgets import QTableWidgetItem


_INSTALLED = False
_ORIGINAL_REFRESH = None


def guidance_for_gap(gap: str) -> str:
    text = " ".join(str(gap or "").strip().split())
    key = text.casefold()

    if "passive rank is not recorded" in key:
        return "Record this character passive rank in Builds → Character Progression, then re-run analysis."
    if "scribed" in key or "grimoire" in key or "script" in key:
        return "Open the build's Scribed Skill setup and verify the grimoire plus all three scripts."
    if "champion point" in key or " cp " in f" {key} ":
        return "Review the build's slotted CP and recorded rank. If the build is correct, this is canonical CP evidence debt rather than a team change."
    if "mundus" in key:
        return "Review the build's Mundus selection and any second-Mundus requirement."
    if "potion" in key or "alchemy" in key:
        return "Review the selected potion/formula on the build. If the selection is correct, verify the canonical potion mapping."
    if "gear" in key or "set " in key or " set" in key:
        return "Review the named set, active piece count, weapon-bar state, and Perfected/non-Perfected identity in the build."
    if "skill" in key or "ability" in key or "morph" in key:
        return "Review the skill name/morph on the saved bar. If it is correct in-game, this is a Foundry skill/effect mapping gap to resolve in Reference Data."
    if "race" in key or "racial" in key:
        return "Review the character race/passive progression. Do not change the build solely to clear this if the character data is already correct."
    if "does not resolve to a canonical effect" in key or "source evidence" in key or "not stat-mapped" in key:
        return "Foundry lacks reviewed canonical evidence here. Verify Reference Data/source mapping; do not change the raid build just to make the warning disappear."
    if "unavailable" in key or "unknown" in key or "unresolved" in key:
        return "Open this saved build and verify the named field. If the saved value is correct, treat this as Foundry data-resolution debt, not an optimization recommendation."
    return "Review this exact field on the saved build. If it is correct, the fix belongs in Foundry's canonical evidence rather than in the player's setup."


def _rows_for_analysis(result, *, team_label: str = ""):
    rows = []
    if result is None:
        return rows
    for summary in tuple(getattr(result, "build_summaries", ()) or ()):
        player = str(getattr(summary, "player_name", "") or "Unnamed Player")
        build = str(getattr(summary, "build_name", "") or "Current Build")
        identity = f"{team_label} • {player} • {build}" if team_label else f"{player} • {build}"
        for gap in tuple(getattr(summary, "capability_gaps", ()) or ()):
            text = str(gap or "").strip()
            if text:
                rows.append((identity, text, guidance_for_gap(text)))
    return rows


def _populate_gap_table(page) -> None:
    card = getattr(page, "gear_card", None)
    table = getattr(page, "gear_table", None)
    if card is None or table is None:
        return

    comparison = getattr(page, "_optimization_current_canonical_comparison", None)
    current = getattr(page, "_optimization_current_canonical_analysis", None)
    rows = []
    if comparison is not None:
        rows.extend(_rows_for_analysis(getattr(comparison, "team_a", None), team_label="Team A"))
        rows.extend(_rows_for_analysis(getattr(comparison, "team_b", None), team_label="Team B"))
    else:
        rows.extend(_rows_for_analysis(current))

    card.setMaximumHeight(16777215)
    card.show()
    card.title_label.setText("Capability Resolution Gaps & What To Fix")
    table.setColumnCount(3)
    table.setHorizontalHeaderLabels(["PLAYER / BUILD", "EXACT GAP", "WHAT TO DO"])
    table.setRowCount(len(rows))
    table.setMinimumHeight(260 if rows else 120)
    table.horizontalHeader().setStretchLastSection(True)

    for row, values in enumerate(rows):
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setToolTip(value)
            table.setItem(row, column, item)

    if not rows:
        table.setRowCount(1)
        table.setItem(0, 0, QTableWidgetItem("—"))
        table.setItem(0, 1, QTableWidgetItem("No capability-resolution gaps."))
        table.setItem(0, 2, QTableWidgetItem("Nothing to fix in static capability resolution."))

    risks = getattr(page, "risks_card", None)
    if risks is not None:
        risks.title_label.setText("Optimization Boundaries & Summary")


def install() -> None:
    global _INSTALLED, _ORIGINAL_REFRESH
    if _INSTALLED:
        return

    from ui import team_optimization_canonical_analysis_support as canonical

    _ORIGINAL_REFRESH = canonical._refresh_canonical_analysis

    def refresh_with_gap_guidance(page) -> None:
        assert _ORIGINAL_REFRESH is not None
        _ORIGINAL_REFRESH(page)
        _populate_gap_table(page)

    canonical._refresh_canonical_analysis = refresh_with_gap_guidance
    _INSTALLED = True


__all__ = ["guidance_for_gap", "install"]
